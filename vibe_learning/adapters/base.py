from abc import ABC, abstractmethod
from ..schema import UniversalContext


class BaseAdapter(ABC):
    """Adapter Layer Base.
    Every adapter converts IDE-native artifacts into UniversalContext.
    The swarm knows nothing about IDE internals.
    """

    @abstractmethod
    def extract(self, project_root: str) -> UniversalContext:
        pass
