"""
Scan workflow module for Xeno project.

This module contains the main scanning workflow that orchestrates
Wi-Fi connection, network scanning, reconnaissance, vulnerability scanning,
exploit testing, and file stealing operations.
"""

import subprocess
from scans.nmap_scanner import run_nmap_scan
from attacks.recon import Recon
from attacks.vulnerability_scan import VulnerabilityScanner
from attacks.exploit_tester import ExploitTester
from attacks.file_stealer import FileStealer
from config.config_loader import load_wifi_credentials, load_ssh_credentials
from utils.display_manager import initialize_display_template, update_display_state
from utils.network_utils import change_mac_address, get_local_ip


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
            if not _connect_to_wifi(wifi_manager, ssid, password, logger, display, state_manager, stats):
                continue
            connected_ssid = ssid

        # Run network scan and process results
        scan_result = _run_network_scan(logger, wifi_manager, display, state_manager, ssid, stats)
        if not scan_result:
            continue

        # Process discovered devices
        parsed_devices = _run_reconnaissance_phase(
            scan_result, logger, display, state_manager, ssid, stats, html_logger
        )

        # Run vulnerability scanning
        vulnerabilities = _run_vulnerability_scan_phase(
            scan_result, logger, display, state_manager, ssid, stats, html_logger
        )

        # Run exploit testing
        _run_exploit_testing_phase(
            vulnerabilities, logger, display, state_manager, ssid, stats, html_logger
        )

        # Run file stealing
        _run_file_stealing_phase(
            vulnerabilities, ssh_credentials, logger, wifi_manager, display, 
            state_manager, ssid, stats, connected_ssid
        )

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


def _connect_to_wifi(wifi_manager, ssid, password, logger, display, state_manager, stats):
    """Connect to Wi-Fi with retry logic."""
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
            return True
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
        return False


def _run_network_scan(logger, wifi_manager, display, state_manager, ssid, stats):
    """Run Nmap network scan and exclude local IP."""
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

    # Exclude our own IP from scan targets
    local_ip = get_local_ip(wifi_manager)
    if local_ip:
        scan_result["discovered_ips"] = [
            ip for ip in scan_result["discovered_ips"] if ip != local_ip
        ]
        logger.log(f"[INFO] Excluding our own {wifi_manager.interface} IP ({local_ip}) from scan targets.")

    return scan_result


def _run_reconnaissance_phase(scan_result, logger, display, state_manager, ssid, stats, html_logger):
    """Run reconnaissance phase on discovered IPs."""
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
    
    return parsed_devices


def _run_vulnerability_scan_phase(scan_result, logger, display, state_manager, ssid, stats, html_logger):
    """Run vulnerability scanning phase."""
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
    
    return vulnerabilities


def _run_exploit_testing_phase(vulnerabilities, logger, display, state_manager, ssid, stats, html_logger):
    """Run exploit testing phase."""
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


def _run_file_stealing_phase(vulnerabilities, ssh_credentials, logger, wifi_manager, 
                           display, state_manager, ssid, stats, connected_ssid):
    """Run file stealing phase."""
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
                os_type="Unknown"  # Could be enhanced to pass actual OS type
            ):
                successful = True
                stats["files"] += 3  # Increment files per successful steal
                break

        if successful:
            logger.log(f"[SUCCESS] File stealing successful for IP: {ip}")
            wifi_manager.disconnect_wifi()
            connected_ssid = None  # Reset connected SSID after disconnecting
            change_mac_address(logger)