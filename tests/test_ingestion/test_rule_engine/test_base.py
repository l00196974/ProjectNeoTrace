"""
测试规则基类
"""

import pytest
from src.ingestion.rule_engine.base import BaseRule, RuleContext, RuleResult


class MockRule(BaseRule):
    """测试用的模拟规则"""

    def evaluate(self, context: RuleContext) -> RuleResult:
        threshold = self.params.get("threshold", 10)
        value = context.event.get("value", 0)

        if value > threshold:
            return RuleResult(
                triggered=True,
                reason=f"值 {value} 超过阈值 {threshold}",
                new_state={"last_value": value}
            )
        return RuleResult(triggered=False, reason="未超过阈值")


def test_rule_context_creation():
    """测试规则上下文创建"""
    event = {"action": "test", "value": 100}
    state = {"counter": 5}
    metadata = {"source": "test"}

    context = RuleContext(event=event, state=state, metadata=metadata)

    assert context.event == event
    assert context.state == state
    assert context.metadata == metadata


def test_rule_context_default_metadata():
    """测试规则上下文默认元数据"""
    context = RuleContext(event={}, state={})
    assert context.metadata == {}


def test_rule_result_creation():
    """测试规则结果创建"""
    result = RuleResult(
        triggered=True,
        reason="测试触发",
        new_state={"key": "value"}
    )

    assert result.triggered is True
    assert result.reason == "测试触发"
    assert result.new_state == {"key": "value"}


def test_rule_result_without_new_state():
    """测试规则结果不带新状态"""
    result = RuleResult(triggered=False, reason="未触发")

    assert result.triggered is False
    assert result.reason == "未触发"
    assert result.new_state is None


def test_base_rule_initialization():
    """测试规则基类初始化"""
    config = {
        "enabled": True,
        "priority": 100,
        "params": {"threshold": 50}
    }

    rule = MockRule("test_rule", config)

    assert rule.rule_id == "test_rule"
    assert rule.enabled is True
    assert rule.priority == 100
    assert rule.params == {"threshold": 50}


def test_base_rule_default_values():
    """测试规则基类默认值"""
    rule = MockRule("test_rule", {})

    assert rule.rule_id == "test_rule"
    assert rule.enabled is True
    assert rule.priority == 0
    assert rule.params == {}


def test_mock_rule_evaluate_triggered():
    """测试模拟规则触发"""
    rule = MockRule("test_rule", {"params": {"threshold": 50}})
    context = RuleContext(event={"value": 100}, state={})

    result = rule.evaluate(context)

    assert result.triggered is True
    assert "100" in result.reason
    assert "50" in result.reason
    assert result.new_state == {"last_value": 100}


def test_mock_rule_evaluate_not_triggered():
    """测试模拟规则未触发"""
    rule = MockRule("test_rule", {"params": {"threshold": 50}})
    context = RuleContext(event={"value": 30}, state={})

    result = rule.evaluate(context)

    assert result.triggered is False
    assert result.reason == "未超过阈值"
    assert result.new_state is None


def test_rule_repr():
    """测试规则字符串表示"""
    rule = MockRule("test_rule", {"enabled": True, "priority": 100})
    repr_str = repr(rule)

    assert "MockRule" in repr_str
    assert "test_rule" in repr_str
    assert "100" in repr_str
    assert "True" in repr_str
