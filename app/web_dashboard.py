from flask import Flask, jsonify
app = Flask(__name__)

current_devices = []
targets_status = []

@app.route("/")
def index():
    return "BT BLE proximity scanner v3.0"

@app.route("/devices")
def devices():
    return jsonify(current_devices)

@app.route("/targets")
def targets():
    return jsonify(targets_status)

def run_web():
    app.run(host="0.0.0.0", port=5000)
