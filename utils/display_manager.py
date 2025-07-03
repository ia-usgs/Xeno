"""
Display manager module for Xeno project.

This module provides functions to manage the e-paper display,
including initialization and state updates during workflow execution.
"""

import logging
from PIL import Image


def initialize_display_template(display, current_ssid="Not Connected", stats=None):
    """
    Initialize the e-paper display with a basic template.

    Parameters:
        display (EPaperDisplay): The e-paper display object to update.
        current_ssid (str): The name of the current Wi-Fi network (default: "Not Connected").
        stats (dict): A dictionary with stats on targets, vulnerabilities, exploits, and files.

    Default Stats:
        - targets: 0
        - vulns: 0
        - exploits: 0
        - files: 0

    Raises:
        Exception: If an error occurs during initialization or image rendering.
    """
    if stats is None:
        stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}  # Default stats
    
    try:
        placeholder_image = Image.new('1', (60, 60), color=255)  # Blank image
        prepared_image = display.prepare_image(placeholder_image)
        layout = display.draw_layout(prepared_image, current_ssid=current_ssid, current_status="Initializing...", stats=stats)
        display.display_image(layout, use_partial_update=False)  # Full refresh for initialization
        print("[INFO] Template initialized.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize display template: {e}")


def update_display_state(display, state_manager, state, current_ssid="SSID",
                         current_status="", stats=None, use_partial_update=True):
    """
    Update the e-paper display with the current workflow state.

    Parameters:
        display (EPaperDisplay): The e-paper display object to update.
        state_manager (ImageStateManager): Manages workflow states and images.
        state (str): The current workflow state (e.g., "scanning", "analyzing").
        current_ssid (str): The name of the current Wi-Fi network.
        current_status (str): The current status message to display.
        stats (dict): A dictionary with stats on targets, vulnerabilities, exploits, and files.
        use_partial_update (bool): Whether to perform a partial refresh (default: True).

    Raises:
        Exception: If the display update fails.
    """
    if stats is None:
        stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}

    try:
        # Log the current state and refresh mode
        logging.info(f"Updating display: state={state}, partial_refresh={use_partial_update}")

        # Update workflow state and load corresponding image and message
        state_manager.set_state(state)
        image, xeno_message = state_manager.get_image_and_message_for_current_state()
        prepared_image = display.prepare_image(image)

        # Initialize the display in the correct mode
        if use_partial_update:
            # Partial refresh does not require reinitialization
            logging.debug("Partial refresh mode: Skipping reinitialization.")
        else:
            # Full refresh requires initialization to default mode
            display.initialize(partial_refresh=False)

        # Combine the current status with the Xenomorph message
        full_status = f"{current_status}\n{xeno_message}"

        # Render layout and update display
        layout = display.draw_layout(prepared_image, current_ssid=current_ssid,
                                      current_status=full_status, stats=stats)
        display.display_image(layout, use_partial_update=use_partial_update)

        # Log success
        logging.info(f"State updated successfully: {state}, partial_refresh={use_partial_update}")
    except Exception as e:
        logging.error(f"Failed to update display: {e}")