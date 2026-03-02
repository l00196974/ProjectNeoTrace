"""Log-to-Text 转换执行引擎

管理规则集合并按优先级执行转换
"""

import logging
from typing import List, Dict
from .base import BaseConversionRule, ConversionContext, ConversionResult

logger = logging.getLogger(__name__)


class LogToTextEngine:
    """Log-to-Text 转换引擎

    管理规则集合，按优先级执行转换
    """

    def __init__(
        self,
        rules: List[BaseConversionRule] = None,
        mode: str = "first_match"
    ):
        """初始化引擎

        Args:
            rules: 规则列表
            mode: 执行模式 ("first_match" 或 "all")
        """
        self.rules = rules or []
        self.mode = mode
        self._sort_rules()

    def _sort_rules(self):
        """按优先级排序规则（降序）"""
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def add_rule(self, rule: BaseConversionRule):
        """添加规则

        Args:
            rule: 规则实例
        """
        self.rules.append(rule)
        self._sort_rules()

    def convert(self, session: Dict) -> ConversionResult:
        """转换 session 为文本

        Args:
            session: Session 数据字典

        Returns:
            转换结果
        """
        context = ConversionContext(session=session)

        if self.mode == "first_match":
            return self._convert_first_match(context)
        elif self.mode == "all":
            results = self._convert_all(context)
            # 对于 "all" 模式，返回优先级最高的成功结果
            if results:
                return results[0]
            else:
                return ConversionResult(
                    success=False,
                    text="",
                    rule_id="none",
                    priority=0,
                    metadata={"error": "No rule matched"}
                )
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    def _convert_first_match(self, context: ConversionContext) -> ConversionResult:
        """第一个匹配模式

        按优先级顺序执行规则，返回第一个成功的结果

        Args:
            context: 转换上下文

        Returns:
            转换结果
        """
        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                if rule.match(context):
                    result = rule.convert(context)
                    if result.success:
                        logger.debug(f"Rule {rule.rule_id} matched and converted successfully")
                        return result
                    else:
                        logger.warning(f"Rule {rule.rule_id} matched but conversion failed")
            except Exception as e:
                logger.warning(f"Rule {rule.rule_id} failed: {e}")
                continue

        # 如果没有规则匹配，返回失败结果
        logger.error("No rule matched for session")
        return ConversionResult(
            success=False,
            text="",
            rule_id="none",
            priority=0,
            metadata={"error": "No rule matched"}
        )

    def _convert_all(self, context: ConversionContext) -> List[ConversionResult]:
        """所有匹配模式

        执行所有匹配的规则，返回所有成功的结果

        Args:
            context: 转换上下文

        Returns:
            转换结果列表
        """
        results = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                if rule.match(context):
                    result = rule.convert(context)
                    if result.success:
                        results.append(result)
                        logger.debug(f"Rule {rule.rule_id} matched and converted successfully")
            except Exception as e:
                logger.warning(f"Rule {rule.rule_id} failed: {e}")
                continue

        return results

    def get_rule_summary(self) -> Dict:
        """获取规则摘要

        Returns:
            规则摘要信息
        """
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "disabled_rules": sum(1 for r in self.rules if not r.enabled),
            "mode": self.mode,
            "rules": [
                {
                    "id": r.rule_id,
                    "type": r.__class__.__name__,
                    "priority": r.priority,
                    "enabled": r.enabled
                }
                for r in self.rules
            ]
        }
