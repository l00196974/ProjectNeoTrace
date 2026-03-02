"""
测试内置 Session 切片规则
"""

import pytest
from src.ingestion.rule_engine.base import RuleContext, RuleResult
from src.ingestion.rule_engine.rules import (
    ScreenOffRule,
    LBSCrossingRule,
    AppCategoryRule,
)


class TestScreenOffRule:
    """测试息屏超时规则"""

    def test_screen_off_exceeds_threshold(self):
        """测试息屏时长超过阈值"""
        rule = ScreenOffRule("screen_off", {"params": {"threshold_seconds": 600}})

        context = RuleContext(
            event={"timestamp": 1000},
            state={"screen_off_time": 100}
        )

        result = rule.evaluate(context)

        assert result.triggered is True
        assert "900s" in result.reason
        assert "600s" in result.reason

    def test_screen_off_below_threshold(self):
        """测试息屏时长未超过阈值"""
        rule = ScreenOffRule("screen_off", {"params": {"threshold_seconds": 600}})

        context = RuleContext(
            event={"timestamp": 500},
            state={"screen_off_time": 100}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "未超过阈值" in result.reason

    def test_screen_off_no_record(self):
        """测试无息屏记录"""
        rule = ScreenOffRule("screen_off", {"params": {"threshold_seconds": 600}})

        context = RuleContext(
            event={"timestamp": 1000},
            state={}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "无息屏记录" in result.reason

    def test_screen_off_default_threshold(self):
        """测试默认阈值"""
        rule = ScreenOffRule("screen_off", {})

        context = RuleContext(
            event={"timestamp": 1000},
            state={"screen_off_time": 100}
        )

        result = rule.evaluate(context)

        assert result.triggered is True
        assert "900s" in result.reason

    def test_screen_off_exact_threshold(self):
        """测试息屏时长等于阈值"""
        rule = ScreenOffRule("screen_off", {"params": {"threshold_seconds": 600}})

        context = RuleContext(
            event={"timestamp": 700},
            state={"screen_off_time": 100}
        )

        result = rule.evaluate(context)

        assert result.triggered is False


class TestLBSCrossingRule:
    """测试 LBS 地标跨越规则"""

    def test_poi_crossing_different_levels(self):
        """测试不同层级 POI 跨越"""
        poi_hierarchy = {
            "home": 1,
            "office": 1,
            "auto_market": 2,
            "4s_store": 2,
        }

        rule = LBSCrossingRule("lbs", {"params": {"poi_hierarchy": poi_hierarchy}})

        context = RuleContext(
            event={"payload": {"lbs_poi": "auto_market"}},
            state={"last_poi": "home"}
        )

        result = rule.evaluate(context)

        assert result.triggered is True
        assert "home" in result.reason
        assert "auto_market" in result.reason
        assert "层级1" in result.reason
        assert "层级2" in result.reason

    def test_poi_same_level(self):
        """测试相同层级 POI"""
        poi_hierarchy = {
            "home": 1,
            "office": 1,
            "auto_market": 2,
        }

        rule = LBSCrossingRule("lbs", {"params": {"poi_hierarchy": poi_hierarchy}})

        context = RuleContext(
            event={"payload": {"lbs_poi": "office"}},
            state={"last_poi": "home"}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "层级未变化" in result.reason

    def test_poi_same_location(self):
        """测试相同 POI"""
        poi_hierarchy = {"home": 1}

        rule = LBSCrossingRule("lbs", {"params": {"poi_hierarchy": poi_hierarchy}})

        context = RuleContext(
            event={"payload": {"lbs_poi": "home"}},
            state={"last_poi": "home"}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "未变化" in result.reason

    def test_poi_missing_current(self):
        """测试缺少当前 POI"""
        poi_hierarchy = {"home": 1}

        rule = LBSCrossingRule("lbs", {"params": {"poi_hierarchy": poi_hierarchy}})

        context = RuleContext(
            event={"payload": {}},
            state={"last_poi": "home"}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "不完整" in result.reason

    def test_poi_missing_last(self):
        """测试缺少上一个 POI"""
        poi_hierarchy = {"home": 1}

        rule = LBSCrossingRule("lbs", {"params": {"poi_hierarchy": poi_hierarchy}})

        context = RuleContext(
            event={"payload": {"lbs_poi": "home"}},
            state={}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "不完整" in result.reason

    def test_poi_unknown(self):
        """测试未知 POI"""
        poi_hierarchy = {"home": 1}

        rule = LBSCrossingRule("lbs", {"params": {"poi_hierarchy": poi_hierarchy}})

        context = RuleContext(
            event={"payload": {"lbs_poi": "unknown_poi"}},
            state={"last_poi": "home"}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "未知 POI" in result.reason

    def test_poi_default_hierarchy(self):
        """测试默认层级字典"""
        rule = LBSCrossingRule("lbs", {})

        context = RuleContext(
            event={"payload": {"lbs_poi": "auto_market"}},
            state={"last_poi": "home"}
        )

        result = rule.evaluate(context)

        assert result.triggered is False


class TestAppCategoryRule:
    """测试应用类目跳变规则"""

    def test_category_change(self):
        """测试应用类目跳变"""
        category_map = {
            "com.autohome": "automotive",
            "com.tencent.mm": "social",
        }

        rule = AppCategoryRule("app_cat", {"params": {"category_map": category_map}})

        context = RuleContext(
            event={"app_pkg": "com.autohome"},
            state={"last_category": "social"}
        )

        result = rule.evaluate(context)

        assert result.triggered is True
        assert "social" in result.reason
        assert "automotive" in result.reason

    def test_category_same(self):
        """测试应用类目相同"""
        category_map = {
            "com.autohome": "automotive",
            "com.yiche": "automotive",
        }

        rule = AppCategoryRule("app_cat", {"params": {"category_map": category_map}})

        context = RuleContext(
            event={"app_pkg": "com.yiche"},
            state={"last_category": "automotive"}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "未变化" in result.reason

    def test_category_missing_current(self):
        """测试缺少当前应用类目"""
        category_map = {"com.autohome": "automotive"}

        rule = AppCategoryRule("app_cat", {"params": {"category_map": category_map}})

        context = RuleContext(
            event={"app_pkg": "com.unknown.app"},
            state={"last_category": "automotive"}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "不完整" in result.reason

    def test_category_missing_last(self):
        """测试缺少上一个应用类目"""
        category_map = {"com.autohome": "automotive"}

        rule = AppCategoryRule("app_cat", {"params": {"category_map": category_map}})

        context = RuleContext(
            event={"app_pkg": "com.autohome"},
            state={}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
        assert "不完整" in result.reason

    def test_category_empty_app_pkg(self):
        """测试空应用包名"""
        category_map = {"com.autohome": "automotive"}

        rule = AppCategoryRule("app_cat", {"params": {"category_map": category_map}})

        context = RuleContext(
            event={"app_pkg": ""},
            state={"last_category": "automotive"}
        )

        result = rule.evaluate(context)

        assert result.triggered is False

    def test_category_default_map(self):
        """测试默认类目映射"""
        rule = AppCategoryRule("app_cat", {})

        context = RuleContext(
            event={"app_pkg": "com.autohome"},
            state={"last_category": "social"}
        )

        result = rule.evaluate(context)

        assert result.triggered is False
