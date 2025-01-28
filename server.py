import json
import logging
import queue
import sys
import threading
from time import time

import mqtt
import datetime
import ipaddress
from flask import Flask, jsonify, request, abort
from typing import Optional

import config
import database
import router_com
from thermo import Thermo, ProcessingError, ConnectError

app = Flask(__name__)

# request logging
formatter = logging.Formatter('%(asctime)s %(message)s', '%Y-%m-%dT%H:%M:%SZ')
request_logger = logging.getLogger('requests_log')
file_handler = logging.FileHandler('requests.log')
file_handler.setFormatter(formatter)
request_logger.addHandler(file_handler)
request_logger.setLevel(logging.INFO)

thermo_dict = {}
last_update = 0
db: Optional[database.Database] = None
logged_name = None

update_thermo_result_queue = queue.Queue()


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


@app.before_request
def check_auth():
    global logged_name

    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            bearer, _, token = auth_header.partition(' ')
            print(token)
            if bearer == 'Bearer' and token and token in config.AUTH_TOKENS:
                logged_name = config.AUTH_TOKENS[token]
                return
    except NameError:
        pass

    ip_address = request.remote_addr
    try:
        for net in config.ALLOWED_NETWORKS:
            if ipaddress.ip_address(ip_address) in ipaddress.ip_network(net):
                return
    except NameError:
        pass

    abort(401,
          'Authentication required. '
          'Please use the assigned access token or access to this resource from allowed network.')


@app.after_request
def log_request(response):
    global request_logger
    request_logger.info('%d: (%s,%s): %s', response.status_code, request.remote_addr, logged_name, request.full_path)
    return response


def init_thermos():
    global db
    # create db connection
    if config.STATS_ENABLED:
        try:
            db = database.Database()

        except Exception:
            eprint('Error connecting to the stats DB')

    # create thermo objects
    for dev_key, dev_props in config.DEVICES.items():
        thermo_dict[dev_key] = Thermo(dev_props['ip'], dev_props['display'], db)
        # thermo_dict[dev_key].set_debug()


def update_job(thermo: Thermo, thermo_id: str):
    try:
        thermo.connect()
        thermo.update_status()
        thermo.disconnect()
        if config.MQTT_ENABLED:
            mqtt.data_queue.put((thermo_id, thermo.status_data))

    except ConnectError as e:
        eprint("[CONN_EXCEPT][%s] %s " % (thermo, e))

    except ProcessingError as e:
        eprint("[VAL_EXCEPT][%s] %s " % (thermo, e))

    except Exception as e:
        eprint("[EXCEPT][%s] %s " % (thermo, e))


def update_thermo_data():
    global thermo_dict, last_update

    # update data
    if time() > (last_update + config.DATA_VALIDITY_SEC):
        # fetch data in parallel

        threads = []
        for thermo_id, thermo in thermo_dict.items():
            thread = threading.Thread(target=update_job, args=(thermo, thermo_id))
            thread.start()
            threads.append(thread)

        # wait to thread done
        for x in threads:
            x.join()

        last_update = time()


def get_thermo(name: str) -> Thermo:
    thermo = thermo_dict.get(name)  # type: Thermo
    if not thermo:
        eprint('Thermostat %s not found!' % name)
        abort(400, description="Thermostat with name %s not found!" % name)
    else:
        return thermo


@app.route("/")
def thermo_list():
    global thermo_dict, last_update
    output = {}

    if config.MESSAGE:
        output['message'] = config.MESSAGE,
        output['exit'] = config.MESSAGE_CLOSE

        if config.MESSAGE_CLOSE:
            return jsonify(output)

    update_thermo_data()
    output['data'] = {k: v.status_data for (k, v) in thermo_dict.items()}
    output['lastUpdate'] = last_update

    return jsonify(output)


@app.route("/schedule", methods=['GET'])
def load_schedule():
    name = request.args.get('name', type=str)
    prog = request.args.get('prog', type=int)
    thermo = get_thermo(name)

    try:
        thermo.connect()
        output = thermo.get_program(prog) if prog else thermo.get_programs()
        return jsonify(output)
    except ConnectError as e:
        eprint("[CONN_EXCEPT] %s" % e)
        abort(503)
    except Exception as e:
        eprint("[EXCEPT] %s" % e)
        abort(500)


@app.route("/invalidate", methods=['GET'])
def invalidate_data():
    global last_update
    name = request.args.get('name', type=str)
    if name in config.DEVICES:
        last_update = 0
        return jsonify({"status": "true"})


@app.route("/switch", methods=['GET'])
def switch_router():
    name = request.args.get('name', type=str)
    if name in config.DEVICES:
        try:
            router_com.change_ip(config.DEVICES[name]['ip'])
            return jsonify({"status": "true"})

        except Exception as e:
            eprint("[EXCEPT] %s" % e)
            abort(500)


@app.route("/manual", methods=['GET'])
def manual_switch():
    global last_update
    name = request.args.get('name', type=str)
    temp = request.args.get('temp', type=int, default=20)
    thermo = get_thermo(name)

    try:
        thermo.connect()
        thermo.set_manual_temp(temp)
        data = thermo.get_status_data()
        thermo.disconnect()
        return jsonify(data)

    except Exception as e:
        eprint("[EXCEPT] %s" % e)
        abort(500)
        return False


@app.route("/auto", methods=['GET'])
def auto_switch():
    name = request.args.get('name', type=str)
    prog = request.args.get('prog', type=int, default=1)
    temp = request.args.get('temp', type=int, default=None)
    thermo = get_thermo(name)

    try:
        thermo.connect()
        thermo.set_auto_prog(prog, temp)
        data = thermo.get_status_data()
        thermo.disconnect()
        return jsonify(data)

    except Exception as e:
        eprint("[EXCEPT] %s" % e)
        abort(500)
        return False


@app.route("/stats", methods=['GET'])
def fetch_daily_stats():
    global db
    day = datetime.datetime.strptime(request.args.get('day', type=str), '%Y-%m-%d')
    if db and day:
        stats = db.get_stats(day)
        return stats
    abort(500, description="Stats not available.")


@app.route("/update-schedule", methods=['POST'])
def update_schedule():
    if not request.json:
        eprint('No JSON request received.')
        abort(400, description="No JSON request received.")

    result = False
    name = request.args.get('name', type=str)
    prog = request.args.get('prog', type=int, default=1)
    data = json.loads(request.data)
    thermo = get_thermo(name)

    try:
        thermo.connect()
        thermo.set_program(prog, data)
        thermo.disconnect()
        result = True

    except Exception as e:
        eprint("[EXCEPT] %s" % e)
        abort(500)

    return jsonify({"status": str(result)})


def write_stats(signal_number=None):
    print("Writing stats")
    global thermo_dict
    update_thermo_data()
    for k in thermo_dict:
        thermo_dict[k].write_stats(k)


# Run Flask app
if __name__ == "__main__":
    init_thermos()

    if config.MQTT_ENABLED:
        print("Starting MQTT thread")
        thread = threading.Thread(target=mqtt.init_mqtt, daemon=True)
        thread.start()

    app.run(host=config.LISTEN_IP, port=config.LISTEN_PORT)
