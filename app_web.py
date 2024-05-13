import json
import mediapipe as mp
import cv2
import io
import pickle
import numpy as np
from PIL import Image
from flask import request
from flask import Flask, render_template
from flask import jsonify
from bluetooth import *
import socket
import time
import subprocess
import base64
import paho.mqtt.client as mqtt
Trimodel = pickle.load(open('model', 'rb'))
hand_signals = ['FW', 'ST', 'RL', 'RR', 'BW']
ip = None
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands = 2, min_detection_confidence = 0.8, min_tracking_confidence = 0.5)
app = Flask(__name__)
app.secret_key = "haha"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test', methods=['POST'])
def test():
    output = request.get_json()
    imgdata = base64.b64decode(output)
    img = Image.open(io.BytesIO(imgdata))
    opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_BGR2RGB)
    opencv_img = cv2.flip(opencv_img, 1)
    opencv_img.flags.writeable = False
    results = hands.process(opencv_img)
    opencv_img.flags.writeable = True
    result = None
    if results.multi_hand_landmarks:
            hands_keypoint = []
            if len(results.multi_handedness) == 2:
                for hand in results.multi_hand_landmarks:
                    hand = convert_landmark_list(hand)
                    hands_keypoint += hand
                if (results.multi_handedness[0].classification[0].label != results.multi_handedness[1].classification[0].label):
                    if (results.multi_handedness[0].classification[0].label == 'Right'):
                        slice = int(len(hands_keypoint) / 2)
                        hands_keypoint = hands_keypoint[slice:] + hands_keypoint[:slice]
                    elif (results.multi_handedness[0].classification[0].label == 'Left'):
                        slice = int(len(hands_keypoint) / 2)
                        hands_keypoint = hands_keypoint[:slice] + hands_keypoint[slice:]
                result = Trimodel.predict([hands_keypoint])
            else:
                for side in results.multi_handedness:
                    if side.classification[0].label == 'Left':
                        for hand in results.multi_hand_landmarks:
                            hand = convert_landmark_list(hand)
                            hands_keypoint += hand
                        hands_keypoint += [0.0] * 63
                    else:
                        hands_keypoint += [0.0] * 63
                        for hand in results.multi_hand_landmarks:
                            hand = convert_landmark_list(hand)
                            hands_keypoint += hand
                result = Trimodel.predict([hands_keypoint])
    print(result)
    if result is not None:
        result = str(hand_signals[result[0]])
        mqtt_client.publish("topic/command", result)
        return jsonify(result)
    result = "Not found"
    mqtt_client.publish("topic/command")
    return jsonify("Not found")

@app.route('/stream', methods=['POST'])
def stream():
    global frame
    if frame:
        return jsonify(frame)

@app.route('/Scan', methods=['POST'])
def Scan():
    nearby_devices = discover_devices(lookup_names=True)
    return jsonify(nearby_devices)

@app.route('/ConnectBluetooth', methods=['POST'])
def ConnectBluetooth():
    bd_addr = request.get_json()
    port = 1
    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    try:
        s.connect((bd_addr, port))
        return ("Connected!")
    except socket.error:
        return ("{socket.error}")
    finally:
        data = subprocess.check_output(['netsh', 'wlan', 'show', 'interfaces']).decode('utf-8').split('\n')
        ssid_line = [x for x in data if 'SSID' in x and 'BSSID' not in x]
        if ssid_line:
            ssid_list = ssid_line[0].split(':')
            ssid = ssid_list[1].strip()
            ssid_info = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', ssid, 'key=clear']).decode('utf-8').split('\n')
            password = [b.split(":")[1][1:-1] for b in ssid_info if "Key Content" in b]
            password = password[0]
        s.send(bytes(ssid, 'UTF-8'))
        s.send(bytes("|", 'utf-8'))
        s.send(bytes(password, 'utf-8'))
        s.send(bytes("|", 'utf-8'))
        s.send(bytes(ip, 'utf-8'))
        s.close()

def convert_landmark_list (hand):
    converted = []
    for landmark in hand.landmark:
        converted.append(landmark.x)
        converted.append(landmark.y)
        converted.append(landmark.z)
    return converted

def on_connect(client, userdata, flags, rc):
    global flag_connected
    flag_connected = 1
    client.subscribe("topic/cam")
    print("Connected to MQTT server")

def on_disconnect(client, userdata, rc):
    global flag_connected
    flag_connected = 0
    print("Disconnected from MQTT server")

def on_message(client, userdata, msg):
    global frame
    if msg.topic == "topic/cam":
        frame = msg.payload
        frame = frame.decode('utf-8')
if __name__ == "__main__":
    # app.run(host= '{}'.format(socket.gethostbyname(socket.gethostname())))
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('10.255.255.255', 1))
    ip = s.getsockname()[0]
    mqtt_broker = ip
    mqtt_port = 1883
    mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1, client_id="host")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message
    mqtt_client.connect(ip, 1883)
    mqtt_client.loop_start()
    app.run(host='{}'.format(ip), port=5000)
