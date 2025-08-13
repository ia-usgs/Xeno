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
import socket

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
        """
        self.epd = epd2in13_V4.EPD()
        self.width = 122   # Display width
        self.height = 250  # Display height
        self.age = 0       # Age in days
        self.level = 1
        self.start_date = None
        self.pet_name = "Xeno"
        self.load_state()
        logging.info("EPaperDisplay initialized.")

    def load_state(self):
        """
        Load the saved display state from a JSON file.
        """
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    state = json.load(f)
                self.level = state.get("level", 1)
                self.start_date = state.get("start_date", None)
                self.pet_name = state.get("pet_name", "Xeno")
                if self.start_date:
                    start_date_obj = datetime.strptime(self.start_date, "%Y-%m-%d")
                    self.age = (datetime.now() - start_date_obj).days
                else:
                    self.age = 0
                logging.info(f"State loaded: {state}")
            except Exception as e:
                logging.error(f"Error loading state file: {e}")
        else:
            # First run
            self.start_date = datetime.now().strftime("%Y-%m-%d")
            logging.info("No saved state found. Initializing with current date.")

    def save_state(self):
        """
        Save the current display state to a JSON file.
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
        """
        try:
            if partial_refresh:
                logging.info("Initializing for partial refresh.")
                self.epd.init_fast()
            else:
                logging.info("Initializing for full refresh.")
                self.epd.init()
            self.epd.Clear(0xFF)
        except Exception as e:
            logging.error(f"Failed to initialize display: {e}")
            raise

    def prepare_image(self, image):
        """
        Resize and process an image to fit the e-paper display.
        """
        try:
            resized = image.resize((90, 90), resample=Image.LANCZOS)
            bw = resized.convert('1', dither=Image.FLOYDSTEINBERG)
            logging.info("Image prepared for display.")
            return bw
        except Exception as e:
            logging.error(f"Error preparing image: {e}")
            raise

    def calculate_level(self, stats):
        """
        Calculate the level dynamically based on cumulative stats.
        """
        try:
            cycle_score = (
                stats["targets"] * 10 +
                stats["vulns"]   * 20 +
                stats["exploits"]* 30 +
                stats["files"]   * 5
            )
            threshold = self.level * 100
            while cycle_score >= threshold:
                self.level += 1
                cycle_score -= threshold
                threshold = self.level * 125
        except KeyError as e:
            logging.error(f"Missing key in stats: {e}")
            raise

    def draw_layout(self, image, current_ssid="Not Connected", current_status="Initializing...", stats=None):
        """
        Draw a custom layout for the e-paper display.
        """
        if stats is None:
            stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}

        try:
            # Update level
            self.calculate_level(stats)

            # Fetch current IP for display
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
                s.close()
            except Exception:
                ip_address = "Unknown"

            # Canvas and drawing context
            canvas = Image.new('1', (self.width, self.height), 255)
            draw = ImageDraw.Draw(canvas)

            # Border
            draw.rectangle((1, 1, self.width-1, self.height-1), outline=0)

            # Top bar: SSID & IP
            draw.rectangle((0, 0, self.width, 20), fill=0)
            font_small = ImageFont.truetype(
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 8)
            draw.text((5, 2),  f"SSID: {current_ssid}", font=font_small, fill=255)
            draw.text((5,12), f"IP:   {ip_address}",   font=font_small, fill=255)

            # Separators
            draw.line((0,20, self.width,20), fill=0)
            draw.line((0,45, self.width,45), fill=0)
            draw.line((0,95, self.width,95), fill=0)

            # Stats
            font_stats = ImageFont.truetype(
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 8)
            draw.text((5,25),  f"Targets: {stats['targets']}" , font=font_stats, fill=0)
            draw.text((75,25), f"Vulns:   {stats['vulns']}"   , font=font_stats, fill=0)
            draw.text((5,35),  f"Exploits:{stats['exploits']}", font=font_stats, fill=0)
            draw.text((75,35), f"Files:   {stats['files']}"   , font=font_stats, fill=0)

            # Status box
            font_body = ImageFont.truetype(
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 8)
            draw.text((40,50), "Status:", font=font_body, fill=0)
            draw.text((5,65),  current_status, font=font_body, fill=0)

            # Pet name, age & level
            draw.text((35,100), self.pet_name, font=font_body, fill=0)
            draw.text((5,110),  f"Age:   {self.age} days", font=font_body, fill=0)
            draw.text((75,110), f"Level: {self.level}",     font=font_body, fill=0)

            # -----------------------------------------------------------------
            # Handshake indicator
            # We reserve a small region beneath the Age/Level row (y≈120) to
            # draw a minimalist handshake icon along with the total count.
            # The icon is rendered using simple shapes so we do not depend
            # on external image assets.  A pair of overlapping ellipses
            # suggests two hands shaking.  Immediately to the right of
            # the icon we draw the numeric count of captured handshakes.
            handshakes = stats.get('handshakes', 0)
            # Coordinates for the icon (x, y) and size
            icon_x = 5
            icon_y = 120
            icon_w = 12
            icon_h = 8
            # Draw a background box around the icon for clarity
            draw.rectangle(
                (icon_x, icon_y, icon_x + icon_w + 4, icon_y + icon_h),
                outline=0,
                fill=255
            )
            # Left 'hand'
            draw.ellipse(
                (icon_x + 1, icon_y + 1, icon_x + 5, icon_y + 5),
                outline=0,
                fill=0
            )
            # Right 'hand'
            draw.ellipse(
                (icon_x + 5, icon_y + 1, icon_x + 9, icon_y + 5),
                outline=0,
                fill=0
            )
            # Overlap shading: draw a smaller white ellipse to
            # emphasise the handshake grip
            draw.ellipse(
                (icon_x + 4, icon_y + 2, icon_x + 7, icon_y + 4),
                outline=255,
                fill=255
            )
            # Numeric count; offset x to leave room after the icon
            draw.text(
                (icon_x + 17, icon_y),
                f"{handshakes}",
                font=font_body,
                fill=0
            )

            # Xeno image
            canvas.paste(image, (17,150))

            logging.info("Dynamic layout drawn successfully.")
            self.save_state()
            return canvas

        except Exception as e:
            logging.error(f"Error drawing layout: {e}")
            raise

    def display_image(self, canvas, use_partial_update=True):
        """
        Display the given image on the e-paper display.
        """
        try:
            buf = self.epd.getbuffer(canvas)
            if use_partial_update:
                self.epd.displayPartial(buf)
            else:
                self.epd.display(buf)
        except Exception as e:
            logging.error(f"Failed to display image: {e}")
            raise

    def clear(self):
        """
        Clear the e-paper display and put it to sleep.
        """
        try:
            self.epd.Clear()
            self.epd.sleep()
            logging.info("Display cleared and sleeping.")
        except Exception as e:
            logging.error(f"Error clearing display: {e}")
            raise
