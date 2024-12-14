import json
import os
from pathlib import Path

class Config:
    """Configuration manager for the application."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.settings = self._load_settings()
    
    def _get_config_dir(self) -> Path:
        """Get the configuration directory path."""
        if os.name == "nt":  # Windows
            config_dir = Path(os.getenv("APPDATA")) / "AIEmailAssistant"
        else:  # Linux/Mac
            config_dir = Path.home() / ".config" / "AIEmailAssistant"
            
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    def _load_settings(self) -> dict:
        """Load settings from the configuration file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                return {}
        return {}
    
    def _save_settings(self, settings: dict):
        """Save settings to the configuration file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def __getitem__(self, key):
        """Get a configuration value."""
        return self.settings.get(key)
    
    def __setitem__(self, key, value):
        """Set a configuration value."""
        self.settings[key] = value
        self._save_settings(self.settings)
    
    def get(self, key, default=None):
        """Get a configuration value with a default."""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value."""
        self.settings[key] = value
        self._save_settings(self.settings) 