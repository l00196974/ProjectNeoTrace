#!/usr/bin/env python3
"""独立的 Log-to-Text 转换脚本

将 sessions.csv 转换为 session_texts.csv
"""

import sys
from pathlib import Path
import argparse
import pandas as pd
from tqdm import tqdm
import time
import logging

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.features.log_to_text_engine.engine import LogToTextEngine
from src.features.log_to_text_engine.config import load_config
from src.features.log_to_text_engine.registry import ConversionRuleRegistry
from src.features.log_to_text_engine.rules import TemplateRule, AutomotiveRule, FallbackRule
from src.features.log_to_text_engine.monitor import ConversionMonitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 注册规则类型
ConversionRuleRegistry.register("template", TemplateRule)
ConversionRuleRegistry.register("automotive", AutomotiveRule)
ConversionRuleRegistry.register("fallback", FallbackRule)


def convert_sessions_to_text(
    sessions_csv_path: str,
    output_csv_path: str,
    config_path: str = None,
    show_progress: bool = True
):
    """将 sessions.csv 转换为 session_texts.csv

    Args:
        sessions_csv_path: 输入 sessions.csv 文件路径
        output_csv_path: 输出 session_texts.csv 文件路径
        config_path: 规则配置文件路径（可选）
        show_progress: 是否显示进度条
    """
    logger.info(f"读取 Session 数据：{sessions_csv_path}")
    df_sessions = pd.read_csv(sessions_csv_path)
    logger.info(f"  共 {len(df_sessions)} 个 Session")

    # 加载配置
    logger.info(f"加载配置：{config_path or '使用默认配置'}")
    config = load_config(config_path)

    # 创建规则引擎
    rules = [ConversionRuleRegistry.create_rule(rule_config) for rule_config in config["rules"]]
    engine = LogToTextEngine(rules=rules, mode=config["execution"]["mode"])
    logger.info(f"  加载了 {len(rules)} 个规则")

    # 打印规则摘要
    rule_summary = engine.get_rule_summary()
    logger.info(f"  执行模式: {rule_summary['mode']}")
    logger.info(f"  启用规则: {rule_summary['enabled_rules']}/{rule_summary['total_rules']}")

    # 创建监控器
    monitor = ConversionMonitor()

    # 转换
    logger.info("开始转换...")
    results = []

    iterator = tqdm(df_sessions.iterrows(), total=len(df_sessions), desc="转换进度") if show_progress else df_sessions.iterrows()

    for _, row in iterator:
        session = row.to_dict()

        # 执行转换（计时）
        start_time = time.time()
        result = engine.convert(session)
        duration_ms = (time.time() - start_time) * 1000

        # 记录监控数据
        monitor.record_conversion(result, duration_ms)

        # 构建输出记录
        output_record = {
            "device_id": session["device_id"],
            "session_id": session["session_id"],
            "session_text": result.text if result.success else "",
            "matched_rule": result.rule_id,
            "rule_priority": result.priority,
            "session_duration": session["session_duration"],
            "app_count": len(eval(session.get("app_pkg_list", "[]"))) if isinstance(session.get("app_pkg_list"), str) else 0,
            "poi_count": len(eval(session.get("lbs_poi_list", "[]"))) if isinstance(session.get("lbs_poi_list"), str) else 0,
            "event_count": session["event_count"],
            "app_switch_freq": session.get("app_switch_freq", 0),
            "config_page_dwell": session.get("config_page_dwell", 0),
            "finance_page_dwell": session.get("finance_page_dwell", 0),
        }
        results.append(output_record)

    # 保存结果
    df_output = pd.DataFrame(results)
    df_output.to_csv(output_csv_path, index=False, encoding="utf-8")
    logger.info(f"✓ 转换完成，输出文件：{output_csv_path}")

    # 生成质量报告
    report = generate_quality_report(df_output)
    print_quality_report(report)

    # 打印监控统计
    monitor.print_summary()

    return df_output


def generate_quality_report(df_session_texts: pd.DataFrame) -> dict:
    """生成质量报告

    Args:
        df_session_texts: session_texts DataFrame

    Returns:
        质量报告字典
    """
    total = len(df_session_texts)
    successful = (df_session_texts["session_text"] != "").sum()

    report = {
        "total_sessions": total,
        "successful_conversions": successful,
        "success_rate": successful / total if total > 0 else 0,
        "avg_text_length": df_session_texts["session_text"].str.len().mean(),
        "empty_texts": (df_session_texts["session_text"] == "").sum(),
        "short_texts": (df_session_texts["session_text"].str.len() < 20).sum(),
        "long_texts": (df_session_texts["session_text"].str.len() > 200).sum(),
        "unique_devices": df_session_texts["device_id"].nunique(),
        "rule_hits": df_session_texts["matched_rule"].value_counts().to_dict()
    }

    return report


def print_quality_report(report: dict):
    """打印质量报告

    Args:
        report: 质量报告字典
    """
    print("\n" + "=" * 50)
    print("质量报告")
    print("=" * 50)
    print(f"总 Session 数：{report['total_sessions']}")
    print(f"成功转换：{report['successful_conversions']} ({report['success_rate']:.1%})")
    print(f"平均文本长度：{report['avg_text_length']:.1f} 字符")
    print(f"空文本数：{report['empty_texts']}")
    print(f"短文本数（< 20 字符）：{report['short_texts']}")
    print(f"长文本数（> 200 字符）：{report['long_texts']}")
    print(f"唯一设备数：{report['unique_devices']}")
    print(f"\n规则命中统计：")
    for rule_id, count in sorted(report['rule_hits'].items(), key=lambda x: x[1], reverse=True):
        percentage = count / report['total_sessions'] * 100
        print(f"  - {rule_id}: {count} 次 ({percentage:.1f}%)")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Log-to-Text 转换脚本")
    parser.add_argument(
        "--input",
        default="data/processed/sessions.csv",
        help="输入 sessions.csv 文件路径"
    )
    parser.add_argument(
        "--output",
        default="data/processed/session_texts.csv",
        help="输出 session_texts.csv 文件路径"
    )
    parser.add_argument(
        "--config",
        default=None,
        help="规则配置文件路径（YAML）"
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="不显示进度条"
    )

    args = parser.parse_args()

    convert_sessions_to_text(
        sessions_csv_path=args.input,
        output_csv_path=args.output,
        config_path=args.config,
        show_progress=not args.no_progress
    )


if __name__ == "__main__":
    main()
