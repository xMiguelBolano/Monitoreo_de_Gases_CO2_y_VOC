#!/usr/bin/python -u
# co2_sgp30.py

from sgp30 import SGP30
import os
from datetime import datetime
import threading
import sys
import paho.mqtt.client as mqtt
import json
import requests  # Se usa para enviar notificaciones por ntfy.sh

#curl -v -X POST http://thingsboard.cloud/api/v1/uNMhPwu0dBVqEU6ck6Md/telemetry --header Content-Type:application/json --data "{temperature:25}"

# Crear clase heredada
class SGP30_Raw(SGP30):
    def get_air_quality_raw(self):
        eco2, tvoc = self.command('measure_air_quality')
        return (eco2, tvoc)

sgp30 = SGP30_Raw()

THINGSBOARD_HOST = '2982a670-334a-11f0-8983-6766228fa881' #'IP NUMBERS GO HERE'
ACCESS_TOKEN = 'uNMhPwu0dBVqEU6ck6Md' #'TOKEN GOES HERE'
INTERVAL = 10

# ntfy.sh ##############################
NTFY_TOPIC = 'co2-alert'

def send_ntfy_notification(title, message):
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={"Title": title}
        )
        print("Notificación enviada con ntfy.sh")
    except Exception as e:
        print("Error enviando notificación:", e)
########################################

# Mensaje de alerta por co2 ##################
def check_co2_levels(co2_value):
    if co2_value > 1000:  # Umbral de CO2 alto
        send_alert_notification()

def send_alert_notification():
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data="Alerta: Niveles de CO2 altos detectados".encode('utf-8'),
            headers={"Title": "Alerta CO2"}
        )
        print("Notificación de alerta enviada")
    except Exception as e:
        print("Error enviando notificación de alerta:", e)
########################################

# Inicio
send_ntfy_notification("CO2", "Sistema iniciado correctamente")

sensor_data = {'co2': 0, 'voc': 0}
client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_HOST, 1883, 60)
exit_thread = threading.Event()

print("Sensor warming up, please wait...")

def crude_progress_bar():
    sys.stdout.write('.')
    sys.stdout.flush()

sgp30.start_measurement(crude_progress_bar)
sys.stdout.write('\n')

client.loop_start()

try:
    while True:
        result = sgp30.get_air_quality()
        raw = sgp30.get_air_quality_raw()
        sensor_data['co2'] = raw[0]
        sensor_data['voc'] = raw[1]

        print(datetime.now())
        print(result)
        print(raw)

        client.publish('v1/devices/me/telemetry', json.dumps(sensor_data), 1)

        # Notificación push con ntfy.sh
        try:
            mensaje = f"eCO2: {raw[0]} ppm, TVOC: {raw[1]} ppb"
            send_ntfy_notification("Lectura SGP30", mensaje)
            check_co2_levels(raw[0])  # Notifiacion por altos niveles de CO2
        except Exception as e:
            print("Error en notificación:", e)

        if exit_thread.wait(timeout=INTERVAL):
            break
except (KeyboardInterrupt, SystemExit):
    raise

client.loop_stop()
client.disconnect()
# EOF
