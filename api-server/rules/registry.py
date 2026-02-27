from typing import Any

from rules.base import BaseRule


class RuleRegistry:
    def __init__(self):
        self._rules: dict[str, BaseRule] = {}

    def register(self, name: str, rule: BaseRule) -> None:
        self._rules[name] = rule

    def get(self, name: str) -> BaseRule | None:
        return self._rules.get(name)

    def evaluate(self, name: str, context: dict[str, Any]) -> dict[str, Any]:
        rule = self.get(name)
        if rule is None:
            raise KeyError(f"Rule '{name}' not found in registry")
        return rule.evaluate(context)


registry = RuleRegistry()
