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
        """
        Initialize the e‑ink display with a full refresh and draw the
        starting layout.  This method seeds the handshake counter
        into the stats dictionary so that the first screen after
        reboot accurately reflects any previously captured handshakes.

        The handshake count is obtained from ImageStateManager.  If
        additional counters are added in the future, they can be
        incorporated here in a similar fashion.
        """
        # full refresh to clear ghosts
        self.display.initialize(partial_refresh=False)

        # build an initial stats dictionary including persistent handshake count
        stats = {
            "targets": 0,
            "vulns":   0,
            "exploits":0,
            "files":   0,
            # Always include the persistent handshake count for the
            # very first screen.  This ensures the user sees the
            # total number of captured handshakes even before any
            # new captures occur in this session.
            "handshakes": self.state_mgr.get_handshakes()
        }
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
        """
        Update the display to a new workflow state.  This method
        ensures that the handshake count persists on every display
        update by merging the count from ImageStateManager into the
        provided stats dictionary.  Callers can override the
        handshake count by explicitly including the 'handshakes'
        key in the stats argument (useful immediately after an
        increment) but otherwise the persisted value will be used.

        Parameters:
            state (str): The workflow state to transition to.
            ssid (str):  The current SSID (or description) to show.
            status (str): A short status message for the user.
            stats (dict): A dictionary of counters (targets, vulns,
                          exploits, files) and optionally the
                          handshake count.
            partial (bool): Whether to use a partial display update.
        """
        # set new state in the state manager
        self.state_mgr.set_state(state)
        # retrieve the appropriate image and message for this state
        image, msg = self.state_mgr.get_image_and_message_for_current_state()
        prepared = self.display.prepare_image(image)
        # reinitialize the display for a full refresh if requested
        if not partial:
            self.display.initialize(partial_refresh=False)
        # merge handshake count: if the caller hasn't specified
        # 'handshakes' explicitly, use the persisted value
        merged_stats = dict(stats)  # shallow copy to avoid modifying caller's dict
        if 'handshakes' not in merged_stats:
            merged_stats['handshakes'] = self.state_mgr.get_handshakes()
        # combine status message with the state's descriptive message
        full_status = f"{status}\n{msg}"
        # draw layout with merged stats and show on display
        layout = self.display.draw_layout(
            prepared,
            current_ssid=ssid,
            current_status=full_status,
            stats=merged_stats
        )
        self.display.display_image(layout, use_partial_update=partial)

    def clear(self):
        self.display.clear()
