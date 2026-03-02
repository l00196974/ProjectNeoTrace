"""
规则引擎核心实现
"""

import logging
from typing import List, Tuple, Dict, Any

from .base import BaseRule, RuleContext, RuleResult

logger = logging.getLogger(__name__)


class RuleEngine:
    """规则引擎 - 按优先级执行规则"""

    def __init__(self, rules: List[BaseRule], execution_mode: str = "chain"):
        """
        初始化规则引擎

        Args:
            rules: 规则列表
            execution_mode: 执行模式
                - "chain": 链式执行，首个触发规则即停止
                - "all": 执行所有规则，收集所有触发结果
        """
        self.rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        self.execution_mode = execution_mode
        self._validate_execution_mode()

    def _validate_execution_mode(self):
        """验证执行模式"""
        valid_modes = ["chain", "all"]
        if self.execution_mode not in valid_modes:
            raise ValueError(f"Invalid execution_mode: {self.execution_mode}. Must be one of {valid_modes}")

    def evaluate(self, context: RuleContext) -> Tuple[bool, str, Dict[str, Any]]:
        """
        评估规则，返回是否触发、原因和新状态

        Args:
            context: 规则执行上下文

        Returns:
            Tuple[bool, str, Dict]: (是否触发, 触发原因, 新状态)
        """
        triggered_results = []

        for rule in self.rules:
            if not rule.enabled:
                logger.debug(f"跳过禁用规则: {rule.rule_id}")
                continue

            try:
                result = rule.evaluate(context)

                if result.triggered:
                    logger.debug(f"规则触发: {rule.rule_id} - {result.reason}")
                    triggered_results.append((rule, result))

                    if self.execution_mode == "chain":
                        return True, result.reason, result.new_state or {}
                else:
                    logger.debug(f"规则未触发: {rule.rule_id}")

            except Exception as e:
                logger.error(f"规则执行异常: {rule.rule_id} - {str(e)}", exc_info=True)
                continue

        if self.execution_mode == "all" and triggered_results:
            reasons = [f"{r.rule_id}: {res.reason}" for r, res in triggered_results]
            combined_reason = "; ".join(reasons)
            combined_state = {}
            for _, res in triggered_results:
                if res.new_state:
                    combined_state.update(res.new_state)
            return True, combined_reason, combined_state

        return False, "无规则触发", {}

    def add_rule(self, rule: BaseRule):
        """动态添加规则"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"添加规则: {rule.rule_id}")

    def remove_rule(self, rule_id: str):
        """移除规则"""
        self.rules = [r for r in self.rules if r.rule_id != rule_id]
        logger.info(f"移除规则: {rule_id}")

    def enable_rule(self, rule_id: str):
        """启用规则"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                logger.info(f"启用规则: {rule_id}")
                return
        logger.warning(f"规则不存在: {rule_id}")

    def disable_rule(self, rule_id: str):
        """禁用规则"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                logger.info(f"禁用规则: {rule_id}")
                return
        logger.warning(f"规则不存在: {rule_id}")

    def get_rule(self, rule_id: str) -> BaseRule:
        """获取规则"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def list_rules(self) -> List[Dict[str, Any]]:
        """列出所有规则"""
        return [
            {
                "rule_id": r.rule_id,
                "type": r.__class__.__name__,
                "enabled": r.enabled,
                "priority": r.priority,
            }
            for r in self.rules
        ]
