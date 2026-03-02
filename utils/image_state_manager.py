import os
import json
import logging
from PIL import Image, ImageEnhance

# Logging setup
logging.basicConfig(level=logging.DEBUG)

# ---------------------------------------------------------------------------
# XP reward table — how many XP each action is worth
# ---------------------------------------------------------------------------
XP_REWARDS = {
    "device_found":      5,   # per device discovered by nmap
    "vuln_found":       15,   # per vulnerability matched
    "exploit_success":  30,   # per successful exploit
    "file_stolen":      50,   # per host files were exfiltrated from
    "handshake":        25,   # per WPA handshake captured
    "network_scanned":  10,   # per SSID fully scanned
}

def xp_for_level(level: int) -> int:
    """
    Total XP required to *reach* `level` from level 1.
    Quadratic curve — each level costs more than the last.
      Level 2  →    75 XP total
      Level 5  →  1 875 XP total
      Level 10 →  7 500 XP total
      Level 20 → 30 000 XP total
    Formula: sum of 75*k^2 for k=1..(level-1)
             = 75 * (level-1)*level*(2*level-1) / 6
    """
    if level <= 1:
        return 0
    n = level - 1
    return int(75 * n * (n + 1) * (2 * n + 1) / 6)


def level_from_xp(xp: int) -> int:
    """Derive current level from a raw XP total."""
    level = 1
    while xp >= xp_for_level(level + 1):
        level += 1
    return level


class ImageStateManager:
    """
    Manages dynamic image updates based on workflow states as well as
    persisting counters for various workflow statistics (handshakes, XP,
    level).  All persistent data lives in ``state.json`` (level/XP/meta)
    and ``handshake_state.json`` (handshake counter) at the repo root.
    """

    # Map workflow states to corresponding images
    IMAGE_MAP = {
        "scanning":            "./images/xeno_walking_right.png",
        "analyzing":           "./images/xeno_detective_right.png",
        "ready_to_attack":     "./images/xeno_preparing_to_attack.png",
        "attacking":           "./images/happy_xeno_ichigo.png",
        "success":             "./images/happy_xeno.png",
        "fallback":            "./images/xeno_walking_left.png",
        "validating":          "./images/xeno_attacking_left.png",
        "reconnaissance":      "./images/xeno_pikachu_hoodie_right.png",
        "investigating":       "./images/xeno_hoodie_left.png",
        "reviewing":           "./images/xeno_detective_left.png",
        "windows_fingerprint": "./images/xeno_windows_fingerprint.png",
        "linux_fingerprint":   "./images/xeno_linux_fingerprint.png",
        "file_stolen":         "./images/xeno_stolen_file.png",
        "handshake_capture":   "./images/xeno_handshake.png",
    }

    # Map workflow states to display messages
    MESSAGE_MAP = {
        "scanning":            "Sniffing the network..!",
        "analyzing":           "So many targets!",
        "ready_to_attack":     "Xeno is sharpening its claws...",
        "attacking":           "Xeno is on the hunt!",
        "success":             "Mission accomplished!",
        "fallback":            "Oops!",
        "validating":          "Double-checking...",
        "reconnaissance":      "Exploring the surroundings...",
        "investigating":       "Looking deeper...",
        "windows_fingerprint": "Windows, Gotcha!",
        "linux_fingerprint":   "Linux, Yummy!",
        "file_stolen":         "Xeno ate a file!",
        "reviewing":           "Pondering...",
    }

    STATE_FILE     = "state.json"
    HANDSHAKE_FILE = "handshake_state.json"

    def __init__(self):
        self.current_state = "scanning"
        self.handshakes    = 0
        self.xp            = 0
        self.level         = 1
        self.pet_name      = "Xeno"
        self.start_date    = ""
        self._load_state()
        self._load_handshake_state()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load_state(self):
        """Load level, XP, pet_name and start_date from state.json."""
        try:
            if os.path.exists(self.STATE_FILE):
                with open(self.STATE_FILE, "r") as fh:
                    data = json.load(fh)
                self.xp         = data.get("xp", 0)
                self.pet_name   = data.get("pet_name", "Xeno")
                self.start_date = data.get("start_date", "")
                # Always recompute level from XP so the two stay in sync
                self.level = level_from_xp(self.xp)
                logging.info(f"State loaded: {data}")
        except Exception as exc:
            logging.error(f"Failed to load state: {exc}")

    def _save_state(self):
        """Persist XP + level + meta to state.json."""
        try:
            data = {
                "level":      self.level,
                "xp":         self.xp,
                "start_date": self.start_date,
                "pet_name":   self.pet_name,
            }
            with open(self.STATE_FILE, "w") as fh:
                json.dump(data, fh)
            logging.info(f"State saved: {data}")
        except Exception as exc:
            logging.error(f"Failed to save state: {exc}")

    def _load_handshake_state(self):
        try:
            if os.path.exists(self.HANDSHAKE_FILE):
                with open(self.HANDSHAKE_FILE, "r") as fh:
                    data = json.load(fh)
                self.handshakes = data.get("handshakes", 0)
            else:
                self.handshakes = 0
        except Exception as exc:
            logging.error(f"Failed to load handshake state: {exc}")
            self.handshakes = 0

    def _save_handshake_state(self):
        try:
            with open(self.HANDSHAKE_FILE, "w") as fh:
                json.dump({"handshakes": self.handshakes}, fh)
        except Exception as exc:
            logging.error(f"Failed to save handshake state: {exc}")

    # ------------------------------------------------------------------
    # XP / Leveling API
    # ------------------------------------------------------------------

    def award_xp(self, action: str, count: int = 1) -> bool:
        """
        Award XP for a completed action.
        Returns True if a level-up occurred (so callers can react).

        Parameters:
            action (str): Key from XP_REWARDS (e.g. 'device_found').
            count  (int): How many times the action occurred.
        """
        reward = XP_REWARDS.get(action, 0) * count
        if reward <= 0:
            return False
        old_level  = self.level
        self.xp   += reward
        self.level = level_from_xp(self.xp)
        leveled_up = self.level > old_level
        if leveled_up:
            logging.info(
                f"[LEVEL UP] {old_level} → {self.level}  "
                f"(+{reward} XP, total {self.xp} XP)"
            )
        else:
            logging.info(
                f"[XP] +{reward} XP for '{action}' × {count}  "
                f"(total {self.xp} XP, level {self.level})"
            )
        self._save_state()
        return leveled_up

    def get_xp(self) -> int:
        return self.xp

    def get_level(self) -> int:
        return self.level

    def xp_for_next_level(self) -> int:
        """XP still needed to reach the next level."""
        return xp_for_level(self.level + 1) - self.xp

    def xp_progress_pct(self) -> int:
        """0-100 progress within the current level band."""
        current_thresh = xp_for_level(self.level)
        next_thresh    = xp_for_level(self.level + 1)
        band = next_thresh - current_thresh
        if band <= 0:
            return 100
        earned_in_band = self.xp - current_thresh
        return min(100, int(earned_in_band * 100 / band))

    # ------------------------------------------------------------------
    # Handshake counter
    # ------------------------------------------------------------------

    def increment_handshakes(self, count: int = 1):
        try:
            if count > 0:
                self.handshakes += count
                self._save_handshake_state()
        except Exception as exc:
            logging.error(f"Error incrementing handshake count: {exc}")

    def get_handshakes(self) -> int:
        return self.handshakes

    # ------------------------------------------------------------------
    # Image / state helpers
    # ------------------------------------------------------------------

    def load_image(self, state):
        try:
            image_path = self.IMAGE_MAP.get(state)
            if not image_path or not os.path.exists(image_path):
                raise FileNotFoundError(
                    f"Image not found for state: {state} at {image_path}"
                )
            logging.info(f"Loading image for state: {state}")
            original_image = Image.open(image_path)
            enhancer = ImageEnhance.Contrast(original_image)
            return enhancer.enhance(2)
        except Exception as e:
            logging.error(f"Error loading image for state '{state}': {e}")
            raise

    def set_state(self, state):
        if state not in self.IMAGE_MAP:
            raise ValueError(
                f"Invalid state: {state}. "
                f"Available states: {list(self.IMAGE_MAP.keys())}"
            )
        self.current_state = state
        logging.info(f"Workflow state updated to: {state}")

    def get_image_and_message_for_current_state(self):
        image   = self.load_image(self.current_state)
        message = self.MESSAGE_MAP.get(
            self.current_state, "Xeno is doing its thing!"
        )
        return image, message
