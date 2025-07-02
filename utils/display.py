import sys
import os
import json
from datetime import datetime
# Add paths for drivers and assets
sys.path.append('/home/pi/xeno/utils/waveshare_epd')
sys.path.append('/home/pi/xeno/utils')
import logging
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from waveshare_epd import epd2in13_V4

# Logging setup
logging.basicConfig(level=logging.DEBUG)

# File to save state
STATE_FILE = "state.json"

class EPaperDisplay:

    def __init__(self):
        """
        Initialize the EPaperDisplay class.

        Attributes:
            epd (EPD): An instance of the Waveshare e-paper display driver.
            width (int): The width of the e-paper display in pixels.
            height (int): The height of the e-paper display in pixels.
            age (int): The age of the display usage in days.
            level (int): The current level for the display (calculated dynamically).
            start_date (str or None): The start date of the display's usage, formatted as "YYYY-MM-DD".

        Workflow:
            - Loads the saved state if available, otherwise initializes with default values.
        """

        self.epd = epd2in13_V4.EPD()
        self.width = 122  # Display width
        self.height = 250  # Display height
        self.age = 0  # Age in days
        self.level = 1
        self.start_date = None
        self.pet_name = "Xeno"  # Default name if not set in state
        self.load_state()  # Load saved state
        logging.info("EPaperDisplay initialized.")

    def load_state(self):
        """
        Load the saved display state from a JSON file.

        Reads the state from `state.json`, which includes:
            - level: The current level for the display.
            - start_date: The start date of the display's usage.

        Calculates the `age` of the display based on the `start_date`.

        Raises:
            Exception: If the state file cannot be read or is improperly formatted.
        """

        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                    self.level = state.get("level", 1)
                    self.start_date = state.get("start_date", None)
                    self.pet_name = state.get("pet_name", "Xeno")

                    # Calculate age based on start_date
                    if self.start_date:
                        start_date_obj = datetime.strptime(self.start_date, "%Y-%m-%d")
                        self.age = (datetime.now() - start_date_obj).days
                    else:
                        self.age = 0

                    logging.info(f"State loaded: {state}")
            except Exception as e:
                logging.error(f"Error loading state file: {e}")
        else:
            # First run, initialize start date
            self.start_date = datetime.now().strftime("%Y-%m-%d")
            logging.info("No saved state found. Initializing with current date.")

    def save_state(self):
        """
        Save the current display state to a JSON file.

        Writes the following attributes to `state.json`:
            - level: The current level for the display.
            - start_date: The start date of the display's usage.

        Raises:
            Exception: If the state file cannot be written or an error occurs during saving.
        """

        try:
            state = {
                "level": self.level,
                "start_date": self.start_date,
                "pet_name": self.pet_name
            }
            with open(STATE_FILE, "w") as f:
                json.dump(state, f)
                logging.info(f"State saved: {state}")
        except Exception as e:
            logging.error(f"Error saving state file: {e}")

    def initialize(self, partial_refresh=False):
        """
        Initialize the e-paper display.

        Parameters:
            partial_refresh (bool): Whether to initialize the display for partial refresh mode.
                                    Defaults to False (full refresh mode).

        Workflow:
            - Initializes the display in the specified refresh mode.
            - Clears the display screen.

        Raises:
            Exception: If the initialization process fails.
        """

        try:
            if partial_refresh:
                logging.info("Initializing for partial refresh.")
                self.epd.init_fast()  # Use partial refresh mode
            else:
                logging.info("Initializing for full refresh.")
                self.epd.init()  # Use full refresh mode
            self.epd.Clear(0xFF)  # Clear the screen
        except Exception as e:
            logging.error(f"Failed to initialize display: {e}")
            raise

    def prepare_image(self, image):
        """
        Resize and process an image to fit the e-paper display.

        Parameters:
            image (PIL.Image): The input image to be resized and processed.

        Returns:
            PIL.Image: The processed image, resized to fit the display dimensions and converted
                       to a 1-bit black-and-white format with dithering.

        Raises:
            Exception: If an error occurs during image processing.
        """

        try:
            # Resize the image
            resized_image = image.resize((90, 90), resample=Image.LANCZOS)
            # Convert to 1-bit black and white with dithering
            processed_image = resized_image.convert('1', dither=Image.FLOYDSTEINBERG)
            logging.info("Image prepared for display.")
            return processed_image
        except Exception as e:
            logging.error(f"Error preparing image: {e}")
            raise

    def calculate_level(self, stats):
        """
        Calculate the level dynamically based on cumulative stats.

        Parameters:
            stats (dict): A dictionary containing performance metrics, including:
                - targets (int): The number of targets discovered.
                - vulns (int): The number of vulnerabilities identified.
                - exploits (int): The number of exploits executed.
                - files (int): The number of files successfully stolen.

        Workflow:
            - Computes the total score based on stats and updates the level.
            - The level threshold increases with each level.

        Raises:
            KeyError: If any required key is missing from the `stats` dictionary.
        """

        try:
            # Calculate total score for the cycle
            cycle_score = (
                stats["targets"] * 10 +
                stats["vulns"] * 20 +
                stats["exploits"] * 30 +
                stats["files"] * 5
            )

            # Determine the threshold for leveling up
            level_threshold = self.level * 100  # Threshold increases with level
            while cycle_score >= level_threshold:
                self.level += 1
                cycle_score -= level_threshold
                level_threshold = self.level * 125  # Update threshold for next level
        except KeyError as e:
            logging.error(f"Missing key in stats: {e}")
            raise

    def draw_layout(self, image, current_ssid="Not Connected", current_status="Initializing...", stats=None):
            """
            Draw a custom layout for the e-paper display.

            Parameters:
                image (PIL.Image): The Xeno image to display.
                current_ssid (str): The name of the current Wi-Fi network. Defaults to "Not Connected".
                current_status (str): The current status message to display. Defaults to "Initializing...".
                stats (dict, optional): A dictionary containing performance metrics, including:
                    - targets (int): Number of targets discovered (default: 0).
                    - vulns (int): Number of vulnerabilities identified (default: 0).
                    - exploits (int): Number of exploits executed (default: 0).
                    - files (int): Number of files successfully stolen (default: 0).

            Returns:
                PIL.Image: The final layout image with all elements rendered.

            Raises:
                Exception: If any error occurs during the rendering of the layout.
            """

            if stats is None:
                stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}

            try:
                # Update level
                self.calculate_level(stats)

                # Create a blank canvas for the display
                canvas = Image.new('1', (self.width, self.height), 255)  # 255 = White background
                draw = ImageDraw.Draw(canvas)

                # Add a border
                border_offset = 1
                draw.rectangle(
                    (border_offset, border_offset, self.width - border_offset, self.height - border_offset),
                    outline=0,  # Black border
                    width=1
                )

                # Top bar with SSID
                draw.rectangle((0, 0, self.width, 20), fill=0)  # Black background
                font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 8)
                draw.text(xy=(5, 2), text=f"SSID: {current_ssid}", font=font_small, fill=255)  # White text for SSID

                # Section separators
                draw.line((0, 20, self.width, 20), fill=0, width=1)
                draw.line((0, 45, self.width, 45), fill=0, width=1)
                draw.line((0, 95, self.width, 95), fill=0, width=1)

                # Stats Section
                font_stats = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 8)
                draw.text(xy=(5, 25), text=f"Targets: {stats['targets']}", font=font_stats, fill=0)
                draw.text(xy=(75, 25), text=f"Vulns: {stats['vulns']}", font=font_stats, fill=0)
                draw.text(xy=(5, 35), text=f"Exploits: {stats['exploits']}", font=font_stats, fill=0)
                draw.text(xy=(75, 35), text=f"Files: {stats['files']}", font=font_stats, fill=0)

                # Current status INSIDE the blank box
                font_body = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 8)
                draw.text(xy=(40, 50), text="Status:", font=font_body, fill=0)
                draw.text(xy=(5, 65), text=current_status, font=font_body, fill=0)

                # Pet Name Section
                font_body = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 8)
                draw.text(xy=(35, 100), text=f"{self.pet_name}", font=font_body, fill=0)
                
                # Age and Level
                draw.text(xy=(5, 110), text=f"Age: {self.age} days", font=font_body, fill=0)
                draw.text(xy=(75, 110), text=f"Level: {self.level}", font=font_body, fill=0)

                # Bottom Section: Xeno Image
                canvas.paste(image, (17, 150))  # Paste the dynamic Xeno image
                logging.info("Dynamic layout drawn successfully.")

                # Save the updated state
                self.save_state()
                return canvas
            except Exception as e:
                logging.error(f"Error drawing layout: {e}")
                raise

    def display_image(self, canvas, use_partial_update=True):
        """
        Display the given image on the e-paper display.

        Parameters:
            canvas (PIL.Image): The prepared layout image to display.
            use_partial_update (bool): Whether to use partial refresh mode. Defaults to True.

        Raises:
            Exception: If an error occurs during the display update process.
        """

        try:
            buffer = self.epd.getbuffer(canvas)
            if use_partial_update:
                logging.debug("Using partial refresh...")
                self.epd.displayPartial(buffer)  # Call the working partial refresh method
            else:
                logging.debug("Using full refresh...")
                self.epd.display(buffer)  # Call the full refresh method
            
            # Save the current display image for web interface
            try:
                canvas.save("latest_display.png")
                logging.debug("Display image saved as latest_display.png for web interface.")
            except Exception as save_error:
                logging.warning(f"Failed to save display image for web interface: {save_error}")
                
        except Exception as e:
            logging.error(f"Failed to display image: {e}")
            raise

    def clear(self):
        """
        Clear the e-paper display and put it into sleep mode.

        Workflow:
            - Clears the display screen to a blank state.
            - Puts the display hardware into low-power sleep mode.

        Raises:
            Exception: If an error occurs during the clearing or sleep process.
        """

        try:
            self.epd.Clear()
            self.epd.sleep()
            logging.info("E-paper display cleared and set to sleep mode.")
        except Exception as e:
            logging.error(f"Error clearing display: {e}")
            raise
