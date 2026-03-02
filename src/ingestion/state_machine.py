"""状态机实现 - 识别 Session 边界

状态机用于识别用户行为序列中的 Session 边界。
使用规则引擎实现可扩展的切片规则管理。

切片规则（按优先级）：
1. 息屏 > 10min → 新 Session
2. LBS 地标跨越 → 新 Session
3. 应用类目跳变 → 新 Session
"""

import logging
from typing import Dict, Optional
from enum import Enum

from .rule_engine import RuleEngine, RuleRegistry, RuleContext
from .rule_engine.config import RuleConfig
from .rule_engine.rules import ScreenOffRule, LBSCrossingRule, AppCategoryRule

# 确保规则已注册
RuleRegistry.register("screen_off", ScreenOffRule)
RuleRegistry.register("lbs_crossing", LBSCrossingRule)
RuleRegistry.register("app_category_change", AppCategoryRule)

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Session 状态"""

    ACTIVE = "active"  # 活跃状态
    IDLE = "idle"  # 空闲状态（息屏）
    ENDED = "ended"  # Session 结束


class SessionStateMachine:
    """Session 状态机 - 使用规则引擎"""

    def __init__(
        self,
        config_path: Optional[str] = None,
        screen_off_threshold: Optional[int] = None,  # 向后兼容参数
    ):
        """
        初始化状态机

        Args:
            config_path: 规则配置文件路径（可选）
            screen_off_threshold: 息屏阈值（秒），用于向后兼容
        """
        # 加载配置
        if config_path:
            config = RuleConfig.load_from_yaml(config_path)
        else:
            config = RuleConfig.get_default_config()

            # 向后兼容：如果提供了 screen_off_threshold，覆盖默认配置
            if screen_off_threshold is not None:
                for rule in config["rules"]:
                    if rule["type"] == "screen_off":
                        rule["params"]["threshold_seconds"] = screen_off_threshold

        # 构建规则引擎
        rules = [
            RuleRegistry.create_rule(r["id"], r)
            for r in config["rules"]
        ]
        execution_mode = config.get("execution", {}).get("mode", "chain")
        self.engine = RuleEngine(rules, execution_mode)

        # 初始化状态
        self.reset()

        logger.info(f"状态机初始化完成，加载 {len(rules)} 个规则")

    def reset(self):
        """重置状态机"""
        self.state = SessionState.ACTIVE
        self.last_timestamp = None
        self.last_poi = None
        self.last_category = None
        self.screen_off_time = None

    def should_start_new_session(self, event: Dict) -> bool:
        """
        判断是否应该开始新的 Session

        Args:
            event: 事件数据

        Returns:
            是否开始新 Session
        """
        # 第一个事件，不需要新 Session
        if self.last_timestamp is None:
            self._update_state(event)
            return False

        # 构建规则上下文
        context = RuleContext(
            event=event,
            state=self._get_state_dict()
        )

        # 使用规则引擎评估
        triggered, reason, new_state = self.engine.evaluate(context)

        if triggered:
            logger.info(f"触发 Session 切割: {reason}")
            self.reset()
            self._update_state(event)
            return True

        # 更新状态
        self._update_state(event)
        return False

    def _get_state_dict(self) -> Dict:
        """获取状态字典"""
        return {
            "state": self.state.value,
            "last_timestamp": self.last_timestamp,
            "last_poi": self.last_poi,
            "last_category": self.last_category,
            "screen_off_time": self.screen_off_time,
        }

    def _update_state(self, event: Dict):
        """更新状态机内部状态"""
        timestamp = event["timestamp"]
        action = event["action"]
        payload = event.get("payload", {})
        app_pkg = event.get("app_pkg", "")

        self.last_timestamp = timestamp

        # 更新 POI
        current_poi = payload.get("lbs_poi")
        if current_poi:
            self.last_poi = current_poi

        # 更新应用类目
        # 从规则引擎获取类目映射
        app_category_rule = self.engine.get_rule("app_category_rule")
        if app_category_rule:
            category_map = app_category_rule.params.get("category_map", {})
            current_category = category_map.get(app_pkg)
            if current_category:
                self.last_category = current_category

        # 更新息屏状态
        if action == "screen_off":
            self.screen_off_time = timestamp
            self.state = SessionState.IDLE
        elif action == "screen_on":
            self.screen_off_time = None
            self.state = SessionState.ACTIVE
