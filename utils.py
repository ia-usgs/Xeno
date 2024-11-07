import json

def log_error(module, message, error):
    print(f"[{module}] {message}: {error}")

def load_config(file_path):
    """Loads configuration from a JSON file and returns it as a dictionary."""
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        log_error("Config Loader", f"Failed to load config from {file_path}", e)
        return None
