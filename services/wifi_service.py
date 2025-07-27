import json
import subprocess
import time
from utils.logger import Logger
from wifi.wifi_manager import WiFiManager

class WifiService:
    def __init__(self, creds_path="config/wifi_credentials.json", logger=None):
        self.creds_path = creds_path
        self.logger = logger or Logger(log_file="logs/scan.log")
        self.manager = WiFiManager(logger=self.logger)
        self.connected_ssid = None
        iface = self.manager.detect_active_interface()
        self.logger.log(f"[INFO] Active Wi-Fi interface detected: {iface}")


    def load_credentials(self):
        try:
            with open(self.creds_path, "r") as f:
                creds = json.load(f)
            self.logger.log(f"[INFO] Loaded {len(creds)} Wi-Fi credential sets.")
            return creds
        except Exception as e:
            self.logger.log(f"[ERROR] Failed to load Wi-Fi credentials: {e}")
            return []

    def change_mac(self, interface="wlan0"):
        try:
            self.logger.log("[INFO] Changing MAC address for wlan0.")
            subprocess.run(["sudo", "ifconfig", interface, "down"], check=True)
            subprocess.run(["sudo", "macchanger", "-r", interface], check=True)
            subprocess.run(["sudo", "ifconfig", interface, "up"], check=True)
            self.logger.log("[SUCCESS] MAC address changed successfully.")
        except subprocess.CalledProcessError as e:
            self.logger.log(f"[ERROR] Failed to change MAC address: {e}")

    def connect(self, ssid, password, attempts=3, retry_delay=5):
        if self.connected_ssid == ssid:
            self.logger.log(f"[INFO] Already on SSID: {ssid}.")
            return True

        self.manager.disconnect_wifi()
        for i in range(1, attempts+1):
            self.logger.log(f"[INFO] Connecting to SSID '{ssid}' (Attempt {i}/{attempts})")
            self.manager.ensure_wlan0_active()
            # Rescan & give it a moment
            subprocess.run(["sudo", "nmcli", "dev", "wifi", "rescan"], check=False)
            time.sleep(2)
            if self.manager.connect_to_wifi(ssid, password):
                self.logger.log(f"[SUCCESS] Connected to SSID: {ssid}")
                self.connected_ssid = ssid
                return True
            time.sleep(retry_delay)

        self.logger.log(f"[ERROR] Could not connect to SSID: {ssid} after {attempts} attempts.")
        return False

    def disconnect(self):
        self.manager.disconnect_wifi()
        self.connected_ssid = None
