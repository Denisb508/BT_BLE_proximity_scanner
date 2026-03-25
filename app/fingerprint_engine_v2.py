def calculate_score(device, target):
    score = 0
    name = (device.get("name") or "").lower()
    manufacturer = (device.get("brand") or device.get("manufacturer") or "").lower()
    rssi = device.get("rssi", -100)

    for candidate in target.get("ble_names", []):
        if candidate and candidate.lower() in name:
            score += 10

    for candidate in target.get("ble_manufacturers", []):
        if candidate and candidate.lower() in manufacturer:
            score += 10

    if device.get("source") == "BT Classic":
        score += 10

    min_rssi = target.get("min_rssi")
    if isinstance(rssi, (int, float)) and isinstance(min_rssi, (int, float)) and rssi >= min_rssi:
        score += 5

    return score
