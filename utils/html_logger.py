import os
import json
from datetime import datetime


class HTMLLogger:
    def __init__(self, output_dir="utils/html_logs", json_dir="utils/json_logs"):
        """
        Initialize the HTMLLogger class.

        Parameters:
            output_dir (str, optional): The directory where HTML logs will be saved.
                                        Defaults to "utils/html_logs".
            json_dir (str, optional): The directory where JSON logs will be saved.
                                      Defaults to "utils/json_logs".

        Workflow:
            - Creates the specified directories for HTML and JSON logs if they do not already exist.
        """

        self.output_dir = output_dir
        self.json_dir = json_dir
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)

    def save_scan_result_to_json(self, ssid, scan_result):
        """
        Save scan results to a JSON file.

        Parameters:
            ssid (str): The SSID of the Wi-Fi network associated with the scan results.
            scan_result (str): The raw output or processed result of the scan.

        Workflow:
            - Loads existing data from the corresponding JSON file, if it exists.
            - Appends the new scan result with a timestamp to the JSON data.
            - Saves the updated JSON data back to the file.

        Returns:
            str: The path to the JSON file where the scan results were saved.
        """

        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Load existing data if the file exists
        if os.path.exists(json_file):
            with open(json_file, "r") as file:
                data = json.load(file)
        else:
            data = {"ssid": ssid, "scans": []}

        # Append the new scan result
        data["scans"].append({"timestamp": timestamp, "result": scan_result})

        # Save the updated data back to the JSON file
        with open(json_file, "w") as file:
            json.dump(data, file, indent=4)

        print(f"[INFO] Scan result saved to JSON: {json_file}")
        return json_file

    def generate_html_from_json(self, ssid):
        """
        Generate or update an HTML log based on a JSON file.

        Parameters:
            ssid (str): The SSID of the Wi-Fi network associated with the scan results.

        Workflow:
            - Reads scan results from the corresponding JSON file.
            - Generates an HTML file with the scan results formatted as entries.
            - Saves or updates the HTML file in the specified output directory.

        Raises:
            Warning: If the JSON file for the specified SSID does not exist.
        """

        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        html_file = os.path.join(self.output_dir, f"{ssid}.html")

        if not os.path.exists(json_file):
            print(f"[WARNING] No JSON file found for SSID: {ssid}. Cannot generate HTML log.")
            return

        # Load scan data from JSON
        with open(json_file, "r") as file:
            data = json.load(file)

        # Generate HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Wi-Fi Scan Log for SSID: {ssid}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .scan-entry {{ margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9; }}
                .scan-entry h2 {{ margin: 0; font-size: 1.2em; color: #333; }}
                .scan-entry pre {{ background-color: #eee; padding: 10px; border-radius: 3px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <h1>Wi-Fi Scan Log for SSID: {ssid}</h1>
        """

        for scan in data["scans"]:
            html_content += f"""
            <div class="scan-entry">
                <h2>Scan conducted at: {scan['timestamp']}</h2>
                <pre>{scan.get('result', 'None')}</pre>
            </div>
            """
            if "vulnerability_results" in scan:
                html_content += """
                <div class="scan-entry">
                    <h2>Vulnerability Scan conducted at: {}</h2>
                    <pre>{}</pre>
                </div>
                """.format(
                    scan["timestamp"],
                    json.dumps(scan["vulnerability_results"], indent=4)
                )

        html_content += """
        </body>
        </html>
        """

        # Save the HTML content to the file
        with open(html_file, "w") as file:
            file.write(html_content)

        print(f"[INFO] HTML log updated: {html_file}")

    def append_recon_results_to_html(self, ssid, recon_results):
        """
        Append reconnaissance results to the existing HTML log.

        Parameters:
            ssid (str): The SSID of the Wi-Fi network associated with the reconnaissance results.
            recon_results (dict): A dictionary containing the reconnaissance data to append.

        Workflow:
            - Loads or creates a JSON log for the specified SSID.
            - Appends the reconnaissance results with a timestamp to the JSON data.
            - Updates the corresponding HTML log to include the new data.
        """

        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Load or create JSON log
        if os.path.exists(json_file):
            with open(json_file, "r") as file:
                data = json.load(file)
        else:
            data = {"ssid": ssid, "scans": []}

        # Add recon results
        data["scans"].append({
            "timestamp": timestamp,
            "recon_results": recon_results
        })

        # Save updated JSON
        with open(json_file, "w") as file:
            json.dump(data, file, indent=4)

        # Generate updated HTML
        self.generate_html_from_json(ssid)

    def append_vulnerability_results_to_html(self, ssid, vulnerability_results):
        """
        Append vulnerability scan results to the existing HTML log.

        Parameters:
            ssid (str): The SSID of the Wi-Fi network associated with the vulnerability results.
            vulnerability_results (dict): A dictionary containing the vulnerability data to append.

        Workflow:
            - Loads or creates a JSON log for the specified SSID.
            - Appends the vulnerability results with a timestamp to the JSON data.
            - Updates the corresponding HTML log to include the new data.
        """

        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Load or create JSON log
        if os.path.exists(json_file):
            with open(json_file, "r") as file:
                data = json.load(file)
        else:
            data = {"ssid": ssid, "scans": []}

        # Add vulnerability scan results
        data["scans"].append({
            "timestamp": timestamp,
            "vulnerability_results": vulnerability_results
        })

        # Save updated JSON
        with open(json_file, "w") as file:
            json.dump(data, file, indent=4)

        # Generate updated HTML
        self.generate_html_from_json(ssid)
