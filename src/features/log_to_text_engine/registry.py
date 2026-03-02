"""转换规则注册表

管理规则类型的注册和创建
"""

from typing import Dict, Type
from .base import BaseConversionRule


class ConversionRuleRegistry:
    """转换规则注册表

    提供规则类型注册和工厂方法
    """

    _rules: Dict[str, Type[BaseConversionRule]] = {}

    @classmethod
    def register(cls, rule_type: str, rule_class: Type[BaseConversionRule]):
        """注册规则类型

        Args:
            rule_type: 规则类型标识
            rule_class: 规则类
        """
        cls._rules[rule_type] = rule_class

    @classmethod
    def create_rule(cls, config: Dict) -> BaseConversionRule:
        """从配置创建规则实例

        Args:
            config: 规则配置字典，必须包含 'type' 和 'id' 字段

        Returns:
            规则实例

        Raises:
            ValueError: 未知的规则类型或配置格式错误
        """
        if "type" not in config:
            raise ValueError("Rule config must contain 'type' field")
        if "id" not in config:
            raise ValueError("Rule config must contain 'id' field")

        rule_type = config["type"]
        rule_class = cls._rules.get(rule_type)

        if not rule_class:
            raise ValueError(f"Unknown rule type: {rule_type}")

        return rule_class(
            rule_id=config["id"],
            priority=config.get("priority", 50),
            enabled=config.get("enabled", True),
            params=config.get("params", {})
        )

    @classmethod
    def list_registered_types(cls) -> list:
        """列出所有已注册的规则类型

        Returns:
            规则类型列表
        """
        return list(cls._rules.keys())

    @classmethod
    def get_rule_class(cls, rule_type: str) -> Type[BaseConversionRule]:
        """获取规则类

        Args:
            rule_type: 规则类型

        Returns:
            规则类

        Raises:
            ValueError: 未知的规则类型
        """
        rule_class = cls._rules.get(rule_type)
        if not rule_class:
            raise ValueError(f"Unknown rule type: {rule_type}")
        return rule_class
