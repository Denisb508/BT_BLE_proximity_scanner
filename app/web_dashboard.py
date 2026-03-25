from flask import Flask, jsonify

app = Flask(__name__)
current_devices = []
targets_status = []

@app.route("/")
def index():
    return jsonify({
        "app": "BT BLE proximity scanner v3.0",
        "devices_endpoint": "/devices",
        "targets_endpoint": "/targets",
    })

@app.route("/devices")
def devices():
    return jsonify(current_devices)

@app.route("/targets")
def targets():
    return jsonify(targets_status)
