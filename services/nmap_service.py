from scans.nmap_scanner import run_nmap_scan
from utils.logger import Logger
import subprocess

class NmapService:
    def __init__(self, wifi_mgr, logger=None):
        """
        wifi_mgr: an instance of wifi.wifi_manager.WiFiManager (already initialized
                  and having detected the active interface).
        logger:  an optional Logger instance.
        """
        self.manager = wifi_mgr
        self.logger  = logger or Logger(log_file="logs/scan.log")

    def discover(self, target="192.168.1.0/24"):
        """
        Runs an Nmap discovery on the given target subnet, then
        filters out the Pi's own IP on the active interface.
        Returns: { "discovered_ips": [...], "raw_output": "..." }
        """
        # log which interface we're using
        self.logger.log(f"[DEBUG] WiFiManager using interface: {self.manager.interface}")
        self.logger.log(f"[INFO] Running Nmap discovery on {target}")

        # perform the scan
        result = run_nmap_scan(target, logger=self.logger)

        # determine and exclude our own IP
        iface = self.manager.interface
        out = subprocess.run(
            ["ip", "addr", "show", iface],
            stdout=subprocess.PIPE,
            text=True,
            check=False
        ).stdout

        local_ip = next(
            (line.split()[1].split("/")[0]
             for line in out.splitlines() if line.strip().startswith("inet ")),
            None
        )

        if local_ip:
            original = result.get("discovered_ips", [])
            filtered = [ip for ip in original if ip != local_ip]
            result["discovered_ips"] = filtered
            self.logger.log(f"[INFO] Excluding our own {iface} IP ({local_ip}) from targets.")

        self.logger.log(f"[INFO] Nmap found {len(result.get('discovered_ips', []))} hosts.")
        return result
