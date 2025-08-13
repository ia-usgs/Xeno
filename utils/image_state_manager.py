import os
import json
import logging
from PIL import Image, ImageEnhance

# Logging setup
logging.basicConfig(level=logging.DEBUG)

class ImageStateManager:
    """
    Manages dynamic image updates based on workflow states as well as
    persisting counters for various workflow statistics.  In addition to
    tracking which Xeno image to display for each workflow state, this
    class now maintains a persistent handshake counter.  Keeping the
    handshake count here centralises state management in one place and
    allows other components (e.g., the e‑ink display and logging
    services) to query or update the counter without duplicating file
    operations.  The handshake counter is stored in a small JSON file
    (`HANDSHAKE_FILE`) so that the number of captured handshakes
    survives across program restarts and even full system reboots.
    """

    # Map workflow states to corresponding images in the /images folder
    IMAGE_MAP = {
        "scanning": "/home/pi/xeno/images/xeno_walking_right.png",
        "analyzing": "/home/pi/xeno/images/xeno_detective_right.png",
        "ready_to_attack": "/home/pi/xeno/images/xeno_preparing_to_attack.png",
        "attacking": "/home/pi/xeno/images/happy_xeno_ichigo.png",
        "success": "/home/pi/xeno/images/happy_xeno.png",
        "fallback": "/home/pi/xeno/images/xeno_walking_left.png",
        "validating": "/home/pi/xeno/images/xeno_attacking_left.png",
        "reconnaissance": "/home/pi/xeno/images/xeno_pikachu_hoodie_right.png",
        "investigating": "/home/pi/xeno/images/xeno_hoodie_left.png",
        "reviewing": "/home/pi/xeno/images/xeno_detective_left.png",
        "windows_fingerprint": "/home/pi/xeno/images/xeno_windows_fingerprint.png",
        "linux_fingerprint": "/home/pi/xeno/images/xeno_linux_fingerprint.png",
        "file_stolen": "/home/pi/xeno/images/xeno_stolen_file.png",
        "handshake_capture": "/home/pi/xeno/images/xeno_handshake.png",
    }

    # Map workflow states to corresponding messages
    MESSAGE_MAP = {
        "scanning": "Sniffing the network..!",
        "analyzing": "So many targets!",
        "ready_to_attack": "Xeno is sharpening its claws...",
        "attacking": "Xeno is on the hunt!",
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
        """
        Initialize the ImageStateManager with a default state.  In
        addition to setting up the current workflow state, this will
        initialize and load the persistent handshake count.  If the
        handshake count file does not exist the counter will default
        to zero.
        """
        self.current_state = "scanning"
        # Initialise handshake counter before any images are loaded
        self.handshakes = 0
        self._load_handshake_state()

    # File used to persist the handshake counter.  We keep it at the
    # repository root so that it can easily be inspected by the user.
    HANDSHAKE_FILE = "handshake_state.json"

    def _load_handshake_state(self):
        """
        Load the stored handshake count from disk.  If the file is
        missing or cannot be parsed, the counter will be initialised to
        zero.  Any I/O errors are logged but not raised so that
        execution can proceed normally; a broken or missing file will
        simply reset the counter.
        """
        try:
            if os.path.exists(self.HANDSHAKE_FILE):
                with open(self.HANDSHAKE_FILE, "r") as fh:
                    data = json.load(fh)
                self.handshakes = data.get("handshakes", 0)
            else:
                self.handshakes = 0
        except Exception as exc:
            # If something goes wrong (corrupt JSON, permission error), log
            # the error and reset the counter.  This prevents the
            # application from crashing on startup due to a bad state
            # file.
            logging.error(f"Failed to load handshake state: {exc}")
            self.handshakes = 0

    def _save_handshake_state(self):
        """
        Persist the current handshake count to disk.  This method is
        called automatically whenever the count is incremented.  If
        saving fails, an error will be logged but not raised.
        """
        try:
            data = {"handshakes": self.handshakes}
            with open(self.HANDSHAKE_FILE, "w") as fh:
                json.dump(data, fh)
            logging.debug(f"Handshake count saved: {self.handshakes}")
        except Exception as exc:
            logging.error(f"Failed to save handshake state: {exc}")

    def increment_handshakes(self, count: int = 1):
        """
        Increment the handshake counter by the specified count and
        immediately persist the new value to disk.  This should be
        called whenever a handshake capture is detected.  A count of
        zero or negative will have no effect.

        Parameters:
            count (int): The number of additional handshakes to record.
        """
        try:
            if count > 0:
                self.handshakes += count
                self._save_handshake_state()
        except Exception as exc:
            logging.error(f"Error incrementing handshake count: {exc}")

    def get_handshakes(self) -> int:
        """
        Return the number of handshakes captured so far.  This value is
        loaded from disk during initialization and updated via
        `increment_handshakes()`.
        """
        return self.handshakes

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
