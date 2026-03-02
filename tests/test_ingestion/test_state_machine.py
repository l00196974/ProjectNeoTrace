"""
测试重构后的状态机 - 确保向后兼容性
"""

import pytest
from src.ingestion.state_machine import SessionStateMachine, SessionState
from src.ingestion.rule_engine import RuleRegistry
from src.ingestion.rule_engine.rules import ScreenOffRule, LBSCrossingRule, AppCategoryRule


@pytest.fixture(autouse=True)
def ensure_rules_registered():
    """确保规则已注册（每个测试前执行）"""
    RuleRegistry.register("screen_off", ScreenOffRule)
    RuleRegistry.register("lbs_crossing", LBSCrossingRule)
    RuleRegistry.register("app_category_change", AppCategoryRule)
    yield


class TestSessionStateMachineBackwardCompatibility:
    """测试状态机向后兼容性"""

    def test_initialization_default(self):
        """测试默认初始化"""
        sm = SessionStateMachine()

        assert sm.state == SessionState.ACTIVE
        assert sm.last_timestamp is None
        assert sm.last_poi is None
        assert sm.last_category is None
        assert sm.screen_off_time is None

    def test_initialization_with_threshold(self):
        """测试使用自定义阈值初始化（向后兼容）"""
        sm = SessionStateMachine(screen_off_threshold=300)

        # 验证规则引擎已加载
        assert sm.engine is not None
        assert len(sm.engine.rules) == 3

        # 验证阈值已应用
        screen_off_rule = sm.engine.get_rule("screen_off_rule")
        assert screen_off_rule is not None
        assert screen_off_rule.params["threshold_seconds"] == 300

    def test_first_event_no_new_session(self):
        """测试第一个事件不触发新 Session"""
        sm = SessionStateMachine()
        event = {
            "timestamp": 1000,
            "action": "app_foreground",
            "app_pkg": "com.autohome"
        }

        result = sm.should_start_new_session(event)

        assert result is False
        assert sm.last_timestamp == 1000

    def test_screen_off_triggers_new_session(self):
        """测试息屏超时触发新 Session"""
        sm = SessionStateMachine(screen_off_threshold=600)

        # 第一个事件：息屏
        event1 = {
            "timestamp": 1000,
            "action": "screen_off",
            "app_pkg": ""
        }
        sm.should_start_new_session(event1)

        # 第二个事件：超过阈值后的事件
        event2 = {
            "timestamp": 2000,
            "action": "app_foreground",
            "app_pkg": "com.autohome"
        }
        result = sm.should_start_new_session(event2)

        assert result is True

    def test_screen_off_below_threshold(self):
        """测试息屏未超过阈值不触发"""
        sm = SessionStateMachine(screen_off_threshold=600)

        event1 = {
            "timestamp": 1000,
            "action": "screen_off",
            "app_pkg": ""
        }
        sm.should_start_new_session(event1)

        event2 = {
            "timestamp": 1500,
            "action": "app_foreground",
            "app_pkg": "com.autohome"
        }
        result = sm.should_start_new_session(event2)

        assert result is False

    def test_lbs_crossing_triggers_new_session(self):
        """测试 LBS 地标跨越触发新 Session"""
        sm = SessionStateMachine()

        event1 = {
            "timestamp": 1000,
            "action": "app_foreground",
            "app_pkg": "com.autohome",
            "payload": {"lbs_poi": "home"}
        }
        sm.should_start_new_session(event1)

        event2 = {
            "timestamp": 2000,
            "action": "app_foreground",
            "app_pkg": "com.autohome",
            "payload": {"lbs_poi": "auto_market"}
        }
        result = sm.should_start_new_session(event2)

        assert result is True

    def test_lbs_same_level_no_trigger(self):
        """测试相同层级 POI 不触发"""
        sm = SessionStateMachine()

        event1 = {
            "timestamp": 1000,
            "action": "app_foreground",
            "app_pkg": "com.autohome",
            "payload": {"lbs_poi": "home"}
        }
        sm.should_start_new_session(event1)

        event2 = {
            "timestamp": 2000,
            "action": "app_foreground",
            "app_pkg": "com.autohome",
            "payload": {"lbs_poi": "office"}
        }
        result = sm.should_start_new_session(event2)

        assert result is False

    def test_app_category_change_triggers_new_session(self):
        """测试应用类目跳变触发新 Session"""
        sm = SessionStateMachine()

        event1 = {
            "timestamp": 1000,
            "action": "app_foreground",
            "app_pkg": "com.tencent.mm"
        }
        sm.should_start_new_session(event1)

        event2 = {
            "timestamp": 2000,
            "action": "app_foreground",
            "app_pkg": "com.autohome"
        }
        result = sm.should_start_new_session(event2)

        assert result is True

    def test_app_category_same_no_trigger(self):
        """测试相同类目不触发"""
        sm = SessionStateMachine()

        event1 = {
            "timestamp": 1000,
            "action": "app_foreground",
            "app_pkg": "com.autohome"
        }
        sm.should_start_new_session(event1)

        event2 = {
            "timestamp": 2000,
            "action": "app_foreground",
            "app_pkg": "com.yiche"
        }
        result = sm.should_start_new_session(event2)

        assert result is False

    def test_reset(self):
        """测试重置状态机"""
        sm = SessionStateMachine()

        # 设置一些状态
        event = {
            "timestamp": 1000,
            "action": "app_foreground",
            "app_pkg": "com.autohome",
            "payload": {"lbs_poi": "home"}
        }
        sm.should_start_new_session(event)

        # 重置
        sm.reset()

        assert sm.state == SessionState.ACTIVE
        assert sm.last_timestamp is None
        assert sm.last_poi is None
        assert sm.last_category is None
        assert sm.screen_off_time is None

    def test_state_updates_on_screen_off(self):
        """测试息屏时状态更新"""
        sm = SessionStateMachine()

        event = {
            "timestamp": 1000,
            "action": "screen_off",
            "app_pkg": ""
        }
        sm.should_start_new_session(event)

        assert sm.state == SessionState.IDLE
        assert sm.screen_off_time == 1000

    def test_state_updates_on_screen_on(self):
        """测试亮屏时状态更新"""
        sm = SessionStateMachine()

        event1 = {
            "timestamp": 1000,
            "action": "screen_off",
            "app_pkg": ""
        }
        sm.should_start_new_session(event1)

        event2 = {
            "timestamp": 1500,
            "action": "screen_on",
            "app_pkg": ""
        }
        sm.should_start_new_session(event2)

        assert sm.state == SessionState.ACTIVE
        assert sm.screen_off_time is None

    def test_priority_screen_off_over_lbs(self):
        """测试息屏规则优先级高于 LBS"""
        sm = SessionStateMachine(screen_off_threshold=600)

        event1 = {
            "timestamp": 1000,
            "action": "screen_off",
            "app_pkg": "",
            "payload": {"lbs_poi": "home"}
        }
        sm.should_start_new_session(event1)

        # 同时满足息屏和 LBS 跨越
        event2 = {
            "timestamp": 2000,
            "action": "app_foreground",
            "app_pkg": "com.autohome",
            "payload": {"lbs_poi": "auto_market"}
        }
        result = sm.should_start_new_session(event2)

        assert result is True

    def test_multiple_sessions(self):
        """测试多个 Session 切割"""
        sm = SessionStateMachine()

        events = [
            {"timestamp": 1000, "action": "app_foreground", "app_pkg": "com.autohome"},
            {"timestamp": 2000, "action": "app_foreground", "app_pkg": "com.tencent.mm"},  # 类目跳变
            {"timestamp": 3000, "action": "app_foreground", "app_pkg": "com.sina.weibo"},
            {"timestamp": 4000, "action": "app_foreground", "app_pkg": "com.autohome"},  # 类目跳变
        ]

        results = [sm.should_start_new_session(e) for e in events]

        assert results == [False, True, False, True]


class TestSessionStateMachineWithConfig:
    """测试使用配置文件的状态机"""

    def test_load_from_yaml_config(self, tmp_path):
        """测试从 YAML 配置加载"""
        config_content = """
rules:
  - id: screen_off_rule
    type: screen_off
    enabled: true
    priority: 100
    params:
      threshold_seconds: 300

  - id: lbs_crossing_rule
    type: lbs_crossing
    enabled: false
    priority: 50
    params:
      poi_hierarchy:
        home: 1
        auto_market: 2

  - id: app_category_rule
    type: app_category_change
    enabled: true
    priority: 30
    params:
      category_map:
        com.autohome: automotive
        com.tencent.mm: social

execution:
  mode: chain
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        sm = SessionStateMachine(config_path=str(config_file))

        assert sm.engine is not None
        assert len(sm.engine.rules) == 3

        # 验证 LBS 规则被禁用
        lbs_rule = sm.engine.get_rule("lbs_crossing_rule")
        assert lbs_rule.enabled is False

    def test_disabled_rule_not_triggered(self, tmp_path):
        """测试禁用的规则不触发"""
        config_content = """
rules:
  - id: screen_off_rule
    type: screen_off
    enabled: true
    priority: 100
    params:
      threshold_seconds: 600

  - id: lbs_crossing_rule
    type: lbs_crossing
    enabled: false
    priority: 50
    params:
      poi_hierarchy:
        home: 1
        auto_market: 2

  - id: app_category_rule
    type: app_category_change
    enabled: true
    priority: 30
    params:
      category_map:
        com.autohome: automotive

execution:
  mode: chain
"""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(config_content)

        sm = SessionStateMachine(config_path=str(config_file))

        event1 = {
            "timestamp": 1000,
            "action": "app_foreground",
            "app_pkg": "com.autohome",
            "payload": {"lbs_poi": "home"}
        }
        sm.should_start_new_session(event1)

        # LBS 跨越，但规则被禁用
        event2 = {
            "timestamp": 2000,
            "action": "app_foreground",
            "app_pkg": "com.autohome",
            "payload": {"lbs_poi": "auto_market"}
        }
        result = sm.should_start_new_session(event2)

        assert result is False
