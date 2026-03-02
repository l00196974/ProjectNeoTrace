#!/usr/bin/env python3
"""测试完整的离线训练流程（小数据集）

验证 Log-to-Text 转换引擎集成是否正常
"""

import sys
from pathlib import Path
import pandas as pd

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.session_slicer import SessionSlicer
from src.agent.llm_client import create_llm_client
from src.agent.teacher_labeling import TeacherLabeler
from src.features.log_to_text_engine import (
    LogToTextEngine,
    ConversionRuleRegistry,
    TemplateRule,
    AutomotiveRule,
    FallbackRule
)
from src.features.log_to_text_engine.config import load_config
from collections import defaultdict


def test_pipeline():
    """测试完整流程"""
    print("=" * 70)
    print("测试离线训练流程（Log-to-Text 转换引擎集成）")
    print("=" * 70)

    # Step 1: 读取已有的 sessions
    print("\nStep 1: 读取 Session 数据")
    sessions_file = PROJECT_ROOT / "data" / "processed" / "sessions.csv"
    df_sessions = pd.read_csv(sessions_file, nrows=100)  # 只读取前 100 个
    sessions = df_sessions.to_dict('records')
    print(f"✓ 读取了 {len(sessions)} 个 Session")

    # Step 1.5: Log-to-Text 转换
    print("\nStep 1.5: Log-to-Text 转换")

    # 注册规则
    ConversionRuleRegistry.register("template", TemplateRule)
    ConversionRuleRegistry.register("automotive", AutomotiveRule)
    ConversionRuleRegistry.register("fallback", FallbackRule)

    # 创建引擎
    config = load_config()
    rules = [ConversionRuleRegistry.create_rule(r) for r in config["rules"]]
    engine = LogToTextEngine(rules=rules)
    print(f"  加载了 {len(rules)} 个规则")

    # 转换
    results = []
    for session in sessions:
        result = engine.convert(session)
        results.append({
            "session_id": session["session_id"],
            "session_text": result.text,
            "matched_rule": result.rule_id
        })

    df_texts = pd.DataFrame(results)
    session_texts_dict = dict(zip(df_texts["session_id"], df_texts["session_text"]))
    print(f"✓ 转换了 {len(results)} 个 Session")

    # 打印样本
    print("\n样本输出：")
    for i in range(min(3, len(results))):
        print(f"  [{results[i]['matched_rule']}] {results[i]['session_text'][:80]}...")

    # Step 2: Teacher 标注
    print("\nStep 2: Teacher Model 标注")

    # 创建 Mock LLM 客户端
    llm_client = create_llm_client(provider="mock")
    teacher = TeacherLabeler(llm_client, use_mock_embedding=True)

    # 按设备分组
    device_sessions = defaultdict(list)
    for session in sessions:
        device_sessions[session['device_id']].append(session)

    # 取前 5 个设备
    device_ids = sorted(device_sessions.keys())[:5]
    sampled_device_sessions = {
        device_id: device_sessions[device_id]
        for device_id in device_ids
    }

    print(f"  采样了 {len(device_ids)} 个设备")

    # 设备级别标注（使用预生成的文本）
    labeled_devices = teacher.label_devices_batch(
        sampled_device_sessions,
        session_texts_dict=session_texts_dict,
        show_progress=False
    )

    print(f"✓ 标注了 {len(labeled_devices)} 个设备")

    # 打印样本
    print("\n标注样本：")
    for device in labeled_devices[:2]:
        print(f"  设备: {device['device_id']}")
        print(f"    Session 数: {device['session_count']}")
        print(f"    主要意图: {device['primary_intent']}")
        print(f"    紧急度: {device['urgency_score']}")

    print("\n" + "=" * 70)
    print("✓ 流程测试通过！")
    print("=" * 70)


if __name__ == "__main__":
    test_pipeline()
