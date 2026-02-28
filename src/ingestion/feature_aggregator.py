"""特征聚合模块

从 Session 事件序列中提取特征。

特征列表：
- app_switch_freq: App 切换次数
- config_page_dwell: 配置页停留时长（秒）
- finance_page_dwell: 金融页停留时长（秒）
- time_tension_bucket: 时间张力（log 分桶）
- lbs_poi_list: POI 列表
- app_pkg_list: App 列表
"""

import math
from typing import Dict, List
from collections import Counter


class FeatureAggregator:
    """特征聚合器"""

    def __init__(self):
        pass

    def aggregate(self, events: List[Dict]) -> Dict:
        """
        聚合 Session 特征

        Args:
            events: Session 事件列表

        Returns:
            特征字典
        """
        if not events:
            return self._empty_features()

        # 基础信息
        device_id = events[0]["device_id"]
        start_time = events[0]["timestamp"]
        end_time = events[-1]["timestamp"]
        session_duration = end_time - start_time

        # 提取特征
        app_switch_freq = self._compute_app_switch_freq(events)
        config_page_dwell = self._compute_page_dwell(events, "config_page")
        finance_page_dwell = self._compute_page_dwell(events, "finance_page")
        time_tension_bucket = self._compute_time_tension(session_duration)
        lbs_poi_list = self._extract_poi_list(events)
        app_pkg_list = self._extract_app_list(events)

        return {
            "device_id": device_id,
            "start_time": start_time,
            "end_time": end_time,
            "session_duration": session_duration,
            "app_switch_freq": app_switch_freq,
            "config_page_dwell": config_page_dwell,
            "finance_page_dwell": finance_page_dwell,
            "time_tension_bucket": time_tension_bucket,
            "lbs_poi_list": lbs_poi_list,
            "app_pkg_list": app_pkg_list,
            "event_count": len(events),
        }

    def _empty_features(self) -> Dict:
        """返回空特征"""
        return {
            "device_id": "",
            "start_time": 0,
            "end_time": 0,
            "session_duration": 0,
            "app_switch_freq": 0,
            "config_page_dwell": 0,
            "finance_page_dwell": 0,
            "time_tension_bucket": 0,
            "lbs_poi_list": [],
            "app_pkg_list": [],
            "event_count": 0,
        }

    def _compute_app_switch_freq(self, events: List[Dict]) -> int:
        """
        计算 App 切换次数

        Args:
            events: 事件列表

        Returns:
            切换次数
        """
        switch_count = 0
        last_app = None

        for event in events:
            current_app = event.get("app_pkg")
            if current_app and last_app and current_app != last_app:
                switch_count += 1
            last_app = current_app

        return switch_count

    def _compute_page_dwell(self, events: List[Dict], page_type: str) -> int:
        """
        计算特定页面停留时长

        Args:
            events: 事件列表
            page_type: 页面类型（config_page, finance_page）

        Returns:
            停留时长（秒）
        """
        total_dwell = 0

        for event in events:
            payload = event.get("payload", {})
            if payload.get("page_type") == page_type:
                dwell_time = payload.get("dwell_time", 0)
                total_dwell += dwell_time

        return total_dwell

    def _compute_time_tension(self, duration: int) -> int:
        """
        计算时间张力（log 分桶）

        时间张力反映 Session 的时间跨度：
        - Bucket 0: 0-1 分钟
        - Bucket 1: 1-5 分钟
        - Bucket 2: 5-15 分钟
        - Bucket 3: 15-30 分钟
        - Bucket 4: 30-60 分钟
        - Bucket 5: 60+ 分钟

        Args:
            duration: Session 时长（秒）

        Returns:
            时间张力分桶（0-5）
        """
        if duration <= 0:
            return 0

        minutes = duration / 60

        if minutes <= 1:
            return 0
        elif minutes <= 5:
            return 1
        elif minutes <= 15:
            return 2
        elif minutes <= 30:
            return 3
        elif minutes <= 60:
            return 4
        else:
            return 5

    def _extract_poi_list(self, events: List[Dict]) -> List[str]:
        """
        提取 POI 列表（去重，保持顺序）

        Args:
            events: 事件列表

        Returns:
            POI 列表
        """
        poi_list = []
        seen = set()

        for event in events:
            payload = event.get("payload", {})
            poi = payload.get("lbs_poi")
            if poi and poi not in seen:
                poi_list.append(poi)
                seen.add(poi)

        return poi_list

    def _extract_app_list(self, events: List[Dict]) -> List[str]:
        """
        提取 App 列表（去重，保持顺序）

        Args:
            events: 事件列表

        Returns:
            App 列表
        """
        app_list = []
        seen = set()

        for event in events:
            app_pkg = event.get("app_pkg")
            if app_pkg and app_pkg not in seen:
                app_list.append(app_pkg)
                seen.add(app_pkg)

        return app_list

    def compute_session_features_vector(self, features: Dict) -> List[float]:
        """
        将 Session 特征转换为向量（用于后续模型输入）

        Args:
            features: 特征字典

        Returns:
            特征向量（256-dim）
        """
        # 这里先返回一个简化版本，后续会扩展
        vector = [
            float(features["app_switch_freq"]),
            float(features["config_page_dwell"]) / 60.0,  # 归一化到分钟
            float(features["finance_page_dwell"]) / 60.0,
            float(features["time_tension_bucket"]),
            float(features["session_duration"]) / 3600.0,  # 归一化到小时
            float(features["event_count"]) / 100.0,  # 归一化
        ]

        # 填充到 256 维（后续会用更复杂的特征）
        while len(vector) < 256:
            vector.append(0.0)

        return vector[:256]
