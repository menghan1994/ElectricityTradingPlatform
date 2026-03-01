from typing import Any

from rules.base import BaseRule


class RuleRegistry:
    def __init__(self):
        self._rules: dict[str, BaseRule] = {}

    def register(self, name: str, rule: BaseRule) -> None:
        self._rules[name] = rule

    def get(self, name: str) -> BaseRule | None:
        return self._rules.get(name)

    def list_names(self) -> list[str]:
        return list(self._rules.keys())

    def evaluate(self, name: str, context: dict[str, Any]) -> dict[str, Any]:
        rule = self.get(name)
        if rule is None:
            raise KeyError(f"Rule '{name}' not found in registry")
        return rule.evaluate(context)


registry = RuleRegistry()


def register_province(name: str):
    """装饰器：自动注册省份规则实现类到 registry。"""
    def decorator(cls):
        registry.register(name, cls())
        return cls
    return decorator
