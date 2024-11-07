import subprocess
import re
import requests
import nmap
import time 
from mac_vendor_lookup import MacLookup
import socket
from datetime import datetime

def get_default_gateway():
    """
    Retrieves the default gateway IP address dynamically.
    """
    result = subprocess.run(["ip", "route"], capture_output=True, text=True)
    match = re.search(r"default via (\S+)", result.stdout)
    return match.group(1) if match else None

def check_security(ssid):
    """
    Performs comprehensive security checks on the given Wi-Fi network SSID and returns the security information.
    """
    router_ip = get_default_gateway() or "192.168.1.1" 
    security_info = {
        "SSID": ssid,
        "timestamp": datetime.now().isoformat(),
        "encryption_type": "Unknown",
        "wpa_version": "Unknown",
        "mac_filtering": False,
        "ssid_cloaking": False,
        "default_credentials": False,
        "channel": None,
        "signal_strength": None,
        "client_isolation": False,
        "captive_portal": False,
        "vendor_info": None,
        "firmware_version": "Unknown",
        "open_services": [],
        "upnp_enabled": False,
        "wps_enabled": False,
        "dns_security": False,
        "ssl_tls_inspection": False,
        "bandwidth_limit": None,
        "multi_factor_authentication": False,
        "recommendations": []
    }

    print(f"Starting security checks for SSID: {ssid}")

    # Encryption and WPA Version Check
    try:
        print("Checking encryption and WPA version...")
        scan_result = subprocess.run(['iwlist', 'wlan0', 'scan'], capture_output=True, text=True)
        scan_output = scan_result.stdout

        if ssid in scan_output:
            ssid_section = scan_output.split(ssid)[1]
            security_info["encryption_type"] = "Open" if "Encryption key:off" in ssid_section else "Encrypted"
            if "WPA3" in ssid_section:
                security_info["wpa_version"] = "WPA3"
            elif "WPA2" in ssid_section:
                security_info["wpa_version"] = "WPA2"
            elif "WPA" in ssid_section:
                security_info["wpa_version"] = "WPA"
            print(f"Encryption Type: {security_info['encryption_type']}, WPA Version: {security_info['wpa_version']}")

            # Signal Strength and Channel
            signal_match = re.search(r"Signal level=-(\d+) dBm", ssid_section)
            security_info["signal_strength"] = int(signal_match.group(1)) if signal_match else None
            channel_match = re.search(r"Channel:(\d+)", ssid_section)
            security_info["channel"] = int(channel_match.group(1)) if channel_match else None
            print(f"Signal Strength: {security_info['signal_strength']} dBm, Channel: {security_info['channel']}")
    except Exception as e:
        print(f"Error checking encryption and WPA version: {e}")

    # SSID Cloaking Check
    print("Checking if SSID is cloaked...")
    security_info["ssid_cloaking"] = "<hidden>" in scan_output
    print(f"SSID Cloaking: {'Enabled' if security_info['ssid_cloaking'] else 'Disabled'}")

    # Default Credentials Check
    print("Checking for default credentials...")
    try:
        common_creds = [("admin", "admin"), ("admin", "password"), ("user", "user")]
        for username, password in common_creds:
            response = requests.get(f"http://{router_ip}", auth=(username, password), timeout=3)
            if response.status_code == 200:
                security_info["default_credentials"] = True
                print(f"Default credentials found with {username}/{password}")
                break
    except requests.exceptions.RequestException as e:
        print(f"Error checking default credentials: {e}")

    # Client Isolation Check
    print("Checking for client isolation...")
    try:
        isolation_check = subprocess.run(["ping", "-c", "1", "192.168.1.2"], capture_output=True, text=True)
        security_info["client_isolation"] = "100% packet loss" in isolation_check.stdout
        print(f"Client Isolation: {'Enabled' if security_info['client_isolation'] else 'Disabled'}")
    except Exception as e:
        print(f"Error checking network isolation: {e}")

    # Captive Portal Detection
    print("Checking for captive portal...")
    try:
        response = requests.get("http://example.com", timeout=3)
        security_info["captive_portal"] = response.status_code == 302 or "login" in response.url
        print(f"Captive Portal: {'Detected' if security_info['captive_portal'] else 'Not Detected'}")
    except requests.exceptions.RequestException as e:
        print(f"Error checking captive portal: {e}")

    # Vendor Info and Firmware Version
    print("Retrieving vendor info and firmware version...")
    try:
        mac_address = "00:11:22:33:44:55"  # Replace with actual router MAC if known
        security_info["vendor_info"] = MacLookup().lookup(mac_address)
        print(f"Vendor Info: {security_info['vendor_info']}")
    except Exception as e:
        print(f"Error checking vendor info: {e}")

    # Open Services Detection
    print("Detecting open services on the router...")
    try:
        nm = nmap.PortScanner()
        nm.scan(router_ip, arguments="-sV")
        open_services = []
        for proto in nm[router_ip].all_protocols():
            ports = nm[router_ip][proto].keys()
            open_services.extend([(proto, port) for port in ports])
        security_info["open_services"] = open_services
        print(f"Open Services: {security_info['open_services']}")
    except Exception as e:
        print(f"Error checking open services: {e}")

    # UPnP Check
    print("Checking if UPnP is enabled...")
    try:
        upnp_check = subprocess.run(["nmap", "--script", "upnp-info", router_ip], capture_output=True, text=True)
        security_info["upnp_enabled"] = "UPnP" in upnp_check.stdout
        print(f"UPnP: {'Enabled' if security_info['upnp_enabled'] else 'Disabled'}")
    except Exception as e:
        print(f"Error checking UPnP: {e}")

    # WPS Check
    print("Checking if WPS is enabled...")
    try:
        wps_check = subprocess.run(["wash", "-i", "wlan0", "-C"], capture_output=True, text=True)
        security_info["wps_enabled"] = ssid in wps_check.stdout
        print(f"WPS: {'Enabled' if security_info['wps_enabled'] else 'Disabled'}")
    except FileNotFoundError:
        print("Error checking WPS: 'wash' tool not found. Install with 'sudo apt-get install reaver'.")

    # DNS Security Check
    print("Checking DNS security...")
    try:
        response = subprocess.run(["dig", "+dnssec", "example.com"], capture_output=True, text=True)
        security_info["dns_security"] = "ad" in response.stdout
        print(f"DNS Security (DNSSEC): {'Enabled' if security_info['dns_security'] else 'Disabled'}")
    except FileNotFoundError:
        print("Error checking DNS security: 'dig' tool not found. Install with 'sudo apt-get install dnsutils'.")

    # SSL/TLS Inspection Check
    print("Checking for SSL/TLS inspection...")
    try:
        tls_check = requests.get("https://example.com", timeout=3)
        security_info["ssl_tls_inspection"] = "certificate" in tls_check.url or "insecure" in tls_check.url
        print(f"SSL/TLS Inspection: {'Detected' if security_info['ssl_tls_inspection'] else 'Not Detected'}")
    except requests.exceptions.RequestException as e:
        print(f"Error checking SSL/TLS inspection: {e}")

    # Bandwidth Limit Check
    print("Checking for bandwidth throttling...")
    try:
        response_time_start = time.time()
        requests.get("http://speedtest.net", timeout=3)
        response_time_end = time.time()
        if (response_time_end - response_time_start) > 5:
            security_info["bandwidth_limit"] = "Potentially throttled"
            print("Bandwidth Limit: Potentially Throttled")
    except requests.exceptions.RequestException as e:
        print(f"Error checking bandwidth limit: {e}")

    #print("Wi-Fi Security Info:", security_info)
    return security_info
