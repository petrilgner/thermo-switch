from multiprocessing import Pool
from flask import Flask
from flask import jsonify
from flask import request
import time
import thermo_com
import router_com
import config

app = Flask(__name__)

thermo_dict = {}
last_update = 0


def load_status(props):
    try:
        status_dict = thermo_com.get_status(props['ip'])
        status_dict['display'] = props['display']
        return props['name'], status_dict

    except Exception as e:
        print(e)


@app.route("/")
def thermo_list():
    global thermo_dict, last_update

    output_arr = []
    input_arr = []
    output = {}

    if config.MESSAGE:
        output['message'] = config.MESSAGE,
        output['exit'] = config.MESSAGE_CLOSE

        if config.MESSAGE_CLOSE:
            return jsonify(output)


    # prepare array
    for key, props in config.DEVICES.items():
        props['name'] = key
        input_arr.append(props)

    # update data
    if time.time() > (last_update + config.DATA_VALIDITY_SEC):

        # fetch data in parallel
        with Pool(processes=len(config.DEVICES)) as pool:
            output_arr = pool.map(load_status, input_arr)

        # assembly thermo dict
        for name, values in output_arr:
            thermo_dict[name] = values

        last_update = time.time()

    output['data'] = thermo_dict
    output['lastUpdate'] = last_update
    return jsonify(output)


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
        router_com.change_ip(config.DEVICES[name]['ip'])
        return jsonify({"status": "true"})


@app.route("/manual", methods=['GET'])
def manual_switch():
    global last_update
    name = request.args.get('name', type=str)
    temp = request.args.get('temp', type=int, default=20)
    if name in config.DEVICES:
        status_data = thermo_com.set_manual_temp(config.DEVICES[name]['ip'], temp)
        thermo_dict[name].update(status_data)

        return jsonify(status_data)


@app.route("/auto", methods=['GET'])
def auto_switch():
    global last_update
    name = request.args.get('name', type=str)
    prog = request.args.get('prog', type=int, default=1)
    temp = request.args.get('temp', type=int, default=None)
    if name in config.DEVICES:
        status_data = thermo_com.set_auto_prog(config.DEVICES[name]['ip'], prog, temp)
        thermo_dict[name].update(status_data)
        return jsonify(status_data)


# Run Flask app
if __name__ == "__main__":
    app.run(host=config.LISTEN_IP, port=config.LISTEN_PORT)
