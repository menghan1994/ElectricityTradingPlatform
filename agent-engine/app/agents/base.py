from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    @abstractmethod
    async def invoke(self, state: dict[str, Any]) -> dict[str, Any]:
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
