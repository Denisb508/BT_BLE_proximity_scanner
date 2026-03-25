def calculate_score(device, target):
    score = 0
    name = device.get("name","")
    rssi = device.get("rssi",-100)
    manufacturer = device.get("manufacturer","")

    for n in target.get("ble_names",[]):
        if n.lower() in name.lower():
            score += 20

    for m in target.get("ble_manufacturers",[]):
        if m.lower() in manufacturer.lower():
            score += 25

    if rssi >= target.get("min_rssi",-80):
        score += 20

    if device.get("type") == "classic":
        score += 30

    return score
