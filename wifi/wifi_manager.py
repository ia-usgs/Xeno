import subprocess
import time
import json
from pathlib import Path
from utils.logger import Logger


class WiFiManager:
    def __init__(self, interface="wlan0", logger=None):
        self.interface = interface
        self.logger = logger if logger else Logger()

    def ensure_wlan0_active(self):
        """
        Ensure the wlan0 interface is active and set to managed mode.

        Workflow:
            - Checks the status of the Wi-Fi interface using `nmcli`.
            - Activates and sets the interface to managed mode if it is inactive.

        Raises:
            subprocess.CalledProcessError: If an error occurs while interacting with the `nmcli` command.
        """

        try:
            self.logger.log(f"Checking if {self.interface} is active.")
            result = subprocess.run(["sudo", "nmcli", "dev", "status"], stdout=subprocess.PIPE, text=True)
            if self.interface not in result.stdout:
                self.logger.log(f"Bringing up {self.interface} interface.")
                subprocess.run(["sudo", "nmcli", "dev", "set", self.interface, "managed", "yes"], check=True)
        except subprocess.CalledProcessError as e:
            self.logger.log(f"[ERROR] Error ensuring {self.interface} is active: {e}")

    def disconnect_wifi(self):
        """
        Disconnect the current Wi-Fi connection.

        Workflow:
            - Uses `nmcli` to disconnect the specified Wi-Fi interface.
            - Logs the result of the disconnection attempt.

        Raises:
            subprocess.CalledProcessError: If an error occurs during the disconnection process.
        """

        try:
            self.logger.log("[INFO] Disconnecting Wi-Fi interface.")
            result = subprocess.run(
                ["sudo", "nmcli", "dev", "disconnect", self.interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                self.logger.log("[INFO] Successfully disconnected from Wi-Fi.")
            else:
                self.logger.log(f"[WARNING] Failed to disconnect Wi-Fi: {result.stderr.strip()}")
        except subprocess.CalledProcessError as e:
            self.logger.log(f"[ERROR] Exception while disconnecting Wi-Fi: {e}")

    def connect_to_wifi(self, ssid, password, retry_attempts=3):
        """
        Connect to a Wi-Fi network using `nmcli`, with retry logic.

        Parameters:
            ssid (str): The name of the Wi-Fi network to connect to.
            password (str): The password for the Wi-Fi network.
            retry_attempts (int, optional): The number of retry attempts (default: 3).

        Returns:
            bool: True if the connection is successful, False otherwise.

        Workflow:
            - Ensures the Wi-Fi interface is active.
            - Rescans available Wi-Fi networks before attempting a connection.
            - Tries to connect to the specified SSID with the provided password.
            - Logs the outcome of each attempt and retries if the connection fails.

        Raises:
            subprocess.CalledProcessError: If an error occurs while executing the `nmcli` command.
        """

        self.ensure_wlan0_active()

        for attempt in range(retry_attempts):
            try:
                self.logger.log(f"[INFO] Rescanning Wi-Fi networks before connecting to SSID: {ssid}")
                subprocess.run(["sudo", "nmcli", "dev", "wifi", "rescan"], check=True)
                time.sleep(2)  # Allow time for the scan to complete

                self.logger.log(f"[INFO] Attempting to connect to SSID: {ssid} (Attempt {attempt + 1}/{retry_attempts})")
                result = subprocess.run(
                    ["sudo", "nmcli", "dev", "wifi", "connect", ssid, "password", password],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                if result.returncode == 0:
                    self.logger.log(f"[SUCCESS] Successfully connected to SSID: {ssid}")
                    return True
                else:
                    self.logger.log(f"[WARNING] Failed to connect to SSID: {ssid} | {result.stderr.strip()}")
                    if attempt < retry_attempts - 1:
                        self.logger.log(f"[INFO] Retrying connection to {ssid}...")
            except subprocess.CalledProcessError as e:
                self.logger.log(f"[ERROR] Exception occurred while connecting to SSID {ssid}: {e}")
        self.logger.log(f"[ERROR] All connection attempts to SSID {ssid} failed.")
        return False

    def run_scan(self):
        """
        Run a scan to detect available Wi-Fi networks.

        Returns:
            str: The raw output of the `nmcli` command listing available networks.

        Workflow:
            - Executes the `nmcli` command to list available Wi-Fi networks.
            - Logs the scan results.

        Raises:
            subprocess.CalledProcessError: If the scan process fails.
        """

        try:
            self.logger.log("[INFO] Scanning for Wi-Fi networks.")
            result = subprocess.run(["sudo", "nmcli", "dev", "wifi", "list"], stdout=subprocess.PIPE, text=True)
            self.logger.log(f"[INFO] Scan result:\n{result.stdout}")
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.log(f"[ERROR] Failed to scan for Wi-Fi networks: {e}")
            return ""

    def load_wifi_credentials(self):
        """
        Load Wi-Fi credentials from a JSON file.

        Returns:
            list: A list of dictionaries containing Wi-Fi credentials, where each dictionary has:
                  - SSID (str): The name of the Wi-Fi network.
                  - Password (str): The password for the Wi-Fi network.

        Workflow:
            - Reads the credentials from `config/wifi_credentials.json`.
            - Logs the result of the loading operation.

        Raises:
            FileNotFoundError: If the credentials file is not found.
            json.JSONDecodeError: If the credentials file contains invalid JSON.
        """

        credentials_file = Path("config/wifi_credentials.json")
        try:
            with open(credentials_file, "r") as file:
                credentials = json.load(file)
                self.logger.log(f"[INFO] Loaded Wi-Fi credentials from {credentials_file}.")
                return credentials
        except FileNotFoundError:
            self.logger.log(f"[ERROR] Wi-Fi credentials file not found at {credentials_file}.")
            return []
        except json.JSONDecodeError as e:
            self.logger.log(f"[ERROR] Error decoding Wi-Fi credentials JSON: {e}")
            return []

    def handle_network_transition(self, ssid, password):
        """
        Handle the process of disconnecting from the current network, connecting to a new one, and rescanning.

        Parameters:
            ssid (str): The name of the Wi-Fi network to transition to.
            password (str): The password for the Wi-Fi network.

        Workflow:
            - Disconnects from the current Wi-Fi network.
            - Attempts to connect to the specified SSID with the provided password.
            - Logs the outcome of the transition process.
        """

        self.logger.log(f"[INFO] Handling network transition for SSID: {ssid}")
        self.disconnect_wifi()
        if self.connect_to_wifi(ssid, password):
            self.logger.log(f"[INFO] Successfully transitioned to SSID: {ssid}")
        else:
            self.logger.log(f"[WARNING] Could not connect to SSID: {ssid}")
