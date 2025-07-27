# services/log_service.py

from utils.html_logger import HTMLLogger

class LogService:
    def __init__(self,
                 output_dir="utils/html_logs",
                 json_dir="utils/json_logs"):
        self.html_logger = HTMLLogger(output_dir=output_dir,
                                      json_dir=json_dir)

    def save_scan(self, ssid, scan_result):
        """
        Appends a raw Nmap scan result to JSON and regenerates the HTML.
        """
        self.html_logger.save_scan_result_to_json(ssid, scan_result)
        self.html_logger.generate_html_from_json(ssid)

    def append_recon(self, ssid, recon_results):
        """
        Appends recon results (as a separate entry) and regenerates the HTML.
        """
        # Re-use `save_scan_result_to_json` with a custom key
        self.html_logger.save_scan_result_to_json(
            ssid,
            {"recon_results": recon_results}
        )
        self.html_logger.generate_html_from_json(ssid)

    def append_vulns(self, ssid, vulnerability_results):
        """
        Appends vulnerability results and regenerates the HTML.
        """
        self.html_logger.save_scan_result_to_json(
            ssid,
            {"vulnerability_results": vulnerability_results}
        )
        self.html_logger.generate_html_from_json(ssid)

    def append_exploits(self, ssid, exploit_results):
        """
        Appends exploit test outcomes and regenerates the HTML.
        """
        self.html_logger.save_scan_result_to_json(
            ssid,
            {"exploit_results": exploit_results}
        )
        self.html_logger.generate_html_from_json(ssid)
