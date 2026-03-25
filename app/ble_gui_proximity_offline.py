# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    import winsound
except Exception:  # pragma: no cover
    winsound = None

from bleak import BleakScanner

try:
    from scanner_bt_classic import scan_bt_classic
except Exception:  # pragma: no cover
    def scan_bt_classic():
        return []

try:
    from fingerprint_engine_v2 import calculate_score as external_calculate_score
except Exception:  # pragma: no cover
    external_calculate_score = None

try:
    from auto_learn import track_device, get_suggestions
except Exception:  # pragma: no cover
    def track_device(device):
        return None
    def get_suggestions(min_seen=10):
        return []

try:
    import web_dashboard
except Exception:  # pragma: no cover
    web_dashboard = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "ble_monitor_debug.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)

MANUFACTURERS_FILE = os.path.join(BASE_DIR, "manufacturers.json")
NAME_PATTERNS_FILE = os.path.join(BASE_DIR, "name_patterns.json")
SERVICE_UUIDS_FILE = os.path.join(BASE_DIR, "service_uuids.json")
MAC_OUI_FILE = os.path.join(BASE_DIR, "mac_oui.json")
KNOWN_DEVICES_FILE = os.path.join(BASE_DIR, "known_devices.json")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
TARGETS_FILE = os.path.join(CONFIG_DIR, "targets.json")

DEFAULT_MANUFACTURERS = {
    "6": "Microsoft", "15": "Broadcom", "76": "Apple", "117": "Samsung",
    "224": "Google", "301": "Sony", "559": "Nordic", "637": "Xiaomi",
    "595": "Huawei", "220": "Garmin", "270": "Fitbit"
}

DEFAULT_NAME_PATTERNS = [
    {"contains": ["airpods", "airpods pro", "airpods max"], "brand": "Apple", "type": "AirPods-like", "priority": 100},
    {"contains": ["iphone"], "brand": "Apple", "type": "Phone", "priority": 95},
    {"contains": ["ipad"], "brand": "Apple", "type": "Tablet", "priority": 95},
    {"contains": ["apple watch", "watch6,", "watch5,", "watch4,", "watch3,", "watch2,", "watch1,"], "brand": "Apple", "type": "Watch", "priority": 98},
    {"contains": ["airtag"], "brand": "Apple", "type": "Tag", "priority": 98},
    {"contains": ["galaxy buds", "buds live", "buds2", "buds pro"], "brand": "Samsung", "type": "Earbuds/Audio", "priority": 95},
    {"contains": ["galaxy watch", "sm-r8", "sm-r9", "gear s", "gear fit"], "brand": "Samsung", "type": "Watch", "priority": 96},
    {"contains": ["galaxy", "samsung"], "brand": "Samsung", "type": "Phone", "priority": 80},
    {"contains": ["pixel watch"], "brand": "Google", "type": "Watch", "priority": 90},
    {"contains": ["pixel"], "brand": "Google", "type": "Phone", "priority": 80},
    {"contains": ["garmin", "fenix", "forerunner", "venu", "vivomove", "vivoactive", "epix", "instinct", "descent", "marq", "approach"], "brand": "Garmin", "type": "Watch/Band", "priority": 92},
    {"contains": ["fitbit", "versa", "sense", "charge", "inspire", "luxe", "ionic"], "brand": "Fitbit", "type": "Watch/Band", "priority": 90},
    {"contains": ["amazfit", "gtr", "gts", "t-rex", "bip", "cheetah", "falcon"], "brand": "Amazfit", "type": "Watch/Band", "priority": 90},
    {"contains": ["mi band", "xiaomi watch", "xiaomi band", "redmi watch", "redmi band"], "brand": "Xiaomi", "type": "Watch/Band", "priority": 90},
    {"contains": ["huawei watch", "huawei band", "watch fit", "gt runner", "watch gt", "watch ultimate"], "brand": "Huawei", "type": "Watch/Band", "priority": 90},
    {"contains": ["oneplus watch", "opwwe", "opbb"], "brand": "OnePlus", "type": "Watch", "priority": 88},
    {"contains": ["ticwatch", "mobvoi"], "brand": "Mobvoi", "type": "Watch", "priority": 88},
    {"contains": ["suunto", "polar", "coros"], "brand": "Sports Watch", "type": "Watch/Band", "priority": 86},
    {"contains": ["jbl"], "brand": "JBL", "type": "Audio Device", "priority": 75},
    {"contains": ["sony", "wf-", "wh-"], "brand": "Sony", "type": "Audio Device", "priority": 75},
]

DEFAULT_SERVICE_UUIDS = {
    "180a": {"name": "Device Information", "hint_type": "BLE Device"},
    "180d": {"name": "Heart Rate", "hint_type": "Watch/Band"},
    "180f": {"name": "Battery Service", "hint_type": "BLE Device"},
    "1812": {"name": "Human Interface Device", "hint_type": "Input Device"},
    "1814": {"name": "Running Speed and Cadence", "hint_type": "Watch/Band"},
    "1816": {"name": "Cycling Speed and Cadence", "hint_type": "Sensor"},
    "181a": {"name": "Environmental Sensing", "hint_type": "Sensor"},
    "181b": {"name": "Body Composition", "hint_type": "Watch/Band"},
    "181c": {"name": "User Data", "hint_type": "Watch/Band"},
    "181d": {"name": "Weight Scale", "hint_type": "Watch/Band"},
    "181e": {"name": "Bond Management", "hint_type": "BLE Device"},
    "181f": {"name": "Continuous Glucose Monitoring", "hint_type": "Health Device"},
    "1820": {"name": "Internet Protocol Support", "hint_type": "BLE Device"},
    "1826": {"name": "Fitness Machine", "hint_type": "Watch/Band"},
}

DEFAULT_MAC_OUI = {
    "A4:C1:38": "Apple", "F0:99:B6": "Apple", "28:39:26": "Samsung",
    "FC:C2:DE": "Samsung", "3C:28:6D": "Google", "DC:2C:26": "Xiaomi", "88:C6:26": "Sony"
}

DEFAULT_CONFIG = {
    "app_name": "BT BLE proximity scanner",
    "mode": "mix_balanced",
    "scan_interval_sec": 0.4,
    "refresh_ms": 1000,
    "arrive_confirm_count": 2,
    "depart_timeout_sec": 20,
    "stale_device_remove_sec": 120,
    "popup_on_present": True,
    "popup_on_unknown": False,
    "log_unknown_devices": True,
    "sound_on_present": True,
    "sound_on_lost": False,
    "beep_freq": 2200,
    "beep_ms": 250,
    "show_unknown_devices": True,
    "tx_power": -59,
    "distance_exponent": 2.2,
    "enable_bt_classic": True,
    "classic_scan_interval_sec": 8,
    "auto_learn": True,
    "auto_learn_min_seen": 10,
    "web_dashboard": True,
    "web_host": "127.0.0.1",
    "web_port": 5000,
}

DEFAULT_TARGETS = {
    "targets": [
        {
            "label": "MyPhone",
            "enabled": True,
            "classic_macs": [],
            "ble_names": ["iPhone", "Galaxy", "Redmi"],
            "ble_manufacturers": ["Apple", "Samsung", "Xiaomi"],
            "service_uuids": [],
            "min_rssi": -75,
            "score_present": 60,
            "notes": "Example target profile. Replace with your own device fingerprint.",
        }
    ]
}


def average(values):
    return sum(values) / len(values) if values else None


def estimate_distance_from_rssi(rssi, tx_power=-59, n=2.2):
    if rssi is None:
        return None
    try:
        return 10 ** ((tx_power - rssi) / (10 * n))
    except Exception:
        return None


def load_json_file(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def normalize_mac(address):
    return (address or "").upper().replace("-", ":")


def get_short_uuid(uuid_text):
    value = (uuid_text or "").lower().replace("-", "")
    if value.startswith("0000") and len(value) >= 8:
        return value[4:8]
    if len(value) >= 4:
        return value[:4]
    return value


def ensure_default_db_files():
    defaults = [
        (MANUFACTURERS_FILE, DEFAULT_MANUFACTURERS),
        (NAME_PATTERNS_FILE, DEFAULT_NAME_PATTERNS),
        (SERVICE_UUIDS_FILE, DEFAULT_SERVICE_UUIDS),
        (MAC_OUI_FILE, DEFAULT_MAC_OUI),
        (KNOWN_DEVICES_FILE, {}),
        (CONFIG_FILE, DEFAULT_CONFIG),
        (TARGETS_FILE, DEFAULT_TARGETS),
    ]
    for path, data in defaults:
        if not os.path.exists(path):
            save_json_file(path, data)


def detect_from_name_patterns(name):
    name_l = (name or "").lower()
    best_match = None
    best_priority = -1
    for item in NAME_PATTERNS:
        contains = item.get("contains", [])
        priority = item.get("priority", 0)
        for pattern in contains:
            if pattern.lower() in name_l and priority > best_priority:
                best_match = item
                best_priority = priority
    return best_match


def get_brand_watch_hint(brand, name, service_uuids, manufacturer_ids=None):
    brand_l = (brand or "").lower()
    name_l = (name or "").lower()
    manufacturer_ids = manufacturer_ids or []
    short_uuids = {get_short_uuid(x) for x in (service_uuids or [])}
    watch_words = ["watch", "band", "fit", "tracker", "fenix", "forerunner", "venu", "versa", "sense", "bip", "gtr", "gts", "ticwatch", "vivoactive", "vivomove", "instinct", "epix"]
    watch_services = {"180d", "1814", "181b", "181c", "181d", "1826"}
    if any(w in name_l for w in watch_words) or (short_uuids & watch_services):
        return True
    if brand_l in {"garmin", "fitbit", "amazfit", "mobvoi"}:
        return True
    if brand_l == "huawei" and ("watch" in name_l or "band" in name_l or short_uuids & watch_services):
        return True
    if brand_l == "samsung" and ("watch" in name_l or any(s in name_l for s in ["sm-r8", "sm-r9", "gear fit", "gear s"]) or short_uuids & watch_services):
        return True
    if brand_l == "apple" and ("watch" in name_l or 76 in manufacturer_ids or "180d" in short_uuids):
        return True
    if brand_l == "google" and ("pixel watch" in name_l or short_uuids & watch_services):
        return True
    return False


def reload_databases():
    global MANUFACTURERS, NAME_PATTERNS, SERVICE_UUIDS_DB, MAC_OUI_DB, KNOWN_DEVICES, CONFIG, TARGETS
    MANUFACTURERS = load_json_file(MANUFACTURERS_FILE, DEFAULT_MANUFACTURERS)
    NAME_PATTERNS = load_json_file(NAME_PATTERNS_FILE, DEFAULT_NAME_PATTERNS)
    SERVICE_UUIDS_DB = load_json_file(SERVICE_UUIDS_FILE, DEFAULT_SERVICE_UUIDS)
    MAC_OUI_DB = load_json_file(MAC_OUI_FILE, DEFAULT_MAC_OUI)
    KNOWN_DEVICES = load_json_file(KNOWN_DEVICES_FILE, {})
    KNOWN_DEVICES = {normalize_mac(k): v for k, v in KNOWN_DEVICES.items()}
    CONFIG = DEFAULT_CONFIG | load_json_file(CONFIG_FILE, DEFAULT_CONFIG)
    TARGETS = load_json_file(TARGETS_FILE, DEFAULT_TARGETS).get("targets", DEFAULT_TARGETS["targets"])


def save_known_devices():
    save_json_file(KNOWN_DEVICES_FILE, KNOWN_DEVICES)


def save_device_as_known(address, name, brand, device_type, notes=""):
    address = normalize_mac(address)
    KNOWN_DEVICES[address] = {
        "name": name or "Unknown",
        "brand": brand or "Unknown",
        "type": device_type or "Unknown",
        "notes": notes or "",
    }
    save_known_devices()


def save_target_profile(profile):
    data = load_json_file(TARGETS_FILE, DEFAULT_TARGETS)
    targets = data.get("targets", [])
    replaced = False
    for idx, item in enumerate(targets):
        if item.get("label") == profile.get("label"):
            targets[idx] = profile
            replaced = True
            break
    if not replaced:
        targets.append(profile)
    save_json_file(TARGETS_FILE, {"targets": targets})
    reload_databases()


def detect_brand(device, advertisement_data):
    address = normalize_mac(getattr(device, "address", ""))
    name = device.name or getattr(advertisement_data, "local_name", "") or ""
    manufacturer_data = getattr(advertisement_data, "manufacturer_data", {}) or {}
    known = KNOWN_DEVICES.get(address)
    if known and known.get("brand"):
        return known["brand"]
    for company_id in manufacturer_data.keys():
        brand = MANUFACTURERS.get(str(company_id))
        if brand:
            return brand
    oui = address[:8]
    if oui in MAC_OUI_DB:
        return MAC_OUI_DB[oui]
    match = detect_from_name_patterns(name)
    if match and match.get("brand"):
        return match["brand"]
    return "Unknown"


def detect_device_type(device, advertisement_data, brand):
    address = normalize_mac(getattr(device, "address", ""))
    name = device.name or getattr(advertisement_data, "local_name", "") or ""
    manufacturer_data = getattr(advertisement_data, "manufacturer_data", {}) or {}
    service_uuids = getattr(advertisement_data, "service_uuids", []) or []
    manufacturer_ids = list(manufacturer_data.keys())
    known = KNOWN_DEVICES.get(address)
    if known and known.get("type"):
        return known["type"]
    match = detect_from_name_patterns(name)
    if match and match.get("type"):
        return match["type"]
    for uuid in service_uuids:
        info = SERVICE_UUIDS_DB.get(get_short_uuid(uuid))
        if info and info.get("hint_type"):
            hint = info["hint_type"]
            if hint == "Watch/Band" and get_brand_watch_hint(brand, name, service_uuids, manufacturer_ids):
                return f"{brand} Watch-like" if brand and brand != "Unknown" else "Watch/Band"
            return hint
    name_l = (name or "").lower()
    if brand == "Apple":
        if "watch" in name_l:
            return "Apple Watch-like"
        if "iphone" in name_l or "ipad" in name_l:
            return "Apple Device"
        if 76 in manufacturer_data:
            return "Apple BLE Device"
    if brand == "Samsung":
        if "buds" in name_l:
            return "Galaxy Buds-like"
        if get_brand_watch_hint(brand, name, service_uuids, manufacturer_ids):
            return "Samsung Watch-like"
        return "Samsung Device"
    if brand in ("Garmin", "Fitbit", "Amazfit", "Huawei", "Mobvoi"):
        return f"{brand} Watch-like" if get_brand_watch_hint(brand, name, service_uuids, manufacturer_ids) else "Watch/Band"
    if brand in ("Sony", "JBL"):
        return "Audio Device"
    if get_brand_watch_hint(brand, name, service_uuids, manufacturer_ids):
        return f"{brand} Watch-like" if brand and brand != "Unknown" else "Watch/Band"
    if service_uuids:
        return "BLE Device"
    return "Unknown"


def detect_confidence(device, advertisement_data, brand, device_type):
    address = normalize_mac(getattr(device, "address", ""))
    name = device.name or getattr(advertisement_data, "local_name", "") or ""
    manufacturer_data = getattr(advertisement_data, "manufacturer_data", {}) or {}
    if address in KNOWN_DEVICES:
        return "Saved"
    for company_id in manufacturer_data.keys():
        if str(company_id) in MANUFACTURERS:
            return "High"
    if address[:8] in MAC_OUI_DB:
        return "Medium"
    if detect_from_name_patterns(name):
        return "Medium"
    service_uuids = getattr(advertisement_data, "service_uuids", []) or []
    manufacturer_ids = list(manufacturer_data.keys())
    if get_brand_watch_hint(brand, name, service_uuids, manufacturer_ids):
        return "Medium"
    if brand != "Unknown" or device_type != "Unknown":
        return "Low"
    return "Unknown"


def make_device_record(device, advertisement_data, now):
    address = normalize_mac(getattr(device, "address", "Unknown")) or "Unknown"
    adv_name = getattr(advertisement_data, "local_name", None)
    name = device.name or adv_name or "Unknown"
    rssi = getattr(device, "rssi", None)
    brand = detect_brand(device, advertisement_data)
    device_type = detect_device_type(device, advertisement_data, brand)
    confidence = detect_confidence(device, advertisement_data, brand, device_type)
    service_uuids = getattr(advertisement_data, "service_uuids", []) or []
    manufacturer_data = getattr(advertisement_data, "manufacturer_data", {}) or {}

    saved = KNOWN_DEVICES.get(address)
    if saved:
        if saved.get("name") and saved["name"] != "Unknown":
            name = saved["name"]
        brand = saved.get("brand", brand)
        device_type = saved.get("type", device_type)
        confidence = "Saved"

    return {
        "name": name,
        "brand": brand,
        "type": device_type,
        "confidence": confidence,
        "address": address,
        "rssi": rssi,
        "last_seen": now,
        "first_seen": now,
        "seen_count": 1,
        "service_uuids": service_uuids,
        "manufacturer_ids": list(manufacturer_data.keys()),
        "source": "BLE",
    }


def score_target(target, dev):
    reasons = []
    score = 0
    label = target.get("label", "Target")

    addr = normalize_mac(dev.get("address"))
    names = [x.lower() for x in target.get("ble_names", []) if x]
    manufacturers = [x.lower() for x in target.get("ble_manufacturers", []) if x]
    target_uuids = {get_short_uuid(x) for x in target.get("service_uuids", []) if x}
    dev_uuids = {get_short_uuid(x) for x in dev.get("service_uuids", []) if x}
    dev_name_l = (dev.get("name") or "").lower()
    dev_brand_l = (dev.get("brand") or "").lower()
    rssi = dev.get("rssi")
    min_rssi = target.get("min_rssi")

    if addr and addr in [normalize_mac(x) for x in target.get("classic_macs", []) if x]:
        score += 40
        reasons.append("classic MAC")
    if any(name and name in dev_name_l for name in names):
        score += 20
        reasons.append("name")
    if any(m and m == dev_brand_l for m in manufacturers):
        score += 25
        reasons.append("manufacturer")
    if target_uuids and (target_uuids & dev_uuids):
        score += 15
        reasons.append("service UUID")
    if rssi is not None and min_rssi is not None and rssi >= min_rssi:
        score += 20
        reasons.append("RSSI")
    elif rssi is not None and min_rssi is None and rssi >= -72:
        score += 15
        reasons.append("RSSI")

    if dev.get("confidence") == "Saved":
        score += 10
        reasons.append("saved")
    if dev.get("seen_count", 0) >= 2:
        score += 10
        reasons.append("repeat")

if external_calculate_score:
    try:
        score += int(external_calculate_score(dev, target))
        reasons.append("fingerprint_v2")
    except Exception:
        logging.exception("external_calculate_score failed")

    return {
        "label": label,
        "score": score,
        "reasons": reasons,
        "score_present": int(target.get("score_present", 60)),
        "device": dev,
    }


def enqueue_popup(title, text):
    ui_queue.put(("popup", title, text))


def enqueue_status(text):
    ui_queue.put(("status", text))


def beep_once(freq, ms):
    if winsound is None:
        return
    try:
        winsound.Beep(int(freq), int(ms))
    except Exception:
        logging.exception("Beep failed")


def detection_callback(device, advertisement_data):
    now = time.time()
    record = make_device_record(device, advertisement_data, now)
    if CONFIG.get("auto_learn", True):
        track_device(record)
    address = record["address"]
    with devices_lock:
        if address not in devices:
            devices[address] = record
            if CONFIG.get("log_unknown_devices", True):
                logging.info("New device seen: %s | %s | %s", record["name"], record["brand"], address)
        else:
            info = devices[address]
            info.update({
                "last_seen": now,
                "rssi": record["rssi"],
                "brand": record["brand"],
                "type": record["type"],
                "confidence": record["confidence"],
                "service_uuids": record["service_uuids"],
                "manufacturer_ids": record["manufacturer_ids"],
                "source": "BLE",
            })
            info["seen_count"] = info.get("seen_count", 0) + 1
            if (info.get("name") in (None, "", "Unknown")) and record["name"] != "Unknown":
                info["name"] = record["name"]


class PresenceEngine:
    def __init__(self):
        self.state = {}

    def evaluate(self):
        now = time.time()
        global presence_state
        present_summaries = []
        absent_labels = []

        with devices_lock:
            stale_age = float(CONFIG.get("stale_device_remove_sec", 120))
            stale = [addr for addr, info in devices.items() if now - info.get("last_seen", now) > stale_age]
            for addr in stale:
                devices.pop(addr, None)
            snapshot = list(devices.values())

        enabled_targets = [t for t in TARGETS if t.get("enabled", True)]
        if not enabled_targets:
            enqueue_status("No targets configured. Add or import a target profile.")
            return [], []

        for target in enabled_targets:
            label = target.get("label", "Target")
            best = None
            for dev in snapshot:
                result = score_target(target, dev)
                if best is None or result["score"] > best["score"]:
                    best = result

            threshold = int(target.get("score_present", 60))
            target_state = self.state.setdefault(label, {
                "status": "ABSENT",
                "confirm_hits": 0,
                "last_match_time": 0.0,
                "last_device": None,
                "last_popup_key": None,
            })

            if best and best["score"] >= threshold:
                target_state["confirm_hits"] += 1
                target_state["last_match_time"] = now
                target_state["last_device"] = best["device"]
                if target_state["confirm_hits"] >= int(CONFIG.get("arrive_confirm_count", 2)):
                    old_status = target_state["status"]
                    target_state["status"] = "PRESENT"
                    present_summaries.append((target, best, target_state))
                    if old_status != "PRESENT":
                        msg = (
                            f"{label} is PRESENT | score={best['score']} | device={best['device'].get('name')} | "
                            f"RSSI={best['device'].get('rssi')} | reasons={', '.join(best['reasons']) or '-'}"
                        )
                        logging.info(msg)
                        if CONFIG.get("popup_on_present", True):
                            popup_key = f"{label}:{best['device'].get('address')}"
                            if target_state.get("last_popup_key") != popup_key:
                                enqueue_popup("Target PRESENT", msg)
                                target_state["last_popup_key"] = popup_key
                        if CONFIG.get("sound_on_present", True):
                            beep_once(CONFIG.get("beep_freq", 2200), CONFIG.get("beep_ms", 250))
                else:
                    target_state["status"] = "POSSIBLE"
            else:
                target_state["confirm_hits"] = 0
                timeout = float(CONFIG.get("depart_timeout_sec", 20))
                old_status = target_state["status"]
                last_match = target_state.get("last_match_time", 0.0)
                if old_status == "PRESENT" and (now - last_match) <= timeout:
                    target_state["status"] = "LOST"
                else:
                    if old_status in ("PRESENT", "LOST") and (now - last_match) > timeout:
                        logging.info("%s became ABSENT", label)
                        if CONFIG.get("sound_on_lost", False):
                            beep_once(900, 150)
                    target_state["status"] = "ABSENT"
                    target_state["last_popup_key"] = None
                absent_labels.append(label)

        if present_summaries:
            text_parts = []
            for target, best, _target_state in present_summaries:
                dev = best["device"]
                dist = estimate_distance_from_rssi(
                    dev.get("rssi"),
                    CONFIG.get("tx_power", -59),
                    CONFIG.get("distance_exponent", 2.2),
                )
                dist_txt = "?" if dist is None else f"{dist:.1f} m"
                text_parts.append(
                    f"{target.get('label')}: PRESENT | {dev.get('name')} | {dev.get('brand')} | RSSI {dev.get('rssi')} | ~{dist_txt} | score {best['score']}"
                )
            enqueue_status(" | ".join(text_parts))
        else:
            status_parts = [f"{k}: {v['status']}" for k, v in self.state.items()]
            enqueue_status("No confirmed targets present. " + " | ".join(status_parts))

        presence_state = {k: dict(v) for k, v in self.state.items()}
        return present_summaries, absent_labels


async def ble_loop():
    scanner = BleakScanner(detection_callback)
    engine = PresenceEngine()
    try:
        await scanner.start()
        enqueue_status("BLE scan is running. Mix-mode target engine loaded.")
        logging.info("BLE scanner started")
    except Exception as e:
        logging.exception("scanner.start() failed")
        enqueue_status(f"BLE start failed: {type(e).__name__}: {e}")
        enqueue_popup(
            "BLE not available",
            "BLE scan could not start.\n\n"
            f"Reason: {type(e).__name__}: {e}\n\n"
            "Check Bluetooth adapter / driver. The GUI will stay open.",
        )
        return

    try:
        while not stop_event.is_set():
            engine.evaluate()
            await asyncio.sleep(float(CONFIG.get("scan_interval_sec", 0.4)))
    finally:
        try:
            await scanner.stop()
        except Exception:
            logging.exception("scanner.stop() failed")


def run_ble_thread():
    try:
        logging.info("BLE thread entering asyncio.run")
        asyncio.run(ble_loop())
    except Exception as e:
        logging.exception("BLE thread crashed")
        enqueue_popup("BLE error", f"{type(e).__name__}: {e}")
        enqueue_status(f"BLE scan failed: {type(e).__name__}: {e}")


ensure_default_db_files()
reload_databases()

ui_queue = queue.Queue()
stop_event = threading.Event()
devices_lock = threading.Lock()
devices = {}
presence_state = {}



def update_web_dashboard_snapshot(target_rows=None):
    if not web_dashboard or not CONFIG.get("web_dashboard", True):
        return
    try:
        with devices_lock:
            web_dashboard.current_devices = sorted(
                [dict(v) for v in devices.values()],
                key=lambda x: (x.get("last_seen", 0), x.get("name", "")),
                reverse=True,
            )[:200]
        web_dashboard.targets_status = target_rows or []
    except Exception:
        logging.exception("Failed updating web dashboard snapshot")


def bt_classic_loop():
    enqueue_status("BT Classic scanner thread starting...")
    interval = float(CONFIG.get("classic_scan_interval_sec", 8))
    while not stop_event.is_set():
        try:
            now = time.time()
            found = scan_bt_classic() or []
            with devices_lock:
                for idx, dev in enumerate(found):
                    name = (dev.get("name") or f"ClassicDevice{idx}").strip()
                    address = normalize_mac(dev.get("address") or f"CLASSIC:{name}")
                    record = {
                        "name": name,
                        "brand": dev.get("manufacturer") or "Unknown",
                        "type": dev.get("device_type") or "Classic Device",
                        "confidence": "Medium",
                        "address": address,
                        "rssi": dev.get("rssi"),
                        "last_seen": now,
                        "first_seen": devices.get(address, {}).get("first_seen", now),
                        "seen_count": devices.get(address, {}).get("seen_count", 0) + 1,
                        "service_uuids": [],
                        "manufacturer_ids": [],
                        "source": "BT Classic",
                    }
                    devices[address] = record
                    if CONFIG.get("auto_learn", True):
                        track_device(record)
        except Exception:
            logging.exception("BT Classic scan failed")
        time.sleep(interval)

class BLEApp:
    def __init__(self, root):
        self.root = root
        self.root.title(CONFIG.get("app_name", "BT BLE proximity scanner") + " - Mix Mode Offline")
        self.root.geometry("1480x860")
        self.sort_column = "rssi"
        self.sort_reverse = True
        self.target_sort_column = "status"
        self.target_sort_reverse = True

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text=CONFIG.get("app_name", "BT BLE proximity scanner"), font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(top, text=f"Mode: {CONFIG.get('mode', 'mix_balanced')} | Config: {CONFIG_FILE} | Targets: {TARGETS_FILE}", foreground="gray").pack(anchor="w", pady=(2, 10))

        controls = ttk.Frame(root, padding=(10, 0, 10, 10))
        controls.pack(fill="x")
        self.filter_var = tk.StringVar()
        ttk.Label(controls, text="Filter:").pack(side="left")
        ttk.Entry(controls, textvariable=self.filter_var, width=32).pack(side="left", padx=(6, 10))
        ttk.Button(controls, text="Clear", command=self.clear_filter).pack(side="left")
        ttk.Button(controls, text="Reload DB/Config", command=self.reload_db_and_refresh).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Open DB folder", command=self.open_db_folder_info).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Save selected as known", command=self.save_selected_as_known).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Save selected as target", command=self.save_selected_as_target).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Export selected JSON", command=self.export_selected_json).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Refresh auto-learn", command=self.refresh_suggestions).pack(side="left", padx=(8, 0))

        self.status_var = tk.StringVar(value="Starting BLE scanner...")
        self.target_var = tk.StringVar(value="No target selected")
        self.dashboard_var = tk.StringVar(value=f"Dashboard: http://{CONFIG.get('web_host', '127.0.0.1')}:{CONFIG.get('web_port', 5000)}")
        self.learn_var = tk.StringVar(value="Auto-learn: waiting for devices...")
        ttk.Label(root, textvariable=self.status_var, padding=(10, 0, 10, 4)).pack(anchor="w")
        ttk.Label(root, textvariable=self.dashboard_var, padding=(10, 0, 10, 4), foreground="gray").pack(anchor="w")
        ttk.Label(root, textvariable=self.learn_var, padding=(10, 0, 10, 8), foreground="gray").pack(anchor="w")

        targets_box = ttk.LabelFrame(root, text="Target Profiles / Presence Engine", padding=10)
        targets_box.pack(fill="x", padx=10, pady=(0, 8))
        target_cols = ("label", "status", "score", "score_present", "device", "rssi", "last_seen", "reasons")
        self.target_tree = ttk.Treeview(targets_box, columns=target_cols, show="headings", height=6)
        self.target_titles = {
            "label": "Target",
            "status": "Status",
            "score": "Score",
            "score_present": "Present>=",
            "device": "Matched device",
            "rssi": "RSSI",
            "last_seen": "Last seen",
            "reasons": "Reasons",
        }
        for col in target_cols:
            self.target_tree.heading(col, text=self.target_titles[col], command=lambda c=col: self.sort_target_by_column(c))
            width = 120
            if col in ("reasons", "device"):
                width = 220
            elif col == "label":
                width = 160
            self.target_tree.column(col, width=width, anchor="w")
        self.target_tree.pack(fill="x")
        self.configure_target_tree_tags()

        devices_box = ttk.LabelFrame(root, text="Discovered Devices", padding=10)
        devices_box.pack(fill="both", expand=True, padx=10)
        cols = ("name", "brand", "type", "confidence", "address", "rssi", "last_seen", "seen_count", "source")
        self.tree = ttk.Treeview(devices_box, columns=cols, show="headings", height=24)
        self.column_titles = {
            "name": "Name",
            "brand": "Brand",
            "type": "Type",
            "confidence": "Confidence",
            "address": "Address",
            "rssi": "RSSI",
            "last_seen": "Last seen",
            "seen_count": "Seen",
            "source": "Source",
        }
        for col in cols:
            self.tree.heading(col, text=self.column_titles[col], command=lambda c=col: self.sort_by_column(c))
            width = 120
            if col == "address":
                width = 160
            elif col == "name":
                width = 200
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.configure_tree_tags()

        info = ttk.Frame(root, padding=10)
        info.pack(fill="x")
        ttk.Label(info, text=f"Log: {LOG_FILE}", foreground="gray").pack(anchor="w")
        ttk.Label(info, text="Tip: use 'Save selected as target' to build a fingerprint profile for mix-mode detection.", foreground="gray").pack(anchor="w", pady=(3, 0))

        self.filter_var.trace_add("write", lambda *args: self.refresh_tree())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.poll_ui_queue()
        self.auto_refresh()

    def sort_by_column(self, col):
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = col in ("rssi", "last_seen", "seen_count")
        self.refresh_tree()

    def sort_target_by_column(self, col):
        if self.target_sort_column == col:
            self.target_sort_reverse = not self.target_sort_reverse
        else:
            self.target_sort_column = col
            self.target_sort_reverse = col in ("score", "last_seen")
        self.refresh_target_tree()

    def sort_key(self, dev):
        col = self.sort_column or "rssi"
        if col in ("name", "brand", "type", "address", "source"):
            return (dev.get(col) or "").lower()
        if col == "confidence":
            return {"Saved": 5, "High": 4, "Medium": 3, "Low": 2, "Unknown": 1}.get(dev.get("confidence", "Unknown"), 0)
        if col == "rssi":
            return dev.get("rssi") if dev.get("rssi") is not None else -999
        if col == "last_seen":
            return dev.get("last_seen", 0)
        if col == "seen_count":
            return dev.get("seen_count", 0)
        return str(dev.get(col, ""))

    def target_sort_key(self, row):
        col = self.target_sort_column or "status"
        if col in ("label", "device", "reasons"):
            return (row.get(col) or "").lower()
        if col == "status":
            return {"PRESENT": 4, "POSSIBLE": 3, "LOST": 2, "ABSENT": 1}.get(row.get("status"), 0)
        if col in ("score", "score_present", "rssi", "last_seen"):
            return row.get(col) if row.get(col) is not None else -999
        return str(row.get(col, ""))

    def configure_tree_tags(self):
        self.tree.tag_configure("tag_saved", background="#DFF6DD")
        self.tree.tag_configure("tag_audio", background="#E8F4FF")
        self.tree.tag_configure("tag_watch", background="#EAFBE7")
        self.tree.tag_configure("tag_phone", background="#FFF4D6")
        self.tree.tag_configure("tag_tag", background="#FFE8E8")
        self.tree.tag_configure("tag_ble", background="#F3E8FF")
        self.tree.tag_configure("tag_unknown", background="#F0F0F0")

    def configure_target_tree_tags(self):
        self.target_tree.tag_configure("PRESENT", background="#CFF4D2")
        self.target_tree.tag_configure("POSSIBLE", background="#FFF3BF")
        self.target_tree.tag_configure("LOST", background="#FFE8CC")
        self.target_tree.tag_configure("ABSENT", background="#F1F3F5")

    def get_type_tag(self, dev):
        if dev.get("confidence") == "Saved":
            return "tag_saved"
        t = (dev.get("type") or "").lower()
        if any(x in t for x in ["airpods", "audio", "earbuds", "headset"]):
            return "tag_audio"
        if any(x in t for x in ["watch", "band"]):
            return "tag_watch"
        if any(x in t for x in ["phone", "tablet"]):
            return "tag_phone"
        if "tag" in t:
            return "tag_tag"
        if any(x in t for x in ["ble", "device", "sensor", "input"]):
            return "tag_ble"
        return "tag_unknown"

    def clear_filter(self):
        self.filter_var.set("")

    def reload_db_and_refresh(self):
        reload_databases()
        enqueue_status("Offline JSON databases reloaded.")
        self.refresh_tree()
        self.refresh_target_tree()

    def open_db_folder_info(self):
        messagebox.showinfo("DB folder", f"Files are stored here:\n\n{ROOT_DIR}")

    def _matches_filter(self, dev):
        text = self.filter_var.get().strip().lower()
        if not text:
            return True
        return any(text in str(dev.get(key, "")).lower() for key in ["name", "brand", "type", "confidence", "address", "source"])

    def refresh_tree(self):
        current_selection = self.tree.selection()
        selected_id = current_selection[0] if current_selection else None
        for item in self.tree.get_children():
            self.tree.delete(item)
        now = time.time()
        with devices_lock:
            items = list(devices.values())
        items.sort(key=self.sort_key, reverse=self.sort_reverse)
        for dev in items:
            if not CONFIG.get("show_unknown_devices", True) and dev.get("name") == "Unknown":
                continue
            if not self._matches_filter(dev):
                continue
            age = now - dev.get("last_seen", now)
            self.tree.insert("", "end", iid=dev["address"], values=(
                dev.get("name", "Unknown"),
                dev.get("brand", "Unknown"),
                dev.get("type", "Unknown"),
                dev.get("confidence", "Unknown"),
                dev.get("address", "Unknown"),
                str(dev.get("rssi")) if dev.get("rssi") is not None else "?",
                f"{age:.1f}s ago",
                str(dev.get("seen_count", 0)),
                dev.get("source", "BLE"),
            ), tags=(self.get_type_tag(dev),))
        if selected_id and self.tree.exists(selected_id):
            self.tree.selection_set(selected_id)

    def refresh_target_tree(self):
        for item in self.target_tree.get_children():
            self.target_tree.delete(item)
        # Render last known presence state from the running engine.
        rows = []
        now = time.time()
        with devices_lock:
            snapshot = list(devices.values())
        for target in [t for t in TARGETS if t.get("enabled", True)]:
            best = None
            for dev in snapshot:
                result = score_target(target, dev)
                if best is None or result["score"] > best["score"]:
                    best = result
            label = target.get("label", "Target")
            state = presence_state.get(label, {"status": "ABSENT"})
            device_name = best["device"].get("name") if best else "-"
            last_seen = best["device"].get("last_seen") if best else None
            rows.append({
                "label": label,
                "status": state.get("status", "ABSENT"),
                "score": best["score"] if best else 0,
                "score_present": int(target.get("score_present", 60)),
                "device": device_name,
                "rssi": best["device"].get("rssi") if best else None,
                "last_seen": last_seen or 0,
                "reasons": ", ".join(best["reasons"]) if best else "",
            })
        rows.sort(key=self.target_sort_key, reverse=self.target_sort_reverse)
        for row in rows:
            age_text = "-"
            if row["last_seen"]:
                age_text = f"{now - row['last_seen']:.1f}s ago"
            self.target_tree.insert("", "end", values=(
                row["label"], row["status"], row["score"], row["score_present"], row["device"],
                row["rssi"] if row["rssi"] is not None else "?", age_text, row["reasons"]
            ), tags=(row["status"],))

    def _get_selected_dev(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("BT BLE proximity scanner", "First select a device from the list.")
            return None
        addr = selected[0]
        with devices_lock:
            dev = devices.get(addr)
        if not dev:
            messagebox.showwarning("BT BLE proximity scanner", "Selected device is no longer available.")
            return None
        return dev

    def save_selected_as_known(self):
        dev = self._get_selected_dev()
        if not dev:
            return
        name = simpledialog.askstring("Save known device", "Device name:", initialvalue=dev.get("name", "Unknown"), parent=self.root)
        if name is None:
            return
        brand = simpledialog.askstring("Save known device", "Brand:", initialvalue=dev.get("brand", "Unknown"), parent=self.root)
        if brand is None:
            return
        device_type = simpledialog.askstring("Save known device", "Type:", initialvalue=dev.get("type", "Unknown"), parent=self.root)
        if device_type is None:
            return
        notes = simpledialog.askstring("Save known device", "Notes (optional):", initialvalue=KNOWN_DEVICES.get(dev["address"], {}).get("notes", ""), parent=self.root)
        save_device_as_known(dev["address"], name, brand, device_type, notes or "")
        with devices_lock:
            if dev["address"] in devices:
                devices[dev["address"]]["name"] = name
                devices[dev["address"]]["brand"] = brand
                devices[dev["address"]]["type"] = device_type
                devices[dev["address"]]["confidence"] = "Saved"
        self.refresh_tree()
        messagebox.showinfo("Saved", f"Device saved to:\n{KNOWN_DEVICES_FILE}")

    def save_selected_as_target(self):
        dev = self._get_selected_dev()
        if not dev:
            return
        default_label = (dev.get("name") or "Target").replace(" ", "_")
        label = simpledialog.askstring("Save target profile", "Target label:", initialvalue=default_label, parent=self.root)
        if not label:
            return
        min_rssi = simpledialog.askinteger("Save target profile", "Minimum RSSI for score:", initialvalue=int(dev.get("rssi") or -75), parent=self.root)
        if min_rssi is None:
            return
        score_present = simpledialog.askinteger("Save target profile", "Score threshold for PRESENT:", initialvalue=60, parent=self.root)
        if score_present is None:
            return
        profile = {
            "label": label,
            "enabled": True,
            "classic_macs": [dev.get("address")] if dev.get("address") and dev.get("address") != "Unknown" else [],
            "ble_names": [dev.get("name")] if dev.get("name") and dev.get("name") != "Unknown" else [],
            "ble_manufacturers": [dev.get("brand")] if dev.get("brand") and dev.get("brand") != "Unknown" else [],
            "service_uuids": dev.get("service_uuids") or [],
            "min_rssi": min_rssi,
            "score_present": score_present,
            "notes": f"Created from discovered device {dev.get('address')}",
        }
        save_target_profile(profile)
        self.refresh_target_tree()
        messagebox.showinfo("Saved", f"Target profile saved to:\n{TARGETS_FILE}")

    def export_selected_json(self):
        dev = self._get_selected_dev()
        if not dev:
            return
        path = filedialog.asksaveasfilename(
            title="Export selected device to JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{dev['address'].replace(':', '_')}.json",
        )
        if not path:
            return
        export_data = {
            "name": dev.get("name"),
            "brand": dev.get("brand"),
            "type": dev.get("type"),
            "confidence": dev.get("confidence"),
            "address": dev.get("address"),
            "rssi": dev.get("rssi"),
            "service_uuids": dev.get("service_uuids"),
            "manufacturer_ids": dev.get("manufacturer_ids"),
        }
        save_json_file(path, export_data)
        messagebox.showinfo("Exported", f"Saved:\n{path}")

    def poll_ui_queue(self):
        try:
            while True:
                msg = ui_queue.get_nowait()
                kind = msg[0]
                if kind == "popup":
                    _, title, text = msg
                    messagebox.showinfo(title, text)
                elif kind == "status":
                    _, text = msg
                    self.status_var.set(text)
        except queue.Empty:
            pass
        self.root.after(300, self.poll_ui_queue)

    def auto_refresh(self):
        self.refresh_tree()
        self.refresh_target_tree()
        self.refresh_suggestions()
        rows = []
        for item in self.target_tree.get_children():
            values = self.target_tree.item(item, "values")
            rows.append({
                "label": values[0], "status": values[1], "score": values[2],
                "score_present": values[3], "device": values[4], "rssi": values[5],
                "last_seen": values[6], "reasons": values[7],
            })
        update_web_dashboard_snapshot(rows)
        self.root.after(int(CONFIG.get("refresh_ms", 1000)), self.auto_refresh)


def refresh_suggestions(self):
    suggestions = get_suggestions(int(CONFIG.get("auto_learn_min_seen", 10)))
    if not suggestions:
        self.learn_var.set("Auto-learn: no suggestions yet.")
        return
    top = sorted(suggestions, key=lambda x: x.get("seen", 0), reverse=True)[:5]
    text = " | ".join(f"{item['name']} ({item['seen']})" for item in top)
    self.learn_var.set("Auto-learn suggestions: " + text)

    def on_close(self):
        logging.info("Application closing")
        stop_event.set()
        self.root.destroy()


def main():
    logging.info("Application startup")
    if web_dashboard and CONFIG.get("web_dashboard", True):
        try:
            threading.Thread(
                target=lambda: web_dashboard.app.run(
                    host=CONFIG.get("web_host", "127.0.0.1"),
                    port=int(CONFIG.get("web_port", 5000)),
                    debug=False,
                    use_reloader=False,
                ),
                daemon=True,
            ).start()
            logging.info("Web dashboard started")
        except Exception:
            logging.exception("Failed to start web dashboard")
    root = tk.Tk()
    BLEApp(root)
    ble_thread = threading.Thread(target=run_ble_thread, daemon=True)
    ble_thread.start()
    if CONFIG.get("enable_bt_classic", True):
        threading.Thread(target=bt_classic_loop, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Fatal application error")
        raise
