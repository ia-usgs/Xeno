import subprocess
from utils.html_logger import HTMLLogger
from utils.logger import Logger


class Recon:
    def __init__(self, logger=None):
        self.logger = logger if logger else Logger()

    def ping_target(self, target):
        """Ping the target to ensure it is reachable."""
        try:
            self.logger.log(f"[INFO] Pinging target: {target}")
            result = subprocess.run(
                ["ping", "-c", "4", target],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode == 0:
                self.logger.log(f"[SUCCESS] Target {target} is reachable.\n{result.stdout}")
                return True
            else:
                self.logger.log(f"[WARNING] Ping to {target} failed.\n{result.stderr}")
                return False
        except subprocess.CalledProcessError as e:
            self.logger.log(f"[ERROR] Ping failed: {e}")
            return False

    def scan_ports(self, target, timeout=60):
        """Perform a detailed port scan using nmap."""
        try:
            self.logger.log(f"[INFO] Scanning ports on target: {target} with a timeout of {timeout} seconds")
            result = subprocess.run(
                ["nmap", "-sS", "-Pn", "-p-", target],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,  # Add timeout here
            )
            self.logger.log(f"[INFO] Port scan result for {target}:\n{result.stdout}")
            return result.stdout
        except subprocess.TimeoutExpired:
            self.logger.log(f"[WARNING] Port scan for {target} timed out after {timeout} seconds.")
            return None
        except subprocess.CalledProcessError as e:
            self.logger.log(f"[ERROR] Port scan failed: {e}")
            return None

    def enumerate_services(self, target, timeout=60):
        """Enumerate services and versions on open ports."""
        try:
            self.logger.log(f"[INFO] Enumerating services on target: {target} with a timeout of {timeout} seconds")
            result = subprocess.run(
                ["nmap", "-sV", "-Pn", target],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,  # Add timeout here
            )
            self.logger.log(f"[INFO] Service enumeration result for {target}:\n{result.stdout}")
            return result.stdout
        except subprocess.TimeoutExpired:
            self.logger.log(f"[WARNING] Service enumeration for {target} timed out after {timeout} seconds.")
            return None
        except subprocess.CalledProcessError as e:
            self.logger.log(f"[ERROR] Service enumeration failed: {e}")
            return None

    def detect_os(self, target, timeout=60):
        """Perform OS detection using nmap."""
        try:
            self.logger.log(f"[INFO] Detecting OS on target: {target} with a timeout of {timeout} seconds")
            result = subprocess.run(
                ["nmap", "-O", "-Pn", target],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,  # Add timeout here
            )
            self.logger.log(f"[INFO] OS detection result for {target}:\n{result.stdout}")
            return result.stdout
        except subprocess.TimeoutExpired:
            self.logger.log(f"[WARNING] OS detection for {target} timed out after {timeout} seconds.")
            return None
        except subprocess.CalledProcessError as e:
            self.logger.log(f"[ERROR] OS detection failed: {e}")
            return None

    def run_full_recon(self, target, ssid=None, html_logger=None):
        """Run all reconnaissance tasks on the target."""
        self.logger.log(f"[INFO] Starting full reconnaissance on target: {target}")

        # Ping target
        if not self.ping_target(target):
            self.logger.log(f"[WARNING] Skipping further recon on {target} as it is unreachable.")
            return

        # Run port scan
        port_scan_results = self.scan_ports(target)

        # Enumerate services
        service_results = self.enumerate_services(target)

        # Detect OS
        os_results = self.detect_os(target)

        recon_results = {
            "target": target,
            "port_scan": port_scan_results,
            "service_enum": service_results,
            "os_detection": os_results,
        }

        self.logger.log(f"[INFO] Reconnaissance completed for target: {target}")

        # Append results to HTML file
        if html_logger and ssid:
            html_logger.append_recon_results_to_html(ssid, recon_results)

        return recon_results
