from abc import ABC, abstractmethod
from typing import Any


class BaseRule(ABC):
    @abstractmethod
    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        ...
