import logging
from PIL import Image
from utils.display import EPaperDisplay
from utils.image_state_manager import ImageStateManager

class DisplayService:
    def __init__(self):
        # suppress PIL debug chatter
        logging.getLogger("PIL").setLevel(logging.WARNING)

        self.display = EPaperDisplay()
        self.state_mgr = ImageStateManager()

    def initialize(self):
        # full refresh to clear ghosts
        self.display.initialize(partial_refresh=False)

        # draw the “Initializing…” template
        stats = {"targets": 0, "vulns": 0, "exploits": 0, "files": 0}
        blank = Image.new('1', (60, 60), color=255)
        prepared = self.display.prepare_image(blank)
        layout = self.display.draw_layout(
            prepared,
            current_ssid="Not Connected",
            current_status="Initializing...",
            stats=stats
        )
        self.display.display_image(layout, use_partial_update=False)

    def update(self, state, ssid, status, stats, partial=True):
        self.state_mgr.set_state(state)
        image, msg = self.state_mgr.get_image_and_message_for_current_state()
        prepared = self.display.prepare_image(image)
        if not partial:
            # reinitialize for a full-refresh
            self.display.initialize(partial_refresh=False)
        full_status = f"{status}\n{msg}"
        layout = self.display.draw_layout(
            prepared,
            current_ssid=ssid,
            current_status=full_status,
            stats=stats
        )
        self.display.display_image(layout, use_partial_update=partial)

    def clear(self):
        self.display.clear()
