"""
Local Agent Configuration Module.

Purpose: Load and validate configuration from YAML files.
"""

from pathlib import Path
from typing import Dict, Any
import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "configs" / "localagent.yaml"


class LocalAgentConfig:
    """Configuration for the local agent."""
    
    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH):
        """Load configuration from YAML file."""
        self.config_path = Path(config_path).expanduser().resolve()
        self.config: Dict[str, Any] = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load and parse YAML configuration."""
        with self.config_path.open('r', encoding='utf-8') as f:
            loaded = yaml.safe_load(f)
        if not isinstance(loaded, dict):
            raise ValueError(f"Config root must be a mapping: {self.config_path}")
        return loaded
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split('.')
        value: Any = self.config
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return default
            value = value[k]
        return value
