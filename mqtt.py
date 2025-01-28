import paho.mqtt.client as mqtt
from paho.mqtt.client import Client

import queue
import config
from typing import Optional
from thermo import Thermo
import json

mqtt_client = None  # type: Optional[mqtt.Client]
data_queue = queue.Queue()


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        print(f"[MQTT] Failed to connect: {reason_code}. loop_forever() will retry connection")
    else:
        print("[MQTT] Connected to the broker")
        client.subscribe(config.MQTT_TOPIC + "/#")


def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
        print(f"[MQTT] {msg.topic} / Received message: {data}")

    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")


def publish_from_queue():
    while not data_queue.empty():
        thermo_tuple = data_queue.get()
        if thermo_tuple is None:
            return

        if thermo_tuple and thermo_tuple[1]:
            thermo_id = thermo_tuple[0]
            status_data = thermo_tuple[1]
            payload = {
                'temp': status_data['temp'],
                'mode': status_data['mode'],
                'program': status_data['program'],
                'relay': status_data['relay'],
                'locked': status_data['locked'],
                'req_temp': status_data['req_temp']
            }
            mqtt_client.publish(f"{config.MQTT_TOPIC}/{thermo_id}", json.dumps(payload))
            print(f"[MQTT] Published to {config.MQTT_TOPIC}/{thermo_id}")


def init_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message

    mqtt_client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)
    mqtt_client.connect(config.MQTT_HOST, config.MQTT_PORT, 60)

    try:
        while True:
            publish_from_queue()
            mqtt_client.loop(timeout=1.0)  # Run the loop non-blocking
    except KeyboardInterrupt | InterruptedError:
        print("[MQTT] Disconnecting")
        mqtt_client.disconnect()
        data_queue.put(None)
