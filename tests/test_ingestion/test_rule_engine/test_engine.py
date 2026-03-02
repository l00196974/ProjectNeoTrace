"""
测试规则引擎
"""

import pytest
from src.ingestion.rule_engine.base import BaseRule, RuleContext, RuleResult
from src.ingestion.rule_engine.engine import RuleEngine


class AlwaysTriggerRule(BaseRule):
    """总是触发的规则"""

    def evaluate(self, context: RuleContext) -> RuleResult:
        return RuleResult(
            triggered=True,
            reason=f"规则 {self.rule_id} 触发",
            new_state={"triggered_by": self.rule_id}
        )


class NeverTriggerRule(BaseRule):
    """从不触发的规则"""

    def evaluate(self, context: RuleContext) -> RuleResult:
        return RuleResult(triggered=False, reason="未触发")


class ThresholdRule(BaseRule):
    """阈值规则"""

    def evaluate(self, context: RuleContext) -> RuleResult:
        threshold = self.params.get("threshold", 10)
        value = context.event.get("value", 0)

        if value > threshold:
            return RuleResult(
                triggered=True,
                reason=f"值 {value} 超过阈值 {threshold}"
            )
        return RuleResult(triggered=False, reason="未超过阈值")


class ErrorRule(BaseRule):
    """会抛出异常的规则"""

    def evaluate(self, context: RuleContext) -> RuleResult:
        raise ValueError("规则执行错误")


def test_engine_initialization():
    """测试引擎初始化"""
    rules = [
        AlwaysTriggerRule("rule1", {"priority": 100}),
        NeverTriggerRule("rule2", {"priority": 50}),
    ]

    engine = RuleEngine(rules, execution_mode="chain")

    assert len(engine.rules) == 2
    assert engine.execution_mode == "chain"
    assert engine.rules[0].priority == 100
    assert engine.rules[1].priority == 50


def test_engine_sorts_by_priority():
    """测试引擎按优先级排序"""
    rules = [
        AlwaysTriggerRule("rule1", {"priority": 50}),
        AlwaysTriggerRule("rule2", {"priority": 100}),
        AlwaysTriggerRule("rule3", {"priority": 75}),
    ]

    engine = RuleEngine(rules)

    assert engine.rules[0].rule_id == "rule2"
    assert engine.rules[1].rule_id == "rule3"
    assert engine.rules[2].rule_id == "rule1"


def test_engine_invalid_execution_mode():
    """测试无效的执行模式"""
    with pytest.raises(ValueError, match="Invalid execution_mode"):
        RuleEngine([], execution_mode="invalid")


def test_engine_chain_mode_stops_at_first_trigger():
    """测试链式模式在首个触发时停止"""
    rules = [
        AlwaysTriggerRule("rule1", {"priority": 100}),
        AlwaysTriggerRule("rule2", {"priority": 50}),
    ]

    engine = RuleEngine(rules, execution_mode="chain")
    context = RuleContext(event={}, state={})

    triggered, reason, new_state = engine.evaluate(context)

    assert triggered is True
    assert "rule1" in reason
    assert new_state == {"triggered_by": "rule1"}


def test_engine_chain_mode_skips_disabled_rules():
    """测试链式模式跳过禁用的规则"""
    rules = [
        AlwaysTriggerRule("rule1", {"priority": 100, "enabled": False}),
        AlwaysTriggerRule("rule2", {"priority": 50, "enabled": True}),
    ]

    engine = RuleEngine(rules, execution_mode="chain")
    context = RuleContext(event={}, state={})

    triggered, reason, new_state = engine.evaluate(context)

    assert triggered is True
    assert "rule2" in reason
    assert new_state == {"triggered_by": "rule2"}


def test_engine_chain_mode_no_trigger():
    """测试链式模式无规则触发"""
    rules = [
        NeverTriggerRule("rule1", {"priority": 100}),
        NeverTriggerRule("rule2", {"priority": 50}),
    ]

    engine = RuleEngine(rules, execution_mode="chain")
    context = RuleContext(event={}, state={})

    triggered, reason, new_state = engine.evaluate(context)

    assert triggered is False
    assert reason == "无规则触发"
    assert new_state == {}


def test_engine_all_mode_collects_all_triggers():
    """测试全量模式收集所有触发"""
    rules = [
        AlwaysTriggerRule("rule1", {"priority": 100}),
        NeverTriggerRule("rule2", {"priority": 75}),
        AlwaysTriggerRule("rule3", {"priority": 50}),
    ]

    engine = RuleEngine(rules, execution_mode="all")
    context = RuleContext(event={}, state={})

    triggered, reason, new_state = engine.evaluate(context)

    assert triggered is True
    assert "rule1" in reason
    assert "rule3" in reason
    assert "rule2" not in reason


def test_engine_all_mode_merges_states():
    """测试全量模式合并状态"""
    rules = [
        AlwaysTriggerRule("rule1", {"priority": 100}),
        AlwaysTriggerRule("rule2", {"priority": 50}),
    ]

    engine = RuleEngine(rules, execution_mode="all")
    context = RuleContext(event={}, state={})

    triggered, reason, new_state = engine.evaluate(context)

    assert triggered is True
    assert "triggered_by" in new_state


def test_engine_handles_rule_exceptions():
    """测试引擎处理规则异常"""
    rules = [
        ErrorRule("error_rule", {"priority": 100}),
        AlwaysTriggerRule("good_rule", {"priority": 50}),
    ]

    engine = RuleEngine(rules, execution_mode="chain")
    context = RuleContext(event={}, state={})

    triggered, reason, new_state = engine.evaluate(context)

    assert triggered is True
    assert "good_rule" in reason


def test_engine_add_rule():
    """测试动态添加规则"""
    engine = RuleEngine([])
    new_rule = AlwaysTriggerRule("new_rule", {"priority": 100})

    engine.add_rule(new_rule)

    assert len(engine.rules) == 1
    assert engine.rules[0].rule_id == "new_rule"


def test_engine_remove_rule():
    """测试移除规则"""
    rules = [
        AlwaysTriggerRule("rule1", {"priority": 100}),
        AlwaysTriggerRule("rule2", {"priority": 50}),
    ]
    engine = RuleEngine(rules)

    engine.remove_rule("rule1")

    assert len(engine.rules) == 1
    assert engine.rules[0].rule_id == "rule2"


def test_engine_enable_rule():
    """测试启用规则"""
    rule = AlwaysTriggerRule("rule1", {"priority": 100, "enabled": False})
    engine = RuleEngine([rule])

    engine.enable_rule("rule1")

    assert engine.rules[0].enabled is True


def test_engine_disable_rule():
    """测试禁用规则"""
    rule = AlwaysTriggerRule("rule1", {"priority": 100, "enabled": True})
    engine = RuleEngine([rule])

    engine.disable_rule("rule1")

    assert engine.rules[0].enabled is False


def test_engine_get_rule():
    """测试获取规则"""
    rule = AlwaysTriggerRule("rule1", {"priority": 100})
    engine = RuleEngine([rule])

    found_rule = engine.get_rule("rule1")

    assert found_rule is not None
    assert found_rule.rule_id == "rule1"


def test_engine_get_nonexistent_rule():
    """测试获取不存在的规则"""
    engine = RuleEngine([])

    found_rule = engine.get_rule("nonexistent")

    assert found_rule is None


def test_engine_list_rules():
    """测试列出所有规则"""
    rules = [
        AlwaysTriggerRule("rule1", {"priority": 100, "enabled": True}),
        NeverTriggerRule("rule2", {"priority": 50, "enabled": False}),
    ]
    engine = RuleEngine(rules)

    rule_list = engine.list_rules()

    assert len(rule_list) == 2
    assert rule_list[0]["rule_id"] == "rule1"
    assert rule_list[0]["type"] == "AlwaysTriggerRule"
    assert rule_list[0]["enabled"] is True
    assert rule_list[0]["priority"] == 100
