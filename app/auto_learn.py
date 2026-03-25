from collections import defaultdict

_device_history = defaultdict(int)

def track_device(device):
    key = device.get("name") or device.get("address") or "unknown"
    _device_history[key] += 1

def get_suggestions(min_seen=10):
    return [
        {"name": name, "seen": count}
        for name, count in sorted(_device_history.items(), key=lambda kv: kv[1], reverse=True)
        if count >= min_seen
    ]
