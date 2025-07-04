import subprocess
import re
from utils.logger import Logger


def run_nmap_scan(target, logger=None):
    """
        Run a basic `nmap` scan to discover devices on a target network.

        Parameters:
            target (str): The target network or IP range to scan (e.g., "192.168.1.0/24").
            logger (Logger, optional): An instance of the Logger class for logging activities.
                                       If none is provided, a new Logger instance is created.

        Returns:
            dict: A dictionary containing:
                  - discovered_ips (list): A list of IP addresses discovered during the scan.
                  - raw_output (str): The raw output from the `nmap` command.

        Raises:
            subprocess.CalledProcessError: If the `nmap` command fails or encounters an error.
        """

    if logger is None:
        logger = Logger()

    try:
        logger.log(f"Starting nmap scan on target: {target}")
        result = subprocess.run(
            ["sudo", "nmap", "-sn", "-PR", target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
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
