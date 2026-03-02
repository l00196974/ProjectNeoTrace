"""
内置 Session 切片规则实现
"""

import logging
from typing import Optional

from .base import BaseRule, RuleContext, RuleResult

logger = logging.getLogger(__name__)


class ScreenOffRule(BaseRule):
    """息屏超时规则

    当用户息屏时间超过阈值时，触发新 Session
    """

    def evaluate(self, context: RuleContext) -> RuleResult:
        threshold = self.params.get("threshold_seconds", 600)

        event = context.event
        state = context.state

        timestamp = event.get("timestamp")
        screen_off_time = state.get("screen_off_time")

        # 如果没有息屏时间记录，不触发
        if screen_off_time is None:
            return RuleResult(triggered=False, reason="无息屏记录")

        # 计算息屏时长
        idle_duration = timestamp - screen_off_time

        if idle_duration > threshold:
            return RuleResult(
                triggered=True,
                reason=f"息屏时长 {idle_duration}s 超过阈值 {threshold}s"
            )

        return RuleResult(triggered=False, reason=f"息屏时长 {idle_duration}s 未超过阈值")


class LBSCrossingRule(BaseRule):
    """LBS 地标跨越规则

    当用户从一个地标层级跳转到另一个层级时，触发新 Session
    例如：home (层级1) -> auto_market (层级2)
    """

    def evaluate(self, context: RuleContext) -> RuleResult:
        poi_hierarchy = self.params.get("poi_hierarchy", {})

        event = context.event
        state = context.state

        payload = event.get("payload", {})
        current_poi = payload.get("lbs_poi")
        last_poi = state.get("last_poi")

        # 如果没有当前 POI 或上一个 POI，不触发
        if not current_poi or not last_poi:
            return RuleResult(triggered=False, reason="POI 信息不完整")

        # 如果 POI 相同，不触发
        if current_poi == last_poi:
            return RuleResult(triggered=False, reason="POI 未变化")

        # 检查 POI 是否在层级字典中
        if current_poi not in poi_hierarchy or last_poi not in poi_hierarchy:
            logger.debug(f"未知 POI: {current_poi} 或 {last_poi}")
            return RuleResult(triggered=False, reason=f"未知 POI: {current_poi} 或 {last_poi}")

        # 获取层级
        current_level = poi_hierarchy[current_poi]
        last_level = poi_hierarchy[last_poi]

        # 不同层级视为跨越
        if current_level != last_level:
            return RuleResult(
                triggered=True,
                reason=f"POI 跨越: {last_poi}(层级{last_level}) -> {current_poi}(层级{current_level})"
            )

        return RuleResult(triggered=False, reason="POI 层级未变化")


class AppCategoryRule(BaseRule):
    """应用类目跳变规则

    当用户从一个应用类目切换到另一个类目时，触发新 Session
    例如：social -> automotive
    """

    def evaluate(self, context: RuleContext) -> RuleResult:
        category_map = self.params.get("category_map", {})

        event = context.event
        state = context.state

        app_pkg = event.get("app_pkg", "")
        last_category = state.get("last_category")

        # 获取当前应用类目
        current_category = category_map.get(app_pkg)

        # 如果没有当前类目或上一个类目，不触发
        if not current_category or not last_category:
            return RuleResult(triggered=False, reason="应用类目信息不完整")

        # 如果类目相同，不触发
        if current_category == last_category:
            return RuleResult(triggered=False, reason="应用类目未变化")

        # 类目不同，触发
        return RuleResult(
            triggered=True,
            reason=f"应用类目跳变: {last_category} -> {current_category}"
        )
