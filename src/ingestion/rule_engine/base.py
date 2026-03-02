"""
规则引擎基础类定义
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class RuleContext:
    """规则执行上下文"""
    event: Dict[str, Any]
    state: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleResult:
    """规则执行结果"""
    triggered: bool
    reason: str
    new_state: Optional[Dict[str, Any]] = None


class BaseRule(ABC):
    """规则基类"""

    def __init__(self, rule_id: str, config: Dict[str, Any]):
        self.rule_id = rule_id
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 0)
        self.params = config.get("params", {})

    @abstractmethod
    def evaluate(self, context: RuleContext) -> RuleResult:
        """
        评估规则是否触发

        Args:
            context: 规则执行上下文

        Returns:
            RuleResult: 规则执行结果
        """
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.rule_id}, priority={self.priority}, enabled={self.enabled})"
