"""Teacher Model 标注模块测试

测试 Teacher 标注器的简化输出格式。
"""
import pytest
from unittest.mock import Mock, MagicMock
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.teacher_labeling import TeacherLabeler
from src.agent.llm_client import MockLLMClient


class TestTeacherLabelerOutputFormat:
    """测试 Teacher 标注器的输出格式"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.llm_client = MockLLMClient()
        self.teacher = TeacherLabeler(
            llm_client=self.llm_client,
            enable_traceability=False
        )

    def test_label_session_output_format(self):
        """测试 label_session 输出格式（简化版）"""
        session = {
            "session_id": "test_session_001",
            "device_id": "test_device_001",
            "app_pkg_list": ["com.autohome"],
            "lbs_poi_list": ["auto_market"],
            "config_page_dwell": 180,
            "finance_page_dwell": 60,
            "session_duration": 300,
        }

        result = self.teacher.label_session(session)

        # 验证输出格式
        assert "intent_probs" in result, "应包含 intent_probs"
        assert "primary_intent" in result, "应包含 primary_intent"
        assert "urgency_level" in result, "应包含 urgency_level"
        assert "confidence" in result, "应包含 confidence"
        assert "session_text" in result, "应包含 session_text"

        # 验证不包含旧格式字段
        assert "intent_vector" not in result, "不应包含 intent_vector（已重命名为 intent_probs）"
        assert "intent_embedding" not in result, "不应包含 intent_embedding（Teacher 不再生成）"
        assert "urgency_score" not in result, "不应包含 urgency_score（已改为 urgency_level）"

    def test_intent_probs_format(self):
        """测试 intent_probs 格式"""
        session = {
            "session_id": "test_session_002",
            "device_id": "test_device_002",
            "app_pkg_list": ["com.autohome"],
            "session_duration": 300,
        }

        result = self.teacher.label_session(session)

        # 验证 intent_probs 是 11 维列表
        assert isinstance(result["intent_probs"], list), "intent_probs 应该是列表"
        assert len(result["intent_probs"]) == 11, "intent_probs 应该是 11 维"
        assert all(isinstance(p, float) for p in result["intent_probs"]), "所有概率应该是浮点数"
        assert all(0 <= p <= 1 for p in result["intent_probs"]), "所有概率应该在 [0, 1] 范围内"

    def test_urgency_level_values(self):
        """测试 urgency_level 的有效值"""
        session = {
            "session_id": "test_session_003",
            "device_id": "test_device_003",
            "app_pkg_list": ["com.autohome"],
            "session_duration": 300,
        }

        result = self.teacher.label_session(session)

        # 验证 urgency_level 是有效值
        assert result["urgency_level"] in ["high", "medium", "low"], \
            f"urgency_level 应该是 high/medium/low 之一，实际值：{result['urgency_level']}"

    def test_confidence_range(self):
        """测试 confidence 的范围"""
        session = {
            "session_id": "test_session_004",
            "device_id": "test_device_004",
            "app_pkg_list": ["com.autohome"],
            "session_duration": 300,
        }

        result = self.teacher.label_session(session)

        # 验证 confidence 在 [0, 1] 范围内
        assert isinstance(result["confidence"], (int, float)), "confidence 应该是数值"
        assert 0 <= result["confidence"] <= 1, \
            f"confidence 应该在 [0, 1] 范围内，实际值：{result['confidence']}"

    def test_primary_intent_valid(self):
        """测试 primary_intent 是有效的意图名称"""
        from src.agent.intent_taxonomy import ALL_INTENTS

        session = {
            "session_id": "test_session_005",
            "device_id": "test_device_005",
            "app_pkg_list": ["com.autohome"],
            "session_duration": 300,
        }

        result = self.teacher.label_session(session)

        # 验证 primary_intent 是有效的意图名称
        assert result["primary_intent"] in ALL_INTENTS + ["unknown"], \
            f"primary_intent 应该是有效的意图名称，实际值：{result['primary_intent']}"


class TestTeacherLabelerUrgencyConversion:
    """测试紧急度转换逻辑"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.llm_client = MockLLMClient()
        self.teacher = TeacherLabeler(
            llm_client=self.llm_client,
            enable_traceability=False
        )

    def test_urgency_score_to_level_high(self):
        """测试 urgency_score 转换为 high"""
        # urgency_score >= 7 应该转换为 high
        assert self.teacher._convert_urgency_to_level(7) == "high"
        assert self.teacher._convert_urgency_to_level(8) == "high"
        assert self.teacher._convert_urgency_to_level(9) == "high"
        assert self.teacher._convert_urgency_to_level(10) == "high"

    def test_urgency_score_to_level_medium(self):
        """测试 urgency_score 转换为 medium"""
        # 4 <= urgency_score < 7 应该转换为 medium
        assert self.teacher._convert_urgency_to_level(4) == "medium"
        assert self.teacher._convert_urgency_to_level(5) == "medium"
        assert self.teacher._convert_urgency_to_level(6) == "medium"

    def test_urgency_score_to_level_low(self):
        """测试 urgency_score 转换为 low"""
        # urgency_score < 4 应该转换为 low
        assert self.teacher._convert_urgency_to_level(0) == "low"
        assert self.teacher._convert_urgency_to_level(1) == "low"
        assert self.teacher._convert_urgency_to_level(2) == "low"
        assert self.teacher._convert_urgency_to_level(3) == "low"


class TestTeacherLabelerDeviceLevel:
    """测试设备级别标注"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.llm_client = MockLLMClient()
        self.teacher = TeacherLabeler(
            llm_client=self.llm_client,
            enable_traceability=False
        )

    def test_label_device_output_format(self):
        """测试 label_device 输出格式（简化版）"""
        device_id = "test_device_001"
        sessions = [
            {
                "session_id": "session_001",
                "device_id": device_id,
                "app_pkg_list": ["com.autohome"],
                "session_duration": 300,
            },
            {
                "session_id": "session_002",
                "device_id": device_id,
                "app_pkg_list": ["com.yiche"],
                "session_duration": 200,
            }
        ]

        result = self.teacher.label_device(device_id, sessions)

        # 验证输出格式
        assert "device_id" in result
        assert "session_count" in result
        assert "total_duration" in result
        assert "intent_probs" in result, "应包含 intent_probs"
        assert "primary_intent" in result
        assert "secondary_intents" in result
        assert "urgency_level" in result, "应包含 urgency_level"
        assert "confidence" in result, "应包含 confidence"
        assert "device_summary" in result

        # 验证不包含旧格式字段
        assert "intent_vector" not in result, "不应包含 intent_vector"
        assert "intent_embedding" not in result, "不应包含 intent_embedding"
        assert "urgency_score" not in result, "不应包含 urgency_score"

    def test_label_device_intent_probs_format(self):
        """测试设备级别的 intent_probs 格式"""
        device_id = "test_device_002"
        sessions = [
            {
                "session_id": "session_001",
                "device_id": device_id,
                "app_pkg_list": ["com.autohome"],
                "session_duration": 300,
            }
        ]

        result = self.teacher.label_device(device_id, sessions)

        # 验证 intent_probs 格式
        assert isinstance(result["intent_probs"], list)
        assert len(result["intent_probs"]) == 11
        assert all(isinstance(p, float) for p in result["intent_probs"])

    def test_label_device_urgency_level(self):
        """测试设备级别的 urgency_level"""
        device_id = "test_device_003"
        sessions = [
            {
                "session_id": "session_001",
                "device_id": device_id,
                "app_pkg_list": ["com.autohome"],
                "session_duration": 300,
            }
        ]

        result = self.teacher.label_device(device_id, sessions)

        # 验证 urgency_level
        assert result["urgency_level"] in ["high", "medium", "low"]


class TestTeacherLabelerDefaultIntent:
    """测试默认意图"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.llm_client = MockLLMClient()
        self.teacher = TeacherLabeler(
            llm_client=self.llm_client,
            enable_traceability=False
        )

    def test_default_intent_format(self):
        """测试默认意图格式（简化版）"""
        default_intent = self.teacher._get_default_intent()

        # 验证默认意图格式
        assert "intent_probs" in default_intent, "应包含 intent_probs"
        assert "primary_intent" in default_intent
        assert "urgency_level" in default_intent, "应包含 urgency_level"
        assert "confidence" in default_intent, "应包含 confidence"

        # 验证不包含旧格式字段
        assert "intent_vector" not in default_intent
        assert "intent_embedding" not in default_intent
        assert "urgency_score" not in default_intent

        # 验证默认值
        assert len(default_intent["intent_probs"]) == 11
        assert all(p == 0.0 for p in default_intent["intent_probs"])
        assert default_intent["primary_intent"] == "unknown"
        assert default_intent["urgency_level"] == "low"
        assert default_intent["confidence"] == 0.0


class TestTeacherLabelerBatchProcessing:
    """测试批量处理"""

    def setup_method(self):
        """每个测试方法前的设置"""
        self.llm_client = MockLLMClient()
        self.teacher = TeacherLabeler(
            llm_client=self.llm_client,
            enable_traceability=False
        )

    def test_label_sessions_batch(self):
        """测试批量标注 sessions"""
        sessions = [
            {
                "session_id": f"session_{i:03d}",
                "device_id": "test_device_001",
                "app_pkg_list": ["com.autohome"],
                "session_duration": 300,
            }
            for i in range(5)
        ]

        results = self.teacher.label_sessions_batch(sessions, show_progress=False)

        # 验证结果数量
        assert len(results) == 5

        # 验证每个结果的格式
        for result in results:
            assert "intent_probs" in result
            assert "primary_intent" in result
            assert "urgency_level" in result
            assert "confidence" in result

    def test_label_devices_batch(self):
        """测试批量标注设备"""
        device_sessions = {
            "device_001": [
                {"session_id": "s1", "device_id": "device_001", "session_duration": 300}
            ],
            "device_002": [
                {"session_id": "s2", "device_id": "device_002", "session_duration": 200}
            ],
        }

        results = self.teacher.label_devices_batch(
            device_sessions,
            show_progress=False
        )

        # 验证结果数量
        assert len(results) == 2

        # 验证每个结果的格式
        for result in results:
            assert "device_id" in result
            assert "intent_probs" in result
            assert "urgency_level" in result
            assert "confidence" in result
