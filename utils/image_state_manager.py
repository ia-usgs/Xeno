import os
import logging
from PIL import Image, ImageEnhance

# Logging setup
logging.basicConfig(level=logging.DEBUG)

class ImageStateManager:
    """Manages dynamic image updates based on workflow states."""

    # Map workflow states to corresponding images in the /images folder
    IMAGE_MAP = {
        "scanning": "/home/pi/xeno/images/xeno_walking_right.png",
        "analyzing": "/home/pi/xeno/images/xeno_detective_right.png",
        "ready_to_attack": "/home/pi/xeno/images/xeno_preparing_to_attack.png",
        "attacking": "/home/pi/xeno/images/xeno_attacking_right.png",
        "success": "/home/pi/xeno/images/happy_xeno.png",
        "fallback": "/home/pi/xeno/images/xeno_walking_left.png",
        "validating": "/home/pi/xeno/images/xeno_attacking_left.png",
        "reconnaissance": "/home/pi/xeno/images/xeno_hoodie_right.png",
        "investigating": "/home/pi/xeno/images/xeno_hoodie_left.png",
        "reviewing": "/home/pi/xeno/images/xeno_detective_left.png",
        "windows_fingerprint": "/home/pi/xeno/images/xeno_windows_fingerprint.png",
        "linux_fingerprint": "/home/pi/xeno/images/xeno_linux_fingerprint.png",
        "file_stolen": "/home/pi/xeno/images/xeno_stolen_file.png",
    }

    # Map workflow states to corresponding messages
    MESSAGE_MAP = {
        "scanning": "Sniffing the network..!",
        "analyzing": "So many targets!",
        "ready_to_attack": "Xeno is sharpening its claws...",
        "attacking": "Xeno is on the hunt! Beware!",
        "success": "Mission accomplished!",
        "fallback": "Oops!",
        "validating": "Double-checking...",
        "reconnaissance": "Exploring the surroundings...",
        "investigating": "Looking deeper...",
        "windows_fingerprint": "Windows, Gotcha!",
        "linux_fingerprint": "Linux, Yummy!",
        "file_stolen": "Xeno ate a file!",
        "reviewing": "Pondering...",
    }

    def __init__(self):
        """Initialize the ImageStateManager with a default state."""
        self.current_state = "scanning"

    def load_image(self, state):
        """
        Load and process the image corresponding to the given workflow state.

        Parameters:
            state (str): The workflow state for which to load the image.

        Returns:
            PIL.Image: The processed image with enhanced contrast, ready for display.

        Raises:
            FileNotFoundError: If the image for the specified state is not found.
            Exception: If an error occurs while loading or processing the image.
        """

        try:
            image_path = self.IMAGE_MAP.get(state)
            if not image_path or not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found for state: {state} at {image_path}")

            logging.info(f"Loading image for state: {state}")
            original_image = Image.open(image_path)

            # Enhance contrast for better display
            enhancer = ImageEnhance.Contrast(original_image)
            enhanced_image = enhancer.enhance(2)

            return enhanced_image
        except Exception as e:
            logging.error(f"Error loading image for state '{state}': {e}")
            raise

    def set_state(self, state):
        """
        Set the current workflow state.

        Parameters:
            state (str): The new workflow state to set.

        Raises:
            ValueError: If the specified state is invalid or not defined in IMAGE_MAP.
        """

        if state not in self.IMAGE_MAP:
            raise ValueError(f"Invalid state: {state}. Available states: {list(self.IMAGE_MAP.keys())}")
        self.current_state = state
        logging.info(f"Workflow state updated to: {state}")

    def get_image_and_message_for_current_state(self):
        """
        Retrieve the processed image and message corresponding to the current workflow state.

        Returns:
            tuple:
                - PIL.Image: The processed image for the current state.
                - str: The message associated with the current state.

        Raises:
            Exception: If an error occurs while loading the image.
        """

        image = self.load_image(self.current_state)
        message = self.MESSAGE_MAP.get(self.current_state, "Xeno is doing its thing!")
        return image, message
