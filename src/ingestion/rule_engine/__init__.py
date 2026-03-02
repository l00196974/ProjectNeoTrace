"""
规则引擎模块 - 用于 Session 切片规则管理

提供可扩展的规则引擎框架，支持：
- 策略模式：每个规则独立实现
- 责任链模式：按优先级执行规则
- 配置驱动：通过 YAML 配置规则参数
"""

from .base import BaseRule, RuleContext, RuleResult
from .engine import RuleEngine
from .registry import RuleRegistry
from .rules import ScreenOffRule, LBSCrossingRule, AppCategoryRule

# 注册内置规则
RuleRegistry.register("screen_off", ScreenOffRule)
RuleRegistry.register("lbs_crossing", LBSCrossingRule)
RuleRegistry.register("app_category_change", AppCategoryRule)

__all__ = [
    "BaseRule",
    "RuleContext",
    "RuleResult",
    "RuleEngine",
    "RuleRegistry",
    "ScreenOffRule",
    "LBSCrossingRule",
    "AppCategoryRule",
]
