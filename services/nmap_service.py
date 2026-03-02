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

    def _get_local_subnet(self):
        """
        Derive the /24 subnet from the Pi's IP on the active interface.
        e.g.  IP 10.0.0.78  →  '10.0.0.0/24'
              IP 192.168.4.5 →  '192.168.4.0/24'
        Falls back to '192.168.1.0/24' if detection fails.
        """
        iface = self.manager.interface
        try:
            out = subprocess.run(
                ["ip", "addr", "show", iface],
                stdout=subprocess.PIPE, text=True, check=False
            ).stdout
            local_ip = next(
                (line.split()[1].split("/")[0]
                 for line in out.splitlines() if line.strip().startswith("inet ")),
                None
            )
            if local_ip:
                parts = local_ip.split(".")
                subnet = f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
                self.logger.log(f"[INFO] Detected subnet {subnet} from {iface} ({local_ip})")
                return subnet, local_ip
        except Exception as e:
            self.logger.log(f"[WARNING] Could not detect subnet from {iface}: {e}")
        self.logger.log("[WARNING] Falling back to default subnet 192.168.1.0/24")
        return "192.168.1.0/24", None

    def discover(self):
        """
        Runs an Nmap discovery on the subnet derived from the active interface,
        then filters out the Pi's own IP.
        Returns: { "discovered_ips": [...], "raw_output": "..." }
        """
        self.logger.log(f"[DEBUG] WiFiManager using interface: {self.manager.interface}")

        target, local_ip = self._get_local_subnet()
        self.logger.log(f"[INFO] Running Nmap discovery on {target}")

        result = run_nmap_scan(target, logger=self.logger)

        if local_ip:
            original = result.get("discovered_ips", [])
            filtered = [ip for ip in original if ip != local_ip]
            result["discovered_ips"] = filtered
            self.logger.log(
                f"[INFO] Excluding our own {self.manager.interface} IP "
                f"({local_ip}) from targets."
            )

        self.logger.log(f"[INFO] Nmap found {len(result.get('discovered_ips', []))} hosts.")
        return result
