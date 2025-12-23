from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AgentPluginBase(ABC):
    name: str = "plugin"
    description: str = ""

    @abstractmethod
    def matches(self, event: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def run(self, event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        pass


class PluginManager:
    def __init__(self, plugins: Optional[List[AgentPluginBase]] = None):
        self.plugins = plugins or []

    def register(self, plugin: AgentPluginBase):
        self.plugins.append(plugin)

    def run_plugins(self, event: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        for p in self.plugins:
            try:
                if p.matches(event):
                    res = p.run(event, context)
                    if res:
                        results.append({"plugin": p.name, **res})
            except Exception as e:
                logger.error(f"Plugin {p.name} error: {e}")
        return results

