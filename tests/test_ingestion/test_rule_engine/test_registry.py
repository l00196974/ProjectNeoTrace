"""
测试规则注册表
"""

import pytest
from src.ingestion.rule_engine.base import BaseRule, RuleContext, RuleResult
from src.ingestion.rule_engine.registry import RuleRegistry


class TestRuleA(BaseRule):
    """测试规则 A"""

    def evaluate(self, context: RuleContext) -> RuleResult:
        return RuleResult(triggered=True, reason="Rule A triggered")


class TestRuleB(BaseRule):
    """测试规则 B"""

    def evaluate(self, context: RuleContext) -> RuleResult:
        return RuleResult(triggered=False, reason="Rule B not triggered")


@pytest.fixture
def clear_registry():
    """清空注册表（需要时手动使用）"""
    RuleRegistry.clear_registry()
    yield
    RuleRegistry.clear_registry()


def test_register_rule(clear_registry):
    """测试注册规则"""
    RuleRegistry.register("test_rule_a", TestRuleA)

    registered = RuleRegistry.list_registered_types()
    assert "test_rule_a" in registered
    assert registered["test_rule_a"] == "TestRuleA"


def test_register_multiple_rules(clear_registry):
    """测试注册多个规则"""
    RuleRegistry.register("test_rule_a", TestRuleA)
    RuleRegistry.register("test_rule_b", TestRuleB)

    registered = RuleRegistry.list_registered_types()
    assert len(registered) == 2
    assert "test_rule_a" in registered
    assert "test_rule_b" in registered


def test_register_overwrites_existing(clear_registry):
    """测试注册覆盖已存在的规则"""
    RuleRegistry.register("test_rule", TestRuleA)
    RuleRegistry.register("test_rule", TestRuleB)

    registered = RuleRegistry.list_registered_types()
    assert registered["test_rule"] == "TestRuleB"


def test_create_rule(clear_registry):
    """测试创建规则实例"""
    RuleRegistry.register("test_rule_a", TestRuleA)

    config = {
        "type": "test_rule_a",
        "enabled": True,
        "priority": 100,
        "params": {"key": "value"}
    }

    rule = RuleRegistry.create_rule("my_rule", config)

    assert isinstance(rule, TestRuleA)
    assert rule.rule_id == "my_rule"
    assert rule.enabled is True
    assert rule.priority == 100
    assert rule.params == {"key": "value"}


def test_create_rule_missing_type(clear_registry):
    """测试创建规则缺少类型"""
    config = {"enabled": True}

    with pytest.raises(ValueError, match="缺少 'type' 字段"):
        RuleRegistry.create_rule("my_rule", config)


def test_create_rule_unregistered_type(clear_registry):
    """测试创建未注册的规则类型"""
    config = {"type": "nonexistent_rule"}

    with pytest.raises(ValueError, match="未注册的规则类型"):
        RuleRegistry.create_rule("my_rule", config)


def test_list_registered_types_empty(clear_registry):
    """测试列出空注册表"""
    registered = RuleRegistry.list_registered_types()
    assert registered == {}


def test_clear_registry(clear_registry):
    """测试清空注册表"""
    RuleRegistry.register("test_rule_a", TestRuleA)
    RuleRegistry.register("test_rule_b", TestRuleB)

    RuleRegistry.clear_registry()

    registered = RuleRegistry.list_registered_types()
    assert registered == {}
