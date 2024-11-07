import subprocess
import os
from datetime import datetime
from utils import log_error

REMOTE_HOST = "192.168.68.62"  # Example IP for remote host
REMOTE_USER = "irvin"  # Replace with the actual username
REMOTE_PATH = "C:\\Users\\username\\Downloads\\scout_partner"  # Destination on remote host
LOCAL_FILE = "/home/pi/partner_device/scan_results.json"  # File to transfer

# Wi-Fi functions
def connect_to_wifi(ssid, password):
    try:
        subprocess.run(["nmcli", "dev", "wifi", "connect", ssid, "password", password], check=True)
        print(f"Successfully connected to {ssid}.")
        return True
    except subprocess.CalledProcessError as e:
        log_error("Network Module", f"Failed to connect to {ssid}", e)
        return False

def disconnect_wifi():
    try:
        subprocess.run(["nmcli", "dev", "disconnect", "wlan0"], check=True)
        print("Successfully disconnected from Wi-Fi.")
    except subprocess.CalledProcessError as e:
        log_error("Network Module", "Failed to disconnect Wi-Fi", e)

# Connection checking functions
def is_ethernet_connected():
    result = subprocess.run(["ip", "link", "show", "eth0"], capture_output=True, text=True)
    return "state UP" in result.stdout

def is_wifi_connected():
    result = subprocess.run(["iwconfig", "wlan0"], capture_output=True, text=True)
    return "ESSID:" in result.stdout

# File transfer function
def transfer_file():
    """Transfers the scan results JSON file to the specified remote host over SCP."""
    if not (is_ethernet_connected() or is_wifi_connected()):
        print("No network connection available. Skipping file transfer.")
        return False
    
    try:
        print(f"Starting file transfer to {REMOTE_USER}@{REMOTE_HOST} at {datetime.now().isoformat()}")
        # Use SCP command to transfer file
        scp_command = f"scp {LOCAL_FILE} {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}"
        transfer_result = os.system(scp_command)
        
        if transfer_result == 0:  # Check if the transfer was successful
            print(f"File {LOCAL_FILE} successfully transferred to {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}")
            return True
        else:
            print(f"File transfer failed with result code: {transfer_result}")
            return False
    except Exception as e:
        log_error("File Transfer", "File transfer failed", e)
        return False
