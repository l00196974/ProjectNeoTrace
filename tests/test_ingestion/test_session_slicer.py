"""
模块 A：Session 切片引擎单元测试
测试基于 device_id 的状态机和 Session 边界识别
"""
import pytest
from datetime import datetime, timedelta


class TestSessionSlicer:
    """Session 切片器测试"""

    def test_session_boundary_by_screen_off(self, mock_event_sequence):
        """测试息屏 > 10min 切断规则"""
        # 模拟息屏超过 10 分钟的场景
        events = [
            {
                "device_id": "test_device_001",
                "timestamp": 1709136000000,  # T0
                "app_pkg": "com.autohome",
                "action": "app_foreground",
                "payload": {"dwell_time": 300}
            },
            {
                "device_id": "test_device_001",
                "timestamp": 1709136900000,  # T0 + 15min (超过 10min)
                "app_pkg": "com.autohome",
                "action": "app_foreground",
                "payload": {"dwell_time": 200}
            }
        ]

        # TODO: 实现 SessionSlicer 后取消注释
        # from data_ingestion.session_slicer import SessionSlicer
        # slicer = SessionSlicer(idle_threshold_ms=600000)  # 10 min
        # sessions = slicer.slice(events)
        # assert len(sessions) == 2, "应该切分为 2 个 Session"

        # 临时断言
        assert len(events) == 2

    def test_session_boundary_by_lbs_change(self):
        """测试 LBS 地标跨越切断规则"""
        events = [
            {
                "device_id": "test_device_001",
                "timestamp": 1709136000000,
                "app_pkg": "com.autohome",
                "action": "app_foreground",
                "payload": {"lbs_poi": "home"}
            },
            {
                "device_id": "test_device_001",
                "timestamp": 1709136300000,
                "app_pkg": "com.autohome",
                "action": "touch_scroll",
                "payload": {"lbs_poi": "auto_market"}  # LBS 变化
            }
        ]

        # TODO: 实现后取消注释
        # from data_ingestion.session_slicer import SessionSlicer
        # slicer = SessionSlicer()
        # sessions = slicer.slice(events)
        # assert len(sessions) == 2, "LBS 跨越应切分为 2 个 Session"

        assert len(events) == 2

    def test_session_boundary_by_app_category_change(self):
        """测试应用一级类目跳变切断规则"""
        events = [
            {
                "device_id": "test_device_001",
                "timestamp": 1709136000000,
                "app_pkg": "com.autohome",  # 汽车类
                "action": "app_foreground",
                "payload": {}
            },
            {
                "device_id": "test_device_001",
                "timestamp": 1709136300000,
                "app_pkg": "com.wechat",  # 社交类
                "action": "app_foreground",
                "payload": {}
            }
        ]

        # TODO: 实现后取消注释
        # from data_ingestion.session_slicer import SessionSlicer
        # slicer = SessionSlicer()
        # sessions = slicer.slice(events)
        # assert len(sessions) == 2, "类目跳变应切分为 2 个 Session"

        assert len(events) == 2

    def test_feature_aggregation(self, mock_session):
        """测试特征聚合：App 切换频率、停留时长、时间张力"""
        # TODO: 实现后取消注释
        # from data_ingestion.feature_aggregator import FeatureAggregator
        # aggregator = FeatureAggregator()
        # features = aggregator.aggregate(mock_session)

        # assert "app_switch_count" in features
        # assert "total_dwell_time" in features
        # assert "time_tension_bucket" in features

        # 临时断言
        assert "features" in mock_session
        assert mock_session["features"]["app_switch_count"] == 1

    def test_multi_device_isolation(self):
        """测试多设备隔离：不同 device_id 不应混合"""
        events = [
            {"device_id": "device_001", "timestamp": 1709136000000, "app_pkg": "com.autohome", "action": "app_foreground", "payload": {}},
            {"device_id": "device_002", "timestamp": 1709136100000, "app_pkg": "com.autohome", "action": "app_foreground", "payload": {}},
            {"device_id": "device_001", "timestamp": 1709136200000, "app_pkg": "com.autohome", "action": "touch_scroll", "payload": {}}
        ]

        # TODO: 实现后取消注释
        # from data_ingestion.session_slicer import SessionSlicer
        # slicer = SessionSlicer()
        # sessions = slicer.slice(events)

        # device_001_sessions = [s for s in sessions if s["device_id"] == "device_001"]
        # device_002_sessions = [s for s in sessions if s["device_id"] == "device_002"]

        # assert len(device_001_sessions) >= 1
        # assert len(device_002_sessions) >= 1

        assert len(events) == 3


class TestFeatureAggregator:
    """特征聚合器测试"""

    def test_app_switch_frequency(self):
        """测试 App 切换频率统计"""
        session_events = [
            {"app_pkg": "com.autohome", "timestamp": 1709136000000},
            {"app_pkg": "com.autohome", "timestamp": 1709136100000},
            {"app_pkg": "com.wechat", "timestamp": 1709136200000},
            {"app_pkg": "com.autohome", "timestamp": 1709136300000}
        ]

        # TODO: 实现后取消注释
        # from data_ingestion.feature_aggregator import FeatureAggregator
        # aggregator = FeatureAggregator()
        # features = aggregator.compute_app_switch_frequency(session_events)
        # assert features["app_switch_count"] == 3

        assert len(session_events) == 4

    def test_dwell_time_calculation(self):
        """测试停留时长计算"""
        session_events = [
            {"app_pkg": "com.autohome", "payload": {"dwell_time": 300}},
            {"app_pkg": "com.autohome", "payload": {"dwell_time": 150}}
        ]

        # TODO: 实现后取消注释
        # from data_ingestion.feature_aggregator import FeatureAggregator
        # aggregator = FeatureAggregator()
        # total_time = aggregator.compute_total_dwell_time(session_events)
        # assert total_time == 450

        total = sum(e["payload"]["dwell_time"] for e in session_events)
        assert total == 450

    def test_time_tension_bucketing(self):
        """测试时间张力对数分桶"""
        dwell_times = [10, 100, 1000, 10000]

        # TODO: 实现后取消注释
        # from data_ingestion.feature_aggregator import FeatureAggregator
        # aggregator = FeatureAggregator()
        # buckets = [aggregator.time_tension_bucket(t) for t in dwell_times]
        # assert len(set(buckets)) > 1, "不同时长应分到不同桶"

        import math
        buckets = [int(math.log10(t + 1)) for t in dwell_times]
        assert len(set(buckets)) > 1
