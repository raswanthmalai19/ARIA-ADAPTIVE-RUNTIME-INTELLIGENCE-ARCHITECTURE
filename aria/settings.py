"""
ARIA User Settings Manager
Persists user preferences to JSON file
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import threading

logger = logging.getLogger("aria.settings")


class SettingsManager:
    """Manage user settings with persistent storage."""
    
    DEFAULT_SETTINGS = {
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 512,
        "execution_mode": "adaptive",
        "model": "mlx-community/Qwen2.5-3B-Instruct-4bit",
        "theme": "dark",
        "auto_save_history": True,
        "keep_history_days": 30,
        "notifications_enabled": True,
    }
    
    def __init__(self, settings_path: Optional[str] = None):
        """Initialize settings manager."""
        if settings_path is None:
            home = Path.home()
            aria_dir = home / ".aria"
            aria_dir.mkdir(exist_ok=True)
            settings_path = aria_dir / "settings.json"
        
        self.settings_path = Path(settings_path)
        self.lock = threading.Lock()
        self.settings = self.DEFAULT_SETTINGS.copy()
        
        # Load existing settings
        self._load()
    
    def _load(self):
        """Load settings from file."""
        try:
            if self.settings_path.exists():
                with open(self.settings_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (new settings might be added)
                    self.settings = {**self.DEFAULT_SETTINGS, **loaded}
                logger.info(f"Settings loaded from {self.settings_path}")
            else:
                self.settings = self.DEFAULT_SETTINGS.copy()
                self._save()
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            self.settings = self.DEFAULT_SETTINGS.copy()
    
    def _save(self):
        """Save settings to file."""
        try:
            with self.lock:
                with open(self.settings_path, 'w') as f:
                    json.dump(self.settings, f, indent=2)
                logger.debug(f"Settings saved to {self.settings_path}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting."""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a setting and persist."""
        if key not in self.DEFAULT_SETTINGS and not key.startswith("custom_"):
            logger.warning(f"Setting unknown key: {key}")
        
        self.settings[key] = value
        self._save()
        logger.debug(f"Setting updated: {key} = {value}")
    
    def update(self, updates: Dict[str, Any]):
        """Update multiple settings at once."""
        self.settings.update(updates)
        self._save()
        logger.debug(f"Settings updated: {len(updates)} keys")
    
    def get_all(self) -> Dict[str, Any]:
        """Get all settings."""
        return self.settings.copy()
    
    def reset(self):
        """Reset to default settings."""
        self.settings = self.DEFAULT_SETTINGS.copy()
        self._save()
        logger.info("Settings reset to defaults")
    
    def validate(self) -> bool:
        """Validate settings values."""
        try:
            # Validate temperature (0-2)
            temp = self.get("temperature", 0.7)
            if not (0 <= temp <= 2):
                logger.warning(f"Invalid temperature: {temp}, resetting to 0.7")
                self.set("temperature", 0.7)
            
            # Validate top_p (0-1)
            top_p = self.get("top_p", 0.95)
            if not (0 < top_p <= 1):
                logger.warning(f"Invalid top_p: {top_p}, resetting to 0.95")
                self.set("top_p", 0.95)
            
            # Validate max_tokens
            max_tokens = self.get("max_tokens", 512)
            if not (1 <= max_tokens <= 8192):
                logger.warning(f"Invalid max_tokens: {max_tokens}, resetting to 512")
                self.set("max_tokens", 512)
            
            # Validate execution mode
            mode = self.get("execution_mode", "adaptive")
            if mode not in ["adaptive", "baseline", "cascade"]:
                logger.warning(f"Invalid mode: {mode}, resetting to adaptive")
                self.set("execution_mode", "adaptive")
            
            return True
        except Exception as e:
            logger.error(f"Settings validation failed: {e}")
            return False


# Global settings instance
_settings_instance = None

def get_settings() -> SettingsManager:
    """Get global settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SettingsManager()
        _settings_instance.validate()
    return _settings_instance
