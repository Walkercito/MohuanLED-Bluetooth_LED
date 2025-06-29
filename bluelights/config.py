import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class LEDConfig:
    """LED device configuration."""
    mac_address: Optional[str] = None
    uuid: Optional[str] = None
    auto_connect: bool = True
    reconnect_attempts: int = 3
    connection_timeout: int = 10

@dataclass
class GUIConfig:
    """GUI configuration."""
    theme: str = "default"
    start_minimized: bool = False
    minimize_to_tray: bool = True
    window_geometry: Optional[Dict[str, int]] = None
    remember_last_color: bool = True
    last_color: Dict[str, int] = None
    
    def __post_init__(self):
        if self.last_color is None:
            self.last_color = {"red": 255, "green": 255, "blue": 255}
        if self.window_geometry is None:
            self.window_geometry = {"x": 100, "y": 100, "width": 400, "height": 600}

@dataclass
class EffectsConfig:
    """Effects configuration."""
    default_duration: float = 5.0
    rainbow_speed: float = 0.05
    breathing_duration: float = 3.0
    strobe_flashes: int = 10
    strobe_duration: float = 2.0

@dataclass
class AppConfig:
    """Main application configuration."""
    led: LEDConfig
    gui: GUIConfig
    effects: EffectsConfig
    debug: bool = False
    log_level: str = "INFO"
    
    def __post_init__(self):
        if isinstance(self.led, dict):
            self.led = LEDConfig(**self.led)
        if isinstance(self.gui, dict):
            self.gui = GUIConfig(**self.gui)
        if isinstance(self.effects, dict):
            self.effects = EffectsConfig(**self.effects)

class ConfigManager:
    """Manages application configuration."""
    
    DEFAULT_CONFIG_FILENAME = "led_controller_config.json"
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the config manager.
        
        Args:
            config_dir: Directory to store config files. If None, uses default.
        """
        load_dotenv()
        
        if config_dir is None:
            if os.name == 'nt':
                config_dir = Path.home() / "AppData" / "Local" / "LEDController"
            else:
                config_dir = Path.home() / ".config" / "led_controller"
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILENAME
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._config = self._create_default_config()
        
        self.load()
    
    def _create_default_config(self) -> AppConfig:
        """Create default configuration."""
        mac_address = os.getenv('LED_MAC_ADDRESS')
        uuid = os.getenv('LED_UUID')
        debug = os.getenv('DEBUG', 'false').lower() == 'true'
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        return AppConfig(
            led=LEDConfig(
                mac_address=mac_address,
                uuid=uuid
            ),
            gui=GUIConfig(),
            effects=EffectsConfig(),
            debug=debug,
            log_level=log_level
        )
    
    def load(self) -> None:
        """Load configuration from file."""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._config = AppConfig(**{**asdict(self._config), **data})
                logger.info(f"Configuration loaded from {self.config_file}")
            else:
                logger.info("No existing config file found, using defaults")
                
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            logger.info("Using default configuration")
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self) -> AppConfig:
        """Get the current configuration."""
        return self._config
    
    def update(self, **kwargs) -> None:
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        self.save()
    
    def update_led_config(self, **kwargs) -> None:
        """Update LED configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config.led, key):
                setattr(self._config.led, key, value)
        self.save()
    
    def update_gui_config(self, **kwargs) -> None:
        """Update GUI configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config.gui, key):
                setattr(self._config.gui, key, value)
        self.save()
    
    def update_effects_config(self, **kwargs) -> None:
        """Update effects configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config.effects, key):
                setattr(self._config.effects, key, value)
        self.save()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self._config = self._create_default_config()
        self.save()
        logger.info("Configuration reset to defaults")
    
    def export_config(self, filepath: Path) -> None:
        """Export configuration to a specific file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._config), f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration exported to {filepath}")
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
    
    def import_config(self, filepath: Path) -> None:
        """Import configuration from a specific file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self._config = AppConfig(**data)
            self.save()
            logger.info(f"Configuration imported from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
    
    @property
    def led_mac_address(self) -> Optional[str]:
        """Get LED MAC address."""
        return self._config.led.mac_address
    
    @property
    def led_uuid(self) -> Optional[str]:
        """Get LED UUID."""
        return self._config.led.uuid
    
    @property
    def should_auto_connect(self) -> bool:
        """Check if auto-connect is enabled."""
        return self._config.led.auto_connect
    
    @property
    def gui_theme(self) -> str:
        """Get GUI theme."""
        return self._config.gui.theme
    
    @property
    def remember_last_color(self) -> bool:
        """Check if last color should be remembered."""
        return self._config.gui.remember_last_color
    
    @property
    def last_color(self) -> Dict[str, int]:
        """Get last used color."""
        return self._config.gui.last_color.copy()

_config_manager: Optional[ConfigManager] = None

def get_config_manager() -> ConfigManager:
    """Get the global config manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config() -> AppConfig:
    """Get the current configuration."""
    return get_config_manager().get()