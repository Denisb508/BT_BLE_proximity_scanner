import subprocess
def scan_bt_classic():
    devices = []
    try:
        cmd = ["powershell","-Command","Get-PnpDevice -Class Bluetooth | Select-Object Status, FriendlyName"]
        output = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        for line in output.splitlines():
            if "OK" in line:
                devices.append({"name": line.strip(),"type":"classic","rssi":None})
    except Exception as e:
        print("BT Classic scan error:", e)
    return devices
