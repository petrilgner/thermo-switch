from flask import Flask
from flask import jsonify
from flask import request
import time
import thermo_com
import router_com

app = Flask(__name__)
if __name__ == "__main__":
    app.run(host='192.168.11.100', port=5000)

devices = {
    "Test": {'ip': "192.168.11.4", 'display': "Testovací teploměr"},
}

DATA_VALIDITY_SEC = 60

thermo_dict = {}
last_update = 0


@app.route("/")
def thermo_list():
    global thermo_dict, last_update
    output = dict()

    # update data
    if time.time() > (last_update + DATA_VALIDITY_SEC):
        for name, props in devices.items():
            try:
                status_dict = thermo_com.get_status(props['ip'])
                thermo_dict[name] = status_dict
                thermo_dict[name]['display'] = props['display']
            except Exception as e:
                print(e)
                continue

        last_update = time.time()

    output['data'] = thermo_dict
    output['lastUpdate'] = last_update


    return jsonify(output)


@app.route("/invalidate", methods=['GET'])
def invalidate_data():
    global last_update
    name = request.args.get('name', type=str)
    if name in devices:
        last_update = 0
        return jsonify({"status": "true"})


@app.route("/switch", methods=['GET'])
def switch_router():
    name = request.args.get('name', type=str)
    if name in devices:
        router_com.change_ip(devices[name]['ip'])
        return jsonify({"status": "true"})


@app.route("/manual", methods=['GET'])
def manual_switch():
    global last_update
    name = request.args.get('name', type=str)
    temp = request.args.get('temp', type=int, default=20)
    if name in devices:
        status_data = thermo_com.set_manual_temp(devices[name]['ip'], temp)
        thermo_dict[name].update(status_data)

        return jsonify(status_data)


@app.route("/auto", methods=['GET'])
def auto_switch():
    global last_update
    name = request.args.get('name', type=str)
    prog = request.args.get('prog', type=int, default=1)
    if name in devices:
        status_data = thermo_com.set_auto_prog(devices[name]['ip'], prog)
        thermo_dict[name].update(status_data)
        return jsonify(status_data)
