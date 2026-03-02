import os
import json
import datetime
import traceback


# Centralized log file paths
ERROR_LOG_FILE = "logs/errors.json"
ACTIVITY_LOG_FILE = "logs/activity.json"
MAX_ACTIVITY_ENTRIES = 300


class Logger:
    def __init__(self, log_file="logs/scan.log", log_level="INFO"):
        self.log_file = log_file
        self.log_level = self._get_log_level_value(log_level)
        self._ensure_log_directory()
        # Ensure error log directory exists
        os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)

    def _ensure_log_directory(self):
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", encoding="utf-8") as file:
                file.write("")

    def _get_log_level_value(self, log_level):
        levels = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
        return levels.get(log_level.upper(), 20)

    def log(self, message, level="INFO", exc_info=False):
        # Auto-detect level from message prefix like [ERROR], [WARNING], etc.
        detected_level = level
        for lvl in ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "SUCCESS", "FAILED"):
            if message.startswith(f"[{lvl}]"):
                detected_level = lvl if lvl not in ("SUCCESS", "FAILED") else "INFO"
                break

        level_value = self._get_log_level_value(detected_level)
        if level_value >= self.log_level:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{timestamp}] [{detected_level}] {message}"
            print(log_message)
            with open(self.log_file, "a", encoding="utf-8", errors="replace") as file:
                file.write(log_message + "\n")
                if exc_info:
                    file.write(traceback.format_exc() + "\n")

        # Auto-write errors/criticals to the centralized error log
        if detected_level in ("ERROR", "CRITICAL"):
            self._write_error(message, detected_level, exc_info)

    def error(self, message, exc_info=True):
        """Convenience method for logging errors with traceback."""
        self.log(message, level="ERROR", exc_info=exc_info)

    def log_exception(self, message, exception, context=None):
        """
        Log a caught exception with full traceback and optional context.
        Also writes to the centralized error JSON log.
        """
        tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
        tb_str = "".join(tb)
        full_msg = f"[ERROR] {message}: {exception}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [ERROR] {message}: {exception}\n{tb_str}"
        print(log_message)
        with open(self.log_file, "a", encoding="utf-8", errors="replace") as file:
            file.write(log_message + "\n")

        self._write_error(
            message=f"{message}: {exception}",
            level="ERROR",
            exc_info=False,
            traceback_str=tb_str,
            context=context
        )

    def _write_error(self, message, level="ERROR", exc_info=False, traceback_str=None, context=None):
        """Append an error entry to the centralized JSON error log."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = {
                "timestamp": timestamp,
                "level": level,
                "message": message,
                "traceback": traceback_str or (traceback.format_exc() if exc_info else None),
                "context": context or {}
            }
            # Load existing errors
            errors = []
            if os.path.exists(ERROR_LOG_FILE):
                try:
                    with open(ERROR_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                        data = json.load(f)
                        errors = data.get("errors", [])
                except (json.JSONDecodeError, IOError):
                    errors = []

            errors.append(entry)

            # Keep last 500 errors to prevent unbounded growth
            if len(errors) > 500:
                errors = errors[-500:]

            with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump({"errors": errors, "last_updated": timestamp}, f, indent=2)
        except Exception:
            # Last resort: don't crash the logger itself
            pass

    @staticmethod
    def get_errors(limit=100, level_filter=None):
        """
        Read errors from the centralized error log.
        Returns list of error dicts, newest first.
        """
        try:
            if not os.path.exists(ERROR_LOG_FILE):
                return []
            with open(ERROR_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            errors = data.get("errors", [])
            if level_filter:
                errors = [e for e in errors if e.get("level") == level_filter]
            return list(reversed(errors[:limit]))
        except Exception:
            return []

    @staticmethod
    def clear_errors():
        """Clear all errors from the centralized log."""
        try:
            with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump({"errors": [], "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)
        except Exception:
            pass

    # ─── Activity Feed ───────────────────────────────────────────────

    def activity(self, phase, ssid, message, status="running", details=None):
        """
        Log a live-activity event for the web dashboard.
        phase:   workflow step name (e.g. 'handshake_capture', 'nmap_discovery')
        ssid:    target network
        message: human-readable description
        status:  running | success | error | skipped
        details: optional dict with extra info
        """
        try:
            os.makedirs(os.path.dirname(ACTIVITY_LOG_FILE), exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = {
                "timestamp": timestamp,
                "phase": phase,
                "ssid": ssid,
                "message": message,
                "status": status,
                "details": details or {}
            }
            events = []
            if os.path.exists(ACTIVITY_LOG_FILE):
                try:
                    with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                        data = json.load(f)
                        events = data.get("events", [])
                except (json.JSONDecodeError, IOError):
                    events = []

            events.append(entry)
            if len(events) > MAX_ACTIVITY_ENTRIES:
                events = events[-MAX_ACTIVITY_ENTRIES:]

            with open(ACTIVITY_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump({"events": events, "last_updated": timestamp}, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def get_activity(limit=50, ssid_filter=None):
        """Read recent activity events, newest first."""
        try:
            if not os.path.exists(ACTIVITY_LOG_FILE):
                return []
            with open(ACTIVITY_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
            events = data.get("events", [])
            if ssid_filter:
                events = [e for e in events if e.get("ssid") == ssid_filter]
            return list(reversed(events[-limit:]))
        except Exception:
            return []

    @staticmethod
    def clear_activity():
        """Clear all activity events."""
        try:
            with open(ACTIVITY_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump({"events": [], "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f, indent=2)
        except Exception:
            pass
