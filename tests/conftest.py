"""
Pytest 配置文件
提供全局 fixtures 和测试配置
"""
import pytest
import sys
from pathlib import Path

# 添加 src 目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.fixture
def mock_event_log():
    """模拟单条事件日志"""
    return {
        "device_id": "test_device_001",
        "timestamp": 1709136000000,
        "app_pkg": "com.autohome",
        "action": "app_foreground",
        "payload": {
            "dwell_time": 450,
            "lbs_poi": "auto_market"
        }
    }


@pytest.fixture
def mock_event_sequence():
    """模拟事件序列"""
    return [
        {
            "device_id": "test_device_001",
            "timestamp": 1709136000000,
            "app_pkg": "com.autohome",
            "action": "app_foreground",
            "payload": {"dwell_time": 300}
        },
        {
            "device_id": "test_device_001",
            "timestamp": 1709136300000,
            "app_pkg": "com.autohome",
            "action": "touch_scroll",
            "payload": {"dwell_time": 150}
        },
        {
            "device_id": "test_device_001",
            "timestamp": 1709137200000,
            "app_pkg": "com.wechat",
            "action": "app_foreground",
            "payload": {"dwell_time": 200}
        }
    ]


@pytest.fixture
def mock_session():
    """模拟 Session 切片"""
    return {
        "session_id": "session_001",
        "device_id": "test_device_001",
        "start_time": 1709136000000,
        "end_time": 1709136450000,
        "events": [
            {
                "app_pkg": "com.autohome",
                "action": "app_foreground",
                "dwell_time": 450
            }
        ],
        "features": {
            "app_switch_count": 1,
            "total_dwell_time": 450,
            "auto_related_time": 450
        }
    }


@pytest.fixture
def mock_training_sample():
    """模拟训练样本"""
    import numpy as np
    return {
        "device_id": "test_device_001",
        "combined_vector": np.random.randn(256).astype(np.float32),
        "proxy_label": 3
    }
