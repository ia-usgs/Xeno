import bluetooth  # Make sure PyBluez or another Bluetooth library is installed

def scan_bluetooth():
    print("Scanning for Bluetooth devices...")
    nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True, flush_cache=True)
    if nearby_devices:
        print("Bluetooth devices found:", nearby_devices)
        return [{"address": addr, "name": name} for addr, name in nearby_devices]
    else:
        print("No Bluetooth devices found.")
        return None
