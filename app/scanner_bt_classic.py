import subprocess

def _run_powershell(command: str) -> str:
    return subprocess.check_output(
        ["powershell", "-NoProfile", "-Command", command],
        text=True,
        stderr=subprocess.DEVNULL,
    )

def scan_bt_classic():
    devices = []
    commands = [
        "Get-PnpDevice -Class Bluetooth | Select-Object FriendlyName, Status | ConvertTo-Json -Compress",
        "Get-WmiObject Win32_PnPEntity | Where-Object {$_.Name -match 'Bluetooth'} | Select-Object Name, Status | ConvertTo-Json -Compress",
    ]
    for command in commands:
        try:
            output = _run_powershell(command).strip()
            if not output:
                continue
            import json
            parsed = json.loads(output)
            if isinstance(parsed, dict):
                parsed = [parsed]
            for item in parsed:
                name = item.get("FriendlyName") or item.get("Name")
                status = item.get("Status") or ""
                if name:
                    devices.append({
                        "name": name,
                        "status": status,
                        "type": "classic",
                        "manufacturer": "Unknown",
                        "device_type": "Classic Device",
                        "rssi": None,
                    })
            if devices:
                break
        except Exception:
            continue
    return devices
