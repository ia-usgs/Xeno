import subprocess
import re
from utils.logger import Logger


def run_nmap_scan(target, logger=None):
    """
    Run an nmap scan on the specified target and extract discovered IPs.
    """
    if logger is None:
        logger = Logger()

    try:
        logger.log(f"Starting nmap scan on target: {target}")
        result = subprocess.run(
            ["nmap", "-sn", target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        logger.log(f"nmap scan result:\n{result.stdout}")

        # Extract discovered IPs using regex
        discovered_ips = re.findall(r"Nmap scan report for ([\d\.]+)", result.stdout)

        return {
            "discovered_ips": discovered_ips,
            "raw_output": result.stdout,
        }

    except subprocess.CalledProcessError as e:
        logger.log(f"nmap scan failed: {e}")
        return {
            "discovered_ips": [],
            "raw_output": "",
        }
