import os
import time
import logging
# Suppress debug logs from Pillow (PIL)
logging.getLogger("PIL").setLevel(logging.WARNING)
from wifi.wifi_manager import WiFiManager
from utils.logger import Logger
from utils.html_logger import HTMLLogger
from utils.display import EPaperDisplay
from utils.image_state_manager import ImageStateManager
from workflows.scan_workflow import run_scans

def main():
    """
    The main entry point for the Xeno project.

    Initializes the following components:
        - Logger: Handles logging for the application.
        - WiFiManager: Manages Wi-Fi connections.
        - HTMLLogger: Logs scan results in HTML format.
        - EPaperDisplay: Manages the e-paper display updates.
        - ImageStateManager: Tracks and manages workflow states and images.

    Workflow:
        1. Initializes display and loads required credentials.
        2. Continuously performs scans and updates results.
        3. Logs workflow progress and handles any exceptions.

    Raises:
        Exception: If a critical error occurs during initialization or execution.
    """
    os.makedirs("logs", exist_ok=True)
    logger = Logger(log_file="logs/scan.log")
    wifi_manager = WiFiManager(logger=logger)
    html_logger = HTMLLogger(output_dir="utils/html_logs", json_dir="utils/json_logs")
    display = EPaperDisplay()
    state_manager = ImageStateManager()

    try:
        display.initialize()
        while True:
            logger.log("[INFO] Starting new scanning cycle.")
            run_scans(logger, wifi_manager, html_logger, display, state_manager)
            logger.log("[INFO] Scanning cycle completed. Sleeping for 10 minutes.")
            time.sleep(600)  # Sleep for 10 minutes
    except Exception as e:
        logger.log(f"[ERROR] Fatal error occurred: {e}")
    finally:
        display.clear()  # Display is cleared
        print("[INFO] E-paper display cleared.")

if __name__ == "__main__":
    main()
