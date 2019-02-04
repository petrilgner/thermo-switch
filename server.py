import threading
from flask import Flask, jsonify, request, abort
from time import time
from thermo import Thermo
import router_com
import config
import sys
import json

app = Flask(__name__)

thermo_dict = {}
last_update = 0


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


@app.before_first_request
def activate_job():
    # create thermo objects
    for dev_key, dev_props in config.DEVICES.items():
        thermo_dict[dev_key] = Thermo(dev_props['ip'], dev_props['display'])
        thermo_dict[dev_key].set_debug()


def update_job(thermo: Thermo):
    try:
        thermo.connect()
        thermo.update_status()
        thermo.disconnect()

    except Exception as e:
        eprint("[LOAD_EXCEPTION] %s " % e)


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

    # update data
    if time() > (last_update + config.DATA_VALIDITY_SEC):
        # fetch data in parallel
        print(thermo_dict)
        values = thermo_dict.values()
        print(thermo_dict)
        print(values)

        threads = []

        for thermo in values:
            thread = threading.Thread(target=update_job, args=(thermo,))
            thread.start()
            threads.append(thread)

        # wait to threads done
        for x in threads:
            x.join()

        last_update = time()

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
    except (ConnectionResetError, ConnectionAbortedError, ConnectionRefusedError) as e:
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


# Run Flask app
if __name__ == "__main__":
    app.run(host=config.LISTEN_IP, port=config.LISTEN_PORT)
