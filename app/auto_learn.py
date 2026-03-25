from collections import defaultdict
device_history = defaultdict(int)

def track_device(device):
    key = device.get("name","unknown")
    device_history[key] += 1

def get_suggestions(min_seen=10):
    return [{"name":k,"seen":v} for k,v in device_history.items() if v>=min_seen]
