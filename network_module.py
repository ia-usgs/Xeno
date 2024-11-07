import subprocess
from ftplib import FTP
from smb.SMBConnection import SMBConnection
from utils import log_error

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

# File-grabbing functions for FTP and SMB
def access_ftp_files(server_ip, username, password):
    """Accesses files from an FTP server and downloads them."""
    try:
        print(f"Attempting to connect to FTP server at {server_ip}...")
        ftp = FTP(server_ip)
        ftp.login(user=username, passwd=password)
        print("Connected to FTP server. Listing files...")
        files = ftp.nlst()  # List files in the directory
        print(f"Files on FTP server {server_ip}: {files}")
        for file in files:
            with open(file, 'wb') as local_file:
                ftp.retrbinary(f'RETR {file}', local_file.write)
                print(f"Downloaded {file} from FTP server.")
        ftp.quit()
    except Exception as e:
        log_error("FTP Access", f"Failed to access files on FTP server {server_ip}", e)

def access_smb_files(server_ip, username, password, share_name):
    """Accesses files from an SMB share and downloads them."""
    try:
        print(f"Attempting to connect to SMB share at {server_ip}...")
        conn = SMBConnection(username, password, "WiFiScout", "TargetDevice", use_ntlm_v2=True)
        conn.connect(server_ip, 445)
        print("Connected to SMB server. Listing files...")
        files = conn.listPath(share_name, '/')
        for file in files:
            with open(file.filename, 'wb') as f:
                conn.retrieveFile(share_name, '/' + file.filename, f)
                print(f"Downloaded {file.filename} from SMB server.")
        conn.close()
    except Exception as e:
        log_error("SMB Access", f"Failed to access files on SMB server {server_ip}", e)
