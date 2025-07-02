import os
import time
import logging
# Suppress debug logs from Pillow (PIL)
logging.getLogger("PIL").setLevel(logging.WARNING)
from wifi.wifi_manager import WiFiManager
from utils.logger import Logger
from scans.nmap_scanner import run_nmap_scan
from utils.html_logger import HTMLLogger
from attacks.recon import Recon
from attacks.vulnerability_scan import VulnerabilityScanner
from attacks.exploit_tester import ExploitTester
from attacks.file_stealer import FileStealer
from utils.display import EPaperDisplay
from utils.image_state_manager import ImageStateManager
import subprocess

def get_own_ip():
    """
    Detect and return the Raspberry Pi's active IP address.
    
    Uses 'ip route get 1.1.1.1' to determine the IP address used for outbound connections.
    This method is reliable even when MAC addresses change between Wi-Fi sessions.
    
    Returns:
        str or None: The Pi's current IP address if successfully detected, otherwise None.
    
    Raises:
        Exception: If the command fails or output cannot be parsed.
    """
    try:
        result = subprocess.run(["ip", "route", "get", "1.1.1.1"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              text=True)
        if result.returncode == 0:
            # Parse output to extract source IP
            # Expected format: "1.1.1.1 via 192.168.1.1 dev wlan0 src 192.168.1.100 ..."
            output = result.stdout.strip()
            if "src" in output:
                own_ip = output.split("src")[-1].split()[0].strip()
                return own_ip
        return None
    except Exception as e:
        print(f"[ERROR] Failed to detect own IP address: {e}")
        return None

def load_ssh_credentials():
    """
    Load SSH credentials from predefined paths in the project directory.

    Searches in the following order:
        - /home/pi/xeno/config/ssh_default_credentials.txt
        - /root/ssh_default_credentials.txt

    Returns:
        list: A list of dictionaries with SSH credentials, where each dictionary contains:
            - username (str): The username for SSH login.
            - password (str): The password for SSH login.

    Raises:
        Exception: If the file cannot be read or is improperly formatted.
    """

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
    """
    Load Wi-Fi credentials from predefined paths in the project directory.

    Searches in the following order:
        - /home/pi/xeno/config/wifi_credentials.json
        - /root/wifi_credentials.json

    Returns:
        list: A list of dictionaries with Wi-Fi credentials, where each dictionary contains:
            - SSID (str): The Wi-Fi network name.
            - Password (str): The Wi-Fi network password.

    Raises:
        Exception: If the file cannot be read or is improperly formatted.
    """

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

def initialize_display_template(display, current_ssid="Not Connected", stats=None):
    """
    Initialize the e-paper display with a basic template.

    Parameters:
        display (EPaperDisplay): The e-paper display object to update.
        current_ssid (str): The name of the current Wi-Fi network (default: "Not Connected").
        stats (dict): A dictionary with stats on targets, vulnerabilities, exploits, and files.

    Default Stats:
        - targets: 0
        - vulns: 0
        - exploits: 0
        - files: 0

    Raises:
        Exception: If an error occurs during initialization or image rendering.
"""

    if stats is None:
        stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}  # Default stats
    try:
        from PIL import Image
        placeholder_image = Image.new('1', (60, 60), color=255)  # Blank image
        prepared_image = display.prepare_image(placeholder_image)
        layout = display.draw_layout(prepared_image, current_ssid=current_ssid, current_status="Initializing...", stats=stats)
        display.display_image(layout, use_partial_update=False)  # Full refresh for initialization
        print("[INFO] Template initialized.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize display template: {e}")

def update_display_state(self, state_manager, state, current_ssid="SSID",
                         current_status="", stats=None, use_partial_update=True):
    """
    Update the e-paper display with the current workflow state.

    Parameters:
        self (EPaperDisplay): The e-paper display object to update.
        state_manager (ImageStateManager): Manages workflow states and images.
        state (str): The current workflow state (e.g., "scanning", "analyzing").
        current_ssid (str): The name of the current Wi-Fi network.
        current_status (str): The current status message to display.
        stats (dict): A dictionary with stats on targets, vulnerabilities, exploits, and files.
        use_partial_update (bool): Whether to perform a partial refresh (default: True).

    Raises:
        Exception: If the display update fails.
"""

    if stats is None:
        stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}

    try:
        # Log the current state and refresh mode
        logging.info(f"Updating display: state={state}, partial_refresh={use_partial_update}")

        # Update workflow state and load corresponding image and message
        state_manager.set_state(state)
        image, xeno_message = state_manager.get_image_and_message_for_current_state()
        prepared_image = self.prepare_image(image)

        # Initialize the display in the correct mode
        if use_partial_update:
            # Partial refresh does not require reinitialization
            logging.debug("Partial refresh mode: Skipping reinitialization.")
        else:
            # Full refresh requires initialization to default mode
            self.initialize(partial_refresh=False)

        # Combine the current status with the Xenomorph message
        full_status = f"{current_status}\n{xeno_message}"

        # Render layout and update display
        layout = self.draw_layout(prepared_image, current_ssid=current_ssid,
                                  current_status=full_status, stats=stats)
        self.display_image(layout, use_partial_update=use_partial_update)

        # Log success
        logging.info(f"State updated successfully: {state}, partial_refresh={use_partial_update}")
    except Exception as e:
        logging.error(f"Failed to update display: {e}")

def run_scans(logger, wifi_manager, html_logger, display, state_manager):
    """
    Perform the scanning and processing logic for the workflow.

    Parameters:
        logger (Logger): Logger for recording workflow progress.
        wifi_manager (WiFiManager): Manages Wi-Fi connections.
        html_logger (HTMLLogger): Generates HTML logs of scan results.
        display (EPaperDisplay): Updates the e-paper display.
        state_manager (ImageStateManager): Manages workflow states and images.

    Workflow:
        1. Initializes the display with default stats.
        2. Loads Wi-Fi and SSH credentials.
        3. Connects to Wi-Fi networks and performs scans.
        4. Runs reconnaissance, vulnerability scans, and exploit testing.
        5. Attempts file-stealing on discovered devices.
        6. Updates the e-paper display dynamically with results.

    Raises:
        Exception: If any critical errors occur during scanning.
"""

    stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}  # Initialize stats

    # Full refresh for the initial template
    initialize_display_template(display, current_ssid="Not Connected", stats=stats)

    wifi_credentials = load_wifi_credentials()
    if not wifi_credentials:
        logger.log("[ERROR] No Wi-Fi credentials loaded. Ensure the file exists in either config or root.")
        return

    ssh_credentials = load_ssh_credentials()
    if not ssh_credentials:
        logger.log("[ERROR] No SSH credentials loaded. Ensure the file exists in either config or root.")
        return

    connected_ssid = None  # Track the currently connected SSID

    for network in wifi_credentials:
        ssid = network.get("SSID")
        password = network.get("Password")

        if not ssid or not password:
            continue

        # Skip reconnection if already connected to the same SSID
        if connected_ssid == ssid:
            logger.log(f"[INFO] Already connected to SSID: {ssid}. Skipping reconnection.")
        else:
            wifi_manager.disconnect_wifi()

            for attempt in range(3):
                # Partial refresh for connecting to Wi-Fi
                update_display_state(
                    display,
                    state_manager,
                    "scanning",
                    current_ssid=ssid,
                    current_status="Connecting to Wi-Fi",
                    stats=stats,
                    use_partial_update=True
                )
                logger.log(f"[INFO] Attempting to connect to SSID: {ssid} (Attempt {attempt + 1}/3)")
                if wifi_manager.connect_to_wifi(ssid, password):
                    logger.log(f"[SUCCESS] Connected to SSID: {ssid}")
                    connected_ssid = ssid
                    break
            else:
                logger.log(f"[WARNING] Failed to connect to SSID: {ssid}.")
                update_display_state(
                    display,
                    state_manager,
                    "fallback",
                    current_ssid=ssid,
                    current_status="Connection failed. Retrying next...",
                    stats=stats,
                    use_partial_update=True
                )
                continue

        # Run Nmap scan
        logger.log(f"[INFO] Running nmap scan for network: {ssid}")
        update_display_state(
            display,
            state_manager,
            "analyzing",
            current_ssid=ssid,
            current_status="Scanning the network",
            stats=stats,
            use_partial_update=True
        )
        scan_result = run_nmap_scan("192.168.1.0/24", logger=logger)
        stats["targets"] += len(scan_result["discovered_ips"])  # Increment Targets
        html_logger.save_scan_result_to_json(ssid, scan_result["raw_output"])

        # Detect and filter out own IP address to prevent self-targeting
        own_ip = get_own_ip()
        if own_ip:
            logger.log(f"[INFO] Detected own IP address: {own_ip}")
            if own_ip in scan_result["discovered_ips"]:
                scan_result["discovered_ips"].remove(own_ip)
                logger.log(f"[INFO] Removed own IP {own_ip} from target list (skipped: self)")
                stats["targets"] -= 1  # Adjust target count since we removed one
        else:
            logger.log("[WARNING] Could not detect own IP address - proceeding with all discovered IPs")

        # Recon Phase
        recon = Recon(logger=logger)
        parsed_devices = []  # List to store structured device data

        for ip in scan_result["discovered_ips"]:
            update_display_state(
                display,
                state_manager,
                "reconnaissance",
                current_ssid=ssid,
                current_status=f"Scanning IP {ip}",
                stats=stats,
                use_partial_update=True
            )

            # Detect OS during reconnaissance
            os_detected = recon.detect_os(ip)
            if "timed out" in scan_result.get("raw_output", "") or os_detected is None:
                logger.log(f"[ERROR] OS detection returned None for IP {ip}. Defaulting to 'Unknown'.")
                os_type = "Timeout"
            else:
                os_type = os_detected

            # Parse devices from raw Nmap result
            for line in scan_result["raw_output"].split("\n"):
                if f"Nmap scan report for {ip}" in line:
                    # Extract MAC address, vendor, and IP
                    mac_address = "Unknown"
                    vendor = "Unknown"
                    next_lines = scan_result["raw_output"].split("\n")
                    for next_line in next_lines:
                        if "MAC Address" in next_line:
                            mac_address = next_line.split(" ")[2].strip()
                            vendor = " ".join(next_line.split(" ")[3:]).strip("()")
                            break

                    # Append structured data
                    parsed_devices.append({
                        "ip": ip,
                        "mac": mac_address,
                        "vendor": vendor,
                        "os_version": os_type
                    })

        # Save parsed devices to the JSON file
        scan_result["devices"] = parsed_devices
        html_logger.save_scan_result_to_json(ssid, scan_result)

        # Vulnerability Scan Phase
        vuln_scanner = VulnerabilityScanner(logger=logger)
        vulnerabilities = {}
        for ip in scan_result["discovered_ips"]:
            update_display_state(
                display,
                state_manager,
                "investigating",
                current_ssid=ssid,
                current_status="Running vulnerability scan",
                stats=stats,
                use_partial_update=True
            )
            vuln_results = vuln_scanner.run_scan(ip, ssid=ssid, html_logger=html_logger)
            if vuln_results:
                stats["vulns"] += len(vuln_results)
                vulnerabilities[ip] = vuln_results

        # Exploit Testing Phase
        exploit_tester = ExploitTester(logger=logger)
        for ip, vuln_data in vulnerabilities.items():
            for vuln in vuln_data["vulnerabilities"]:
                logger.log(f"[INFO] Running exploit testing on IP: {ip} for vulnerability: {vuln}")
                update_display_state(
                    display,
                    state_manager,
                    "attacking",
                    current_ssid=ssid,
                    current_status="Running exploit tests",
                    stats=stats,
                    use_partial_update=True
                )
                exploit_tester.run_exploit_testing(
                    service_data=vuln,
                    target_ip=ip,
                    ssid=ssid,
                    html_logger=html_logger,
                )
                update_display_state(
                    display,
                    state_manager,
                    "validating",
                    current_ssid=ssid,
                    current_status="Validating exploit results...",
                    stats=stats,
                    use_partial_update=True
                )
                stats["exploits"] += 1

        # File Stealing Phase
        file_stealer = FileStealer(logger=logger)
        for ip in vulnerabilities.keys():
            update_display_state(
                display,
                state_manager,
                "attacking",
                current_ssid=ssid,
                current_status="Stealing files",
                stats=stats,
                use_partial_update=True
            )
            successful = False
            for creds in ssh_credentials:
                # Pass OS type to the file stealer
                if file_stealer.steal_files(
                    target_ip=ip,
                    username=creds["username"],
                    password=creds["password"],
                    os_type=os_type
                ):
                    successful = True
                    stats["files"] += 3  # Increment files per successful steal
                    break

            if successful:
                logger.log(f"[SUCCESS] File stealing successful for IP: {ip}")
                wifi_manager.disconnect_wifi()
                connected_ssid = None  # Reset connected SSID after disconnecting
                change_mac_address(logger)

    # Full refresh after workflow completion
    update_display_state(
        display,
        state_manager,
        "success",
        current_ssid="Completed Network",
        current_status="Workflow Complete",
        stats=stats,
        use_partial_update=False  # Full refresh to clear any ghosting
    )

def change_mac_address(logger):
    """
    Change the MAC address of the `wlan0` interface.

    Parameters:
        logger (Logger): Logger for recording progress and errors.

    Workflow:
        1. Brings the `wlan0` interface down.
        2. Uses `macchanger` to randomly set a new MAC address.
        3. Brings the interface back up.

    Raises:
        subprocess.CalledProcessError: If any command fails during the process.
"""

    try:
        logger.log("[INFO] Changing MAC address for wlan0.")
        subprocess.run(["sudo", "ifconfig", "wlan0", "down"], check=True)
        subprocess.run(["sudo", "macchanger", "-r", "wlan0"], check=True)
        subprocess.run(["sudo", "ifconfig", "wlan0", "up"], check=True)
        logger.log("[SUCCESS] MAC address changed successfully.")
    except subprocess.CalledProcessError as e:
        logger.log(f"[ERROR] Failed to change MAC address: {str(e)}")

def main():
    """
    The main entry point for the Xeno project.

    Initializes the following components:
        - Logger: Handles logging for the application.
        - WiFiManager: Manages Wi-Fi connections.
        - HTMLLogger: Logs scan results in HTML format.
        - EPaperDisplay: Manages the e-paper display updates.
        - ImageStateManager: Tracks and manages workflow states and images.

    Workflow:
        1. Initializes display and loads required credentials.
        2. Continuously performs scans and updates results.
        3. Logs workflow progress and handles any exceptions.

    Raises:
        Exception: If a critical error occurs during initialization or execution.
    """
    os.makedirs("logs", exist_ok=True)
    logger = Logger(log_file="logs/scan.log")
    wifi_manager = WiFiManager(logger=logger)
    html_logger = HTMLLogger(output_dir="utils/html_logs", json_dir="utils/json_logs")
    display = EPaperDisplay()
    state_manager = ImageStateManager()

    try:
        display.initialize()
        while True:
            logger.log("[INFO] Starting new scanning cycle.")
            run_scans(logger, wifi_manager, html_logger, display, state_manager)
            logger.log("[INFO] Scanning cycle completed. Sleeping for 10 minutes.")
            time.sleep(600)  # Sleep for 10 minutes
    except Exception as e:
        logger.log(f"[ERROR] Fatal error occurred: {e}")
    finally:
        display.clear()  # Display is cleared
        print("[INFO] E-paper display cleared.")

if __name__ == "__main__":
    main()
