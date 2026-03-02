"""
规则注册表 - 支持规则注册和工厂创建
"""

import logging
from typing import Dict, Type

from .base import BaseRule

logger = logging.getLogger(__name__)


class RuleRegistry:
    """规则注册表 - 支持自定义规则扩展"""

    _registry: Dict[str, Type[BaseRule]] = {}

    @classmethod
    def register(cls, rule_type: str, rule_class: Type[BaseRule]):
        """
        注册规则类

        Args:
            rule_type: 规则类型标识
            rule_class: 规则类
        """
        if rule_type in cls._registry:
            logger.warning(f"规则类型 {rule_type} 已存在，将被覆盖")
        cls._registry[rule_type] = rule_class
        logger.info(f"注册规则类型: {rule_type} -> {rule_class.__name__}")

    @classmethod
    def create_rule(cls, rule_id: str, rule_config: Dict) -> BaseRule:
        """
        工厂方法 - 创建规则实例

        Args:
            rule_id: 规则ID
            rule_config: 规则配置

        Returns:
            BaseRule: 规则实例

        Raises:
            ValueError: 规则类型未注册
        """
        rule_type = rule_config.get("type")
        if not rule_type:
            raise ValueError(f"规则配置缺少 'type' 字段: {rule_id}")

        if rule_type not in cls._registry:
            raise ValueError(f"未注册的规则类型: {rule_type}")

        rule_class = cls._registry[rule_type]
        return rule_class(rule_id, rule_config)

    @classmethod
    def list_registered_types(cls) -> Dict[str, str]:
        """列出所有已注册的规则类型"""
        return {
            rule_type: rule_class.__name__
            for rule_type, rule_class in cls._registry.items()
        }

    @classmethod
    def clear_registry(cls):
        """清空注册表（主要用于测试）"""
        cls._registry.clear()
        logger.info("清空规则注册表")
