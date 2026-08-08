import json
import os
import config

class ConfigManager:
    """
    Manages loading, parsing, fallback defaults, and writing of config.json
    for dynamic runtime parameter updates.
    """
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self._data = {}
        self.load()

    def load(self) -> None:
        """Loads configuration from config.json, if it exists."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self._data = json.load(f)
            except Exception as e:
                print(f"[ConfigManager] Warning: failed to parse {self.config_path}: {e}")
                self._data = {}
        else:
            self._data = {}

    def get(self, key: str, default=None):
        """
        Retrieves a configuration key. Checks config.json first,
        falling back to config.py defaults if missing, then the default arg.
        """
        # 1. Check loaded JSON config
        if key in self._data:
            return self._data[key]
        # 2. Check fallback static config.py values
        if hasattr(config, key):
            return getattr(config, key)
        return default

    def set(self, key: str, value) -> None:
        """Sets a configuration value and saves it to disk."""
        self._data[key] = value
        self.save()

    def save(self) -> None:
        """Saves current configuration to config.json."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            print(f"[ConfigManager] Error writing {self.config_path}: {e}")
