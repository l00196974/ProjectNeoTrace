"""测试 Log-to-Text 转换引擎

验证规则引擎、模板引擎和转换流程
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.features.log_to_text_engine import (
    LogToTextEngine,
    ConversionRuleRegistry,
    TemplateRule,
    AutomotiveRule,
    FallbackRule
)
from src.features.log_to_text_engine.config import load_config


def test_rule_registry():
    """测试规则注册表"""
    print("测试规则注册表...")

    # 注册规则
    ConversionRuleRegistry.register("template", TemplateRule)
    ConversionRuleRegistry.register("automotive", AutomotiveRule)
    ConversionRuleRegistry.register("fallback", FallbackRule)

    # 验证注册
    types = ConversionRuleRegistry.list_registered_types()
    assert "template" in types
    assert "automotive" in types
    assert "fallback" in types

    # 测试规则创建
    config = {"id": "test", "type": "template", "priority": 50, "params": {}}
    rule = ConversionRuleRegistry.create_rule(config)
    assert rule.rule_id == "test"
    assert rule.priority == 50

    print("✓ 规则注册表测试通过")


def test_template_engine():
    """测试模板引擎"""
    print("\n测试模板引擎...")

    from src.features.log_to_text_engine.template_engine import TemplateEngine

    engine = TemplateEngine()

    # 测试时长格式化
    assert engine._format_duration(30) == "30 秒"
    assert engine._format_duration(120) == "2 分钟"
    assert engine._format_duration(3660) == "1 小时 1 分钟"

    # 测试应用列表格式化
    apps = ["com.autohome", "com.yiche"]
    result = engine._format_app_list(apps)
    assert "汽车之家" in result
    assert "易车" in result

    # 测试模板渲染
    template = "用户在 {{ duration | format_duration }} 内使用了应用"
    context = {"duration": 600}
    text = engine.render(template, context)
    assert "10 分钟" in text

    print("✓ 模板引擎测试通过")


def test_conversion_rules():
    """测试转换规则"""
    print("\n测试转换规则...")

    # 测试汽车规则
    automotive_rule = AutomotiveRule(rule_id="test_auto", priority=100)

    # 汽车 session
    auto_session = {
        "device_id": "test_device",
        "session_id": "test_session",
        "session_duration": 600,
        "app_pkg_list": ["com.autohome", "com.yiche"],
        "lbs_poi_list": ["auto_market"],
        "config_page_dwell": 120,
        "finance_page_dwell": 0,
        "app_switch_freq": 3,
        "event_count": 20
    }

    from src.features.log_to_text_engine.base import ConversionContext

    context = ConversionContext(session=auto_session)
    assert automotive_rule.match(context)

    result = automotive_rule.convert(context)
    assert result.success
    assert "汽车之家" in result.text or "易车" in result.text

    print("✓ 转换规则测试通过")


def test_engine():
    """测试执行引擎"""
    print("\n测试执行引擎...")

    # 注册规则
    ConversionRuleRegistry.register("template", TemplateRule)
    ConversionRuleRegistry.register("automotive", AutomotiveRule)
    ConversionRuleRegistry.register("fallback", FallbackRule)

    # 加载配置
    config = load_config()
    rules = [ConversionRuleRegistry.create_rule(rule_config) for rule_config in config["rules"]]
    engine = LogToTextEngine(rules=rules, mode=config["execution"]["mode"])

    # 测试汽车 session
    auto_session = {
        "device_id": "test_device",
        "session_id": "test_session",
        "session_duration": 600,
        "app_pkg_list": ["com.autohome"],
        "lbs_poi_list": ["auto_market"],
        "config_page_dwell": 120,
        "finance_page_dwell": 0,
        "app_switch_freq": 3,
        "event_count": 20
    }

    result = engine.convert(auto_session)
    assert result.success
    assert result.rule_id == "automotive_rule"
    assert len(result.text) > 0

    # 测试通用 session
    general_session = {
        "device_id": "test_device",
        "session_id": "test_session",
        "session_duration": 300,
        "app_pkg_list": ["com.tencent.mm"],
        "lbs_poi_list": [],
        "config_page_dwell": 0,
        "finance_page_dwell": 0,
        "app_switch_freq": 1,
        "event_count": 10
    }

    result = engine.convert(general_session)
    assert result.success
    assert len(result.text) > 0

    print("✓ 执行引擎测试通过")


def test_monitor():
    """测试监控系统"""
    print("\n测试监控系统...")

    from src.features.log_to_text_engine.monitor import ConversionMonitor
    from src.features.log_to_text_engine.base import ConversionResult

    monitor = ConversionMonitor()

    # 记录一些转换结果
    for i in range(10):
        result = ConversionResult(
            success=True,
            text="测试文本" * 10,
            rule_id="test_rule",
            priority=50
        )
        monitor.record_conversion(result, duration_ms=1.5)

    # 获取统计信息
    stats = monitor.get_statistics()
    assert stats["total_conversions"] == 10
    assert stats["rule_hits"]["test_rule"] == 10
    assert stats["failure_count"] == 0

    print("✓ 监控系统测试通过")


def main():
    """运行所有测试"""
    print("=" * 50)
    print("Log-to-Text 转换引擎测试")
    print("=" * 50)

    try:
        test_rule_registry()
        test_template_engine()
        test_conversion_rules()
        test_engine()
        test_monitor()

        print("\n" + "=" * 50)
        print("✓ 所有测试通过")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
