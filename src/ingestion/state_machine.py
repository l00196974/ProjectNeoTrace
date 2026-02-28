"""状态机实现 - 识别 Session 边界

状态机用于识别用户行为序列中的 Session 边界。

切片规则（按优先级）：
1. 息屏 > 10min → 新 Session
2. LBS 地标跨越 → 新 Session
3. 应用类目跳变 → 新 Session
"""

from typing import Dict, Optional
from enum import Enum


class SessionState(Enum):
    """Session 状态"""

    ACTIVE = "active"  # 活跃状态
    IDLE = "idle"  # 空闲状态（息屏）
    ENDED = "ended"  # Session 结束


# 应用类目映射
APP_CATEGORY_MAP = {
    # 汽车类
    "com.autohome": "automotive",
    "com.yiche": "automotive",
    "com.bitauto": "automotive",
    "com.xcar": "automotive",
    "com.pcauto": "automotive",
    # 社交类
    "com.tencent.mm": "social",
    "com.tencent.mobileqq": "social",
    "com.sina.weibo": "social",
    "com.tencent.wework": "social",
    # 外卖类
    "com.sankuai.meituan": "food_delivery",
    "me.ele": "food_delivery",
    # 电商类
    "com.taobao.taobao": "shopping",
    "com.jingdong.app.mall": "shopping",
    "com.xunmeng.pinduoduo": "shopping",
    # 娱乐类
    "com.ss.android.ugc.aweme": "entertainment",
    "com.tencent.qqlive": "entertainment",
    "com.youku.phone": "entertainment",
    # 金融类
    "com.tencent.wemoney.app": "finance",
    "com.eg.android.AlipayGphone": "finance",
    "com.chinamworld.main": "finance",
}

# POI 类型层级（用于判断地标跨越）
POI_HIERARCHY = {
    "home": 1,
    "office": 1,
    "auto_market": 2,
    "4s_store": 2,
    "shopping_mall": 1,
    "restaurant": 1,
    "gas_station": 1,
}


class SessionStateMachine:
    """Session 状态机"""

    def __init__(
        self,
        screen_off_threshold: int = 600,  # 息屏阈值（秒），默认 10 分钟
    ):
        """
        初始化状态机

        Args:
            screen_off_threshold: 息屏阈值（秒）
        """
        self.screen_off_threshold = screen_off_threshold
        self.reset()

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

        timestamp = event["timestamp"]
        action = event["action"]
        payload = event.get("payload", {})
        app_pkg = event.get("app_pkg", "")

        # 规则 1：息屏 > 10min → 新 Session
        if self.screen_off_time is not None:
            idle_duration = timestamp - self.screen_off_time
            if idle_duration > self.screen_off_threshold:
                self.reset()
                self._update_state(event)
                return True

        # 规则 2：LBS 地标跨越 → 新 Session
        current_poi = payload.get("lbs_poi")
        if current_poi and self.last_poi:
            if self._is_poi_crossing(self.last_poi, current_poi):
                self.reset()
                self._update_state(event)
                return True

        # 规则 3：应用类目跳变 → 新 Session
        current_category = self._get_app_category(app_pkg)
        if current_category and self.last_category:
            if current_category != self.last_category:
                self.reset()
                self._update_state(event)
                return True

        # 更新状态
        self._update_state(event)
        return False

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
        current_category = self._get_app_category(app_pkg)
        if current_category:
            self.last_category = current_category

        # 更新息屏状态
        if action == "screen_off":
            self.screen_off_time = timestamp
            self.state = SessionState.IDLE
        elif action == "screen_on":
            self.screen_off_time = None
            self.state = SessionState.ACTIVE

    def _is_poi_crossing(self, poi1: str, poi2: str) -> bool:
        """判断是否为地标跨越。

        地标跨越定义：从一个层级跳到另一个层级
        例如：home → auto_market（层级 1 → 层级 2）

        Args:
            poi1: POI 1
            poi2: POI 2

        Returns:
            是否为地标跨越
        """
        if poi1 == poi2:
            return False

        # 如果任一 POI 不在字典中，不视为跨越
        if poi1 not in POI_HIERARCHY or poi2 not in POI_HIERARCHY:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"未知 POI: {poi1} 或 {poi2}")
            return False

        level1 = POI_HIERARCHY[poi1]
        level2 = POI_HIERARCHY[poi2]

        # 不同层级视为跨越
        return level1 != level2

    def _get_app_category(self, app_pkg: str) -> Optional[str]:
        """
        获取应用类目

        Args:
            app_pkg: 应用包名

        Returns:
            应用类目
        """
        return APP_CATEGORY_MAP.get(app_pkg)
