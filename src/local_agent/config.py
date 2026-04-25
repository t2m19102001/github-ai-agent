"""
Local Agent Configuration Module.

Purpose: Load and validate configuration from YAML files.
"""

from typing import Dict, Any
import yaml


class LocalAgentConfig:
    """Configuration for the local agent."""
    
    def __init__(self, config_path: str = "configs/localagent.yaml"):
        """Load configuration from YAML file."""
        self.config_path = config_path
        self.config: Dict[str, Any] = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load and parse YAML configuration."""
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value.get(k, {})
        return value if value != {} else default
