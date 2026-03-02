"""完整的离线训练流程（CPU 环境）

整合所有模块，实现端到端训练流程。

优化后的流程：
1. Session 切片
2. Log-to-Text 转换（基于规则引擎）
3. Proxy Label 挖掘（生成 lead/non-lead 标签）
4. Teacher Model 标注（10-20% 子集，设备级别 LLM 批量标注）
5. Student Model 训练（知识蒸馏，从 Teacher 子集学习）
6. SupCon 模型训练（基于二分类 lead/non-lead 标签）
7. 模型验证和保存
"""

import sys
from pathlib import Path
import time

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.session_slicer import SessionSlicer
from src.labeling.proxy_label_miner import ProxyLabelMiner
from src.agent.llm_client import create_llm_client
from src.agent.teacher_labeling import TeacherLabeler
from src.model.train_student_model import (
    train_student_model_cpu,
    stratified_sample_for_teacher_labeling
)
from src.model.trainer import train_supcon_model_cpu


def print_step(step_num: int, total_steps: int, title: str):
    """打印步骤标题"""
    print("\n" + "=" * 70)
    print(f"Step {step_num}/{total_steps}: {title}")
    print("=" * 70)


def main():
    """主函数"""
    print("=" * 70)
    print("ProjectNeoTrace 离线训练流程（CPU 环境）- 优化版")
    print("=" * 70)
    print(f"\n开始时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")

    total_steps = 7  # 更新为 7 个步骤

    # ========== Step 1: Session 切片 ==========
    print_step(1, total_steps, "Session 切片")

    input_file = PROJECT_ROOT / "data" / "raw" / "events.json"
    sessions_file = PROJECT_ROOT / "data" / "processed" / "sessions.csv"

    print(f"输入文件：{input_file}")
    print(f"输出文件：{sessions_file}")

    slicer = SessionSlicer(screen_off_threshold=600)
    sessions = slicer.slice_from_file(str(input_file))
    slicer.save_to_csv(sessions, str(sessions_file))

    print(f"✓ Session 切片完成，共 {len(sessions)} 个 Session")

    # ========== Step 2: Log-to-Text 转换 ==========
    print_step(2, total_steps, "Log-to-Text 转换（基于规则引擎）")

    session_texts_file = PROJECT_ROOT / "data" / "processed" / "session_texts.csv"

    print(f"输入文件：{sessions_file}")
    print(f"输出文件：{session_texts_file}")

    # 导入转换函数
    import pandas as pd
    from src.features.log_to_text_engine import (
        LogToTextEngine,
        ConversionRuleRegistry,
        TemplateRule,
        AutomotiveRule,
        FallbackRule
    )
    from src.features.log_to_text_engine.config import load_config
    from src.features.log_to_text_engine.monitor import ConversionMonitor

    # 注册规则类型
    ConversionRuleRegistry.register("template", TemplateRule)
    ConversionRuleRegistry.register("automotive", AutomotiveRule)
    ConversionRuleRegistry.register("fallback", FallbackRule)

    # 加载配置并创建引擎
    print("加载规则配置...")
    config = load_config()  # 使用默认配置
    rules = [ConversionRuleRegistry.create_rule(rule_config) for rule_config in config["rules"]]
    engine = LogToTextEngine(rules=rules, mode=config["execution"]["mode"])
    print(f"  加载了 {len(rules)} 个规则")

    # 创建监控器
    monitor = ConversionMonitor()

    # 读取 sessions
    print("读取 Session 数据...")
    df_sessions = pd.read_csv(sessions_file)

    # 转换
    print("开始转换...")
    results = []
    for _, row in df_sessions.iterrows():
        session = row.to_dict()
        result = engine.convert(session)

        # 记录监控数据
        monitor.record_conversion(result, duration_ms=0.5)

        # 构建输出记录
        output_record = {
            "device_id": session["device_id"],
            "session_id": session["session_id"],
            "session_text": result.text if result.success else "",
            "matched_rule": result.rule_id,
            "rule_priority": result.priority,
        }
        results.append(output_record)

    # 保存结果
    df_output = pd.DataFrame(results)
    df_output.to_csv(session_texts_file, index=False, encoding="utf-8")

    print(f"✓ Log-to-Text 转换完成")
    print(f"  成功转换：{len(results)} 个 Session")
    print(f"  输出文件：{session_texts_file}")

    # 打印规则命中统计
    stats = monitor.get_statistics()
    print(f"  规则命中统计：")
    for rule_id, count in stats['rule_hits'].items():
        percentage = count / stats['total_conversions'] * 100
        print(f"    - {rule_id}: {count} 次 ({percentage:.1f}%)")

    # ========== Step 3: Proxy Label 挖掘 ==========
    print_step(3, total_steps, "Proxy Label 挖掘（生成 lead/non-lead 标签）")

    print(f"输入文件：{sessions_file}")

    # 创建标签挖掘器
    miner = ProxyLabelMiner()

    # 挖掘标签
    print("挖掘代理标签...")
    labeled_sessions = miner.mine_labels(sessions)

    # 统计标签分布
    distribution = miner.get_label_distribution(labeled_sessions)

    print(f"✓ Proxy Label 挖掘完成")
    print(f"\n代理标签分布（4 级）：")
    label_names = {
        0: "Label 0 (Noise)",
        1: "Label 1 (Fans)",
        2: "Label 2 (Consider)",
        3: "Label 3 (Leads)",
    }
    for label, count in sorted(distribution["proxy_label"].items()):
        percentage = count / len(labeled_sessions) * 100
        print(f"  {label_names[label]}: {count} ({percentage:.2f}%)")

    print(f"\n二分类标签分布：")
    binary_names = {0: "Non-lead", 1: "Lead"}
    for label, count in sorted(distribution["is_lead"].items()):
        percentage = count / len(labeled_sessions) * 100
        print(f"  {binary_names[label]}: {count} ({percentage:.2f}%)")

    # 保存带标签的 sessions
    labeled_sessions_file = PROJECT_ROOT / "data" / "processed" / "labeled_sessions.csv"
    df_labeled_sessions = pd.DataFrame(labeled_sessions)
    df_labeled_sessions.to_csv(labeled_sessions_file, index=False)
    print(f"  标注结果已保存到：{labeled_sessions_file}")

    # ========== Step 4: Teacher Model 标注（10-20% 子集）==========
    print_step(4, total_steps, "Teacher Model 标注（10-20% 子集，设备级别 LLM 批量标注）")

    # 使用 Mock LLM 进行测试（实际使用时替换为真实 LLM）
    print("创建 LLM 客户端（Mock 模式）...")
    llm_client = create_llm_client(provider="mock")

    print("创建 Teacher 标注器...")
    teacher = TeacherLabeler(llm_client)

    # 按设备分组所有 Session
    print(f"按设备分组 Session...")
    from collections import defaultdict
    device_sessions = defaultdict(list)
    for session in labeled_sessions:  # 使用带标签的 sessions
        device_sessions[session['device_id']].append(session)

    # 分层采样：选择 15% 的设备用于 Teacher 标注
    print(f"\n执行分层采样（采样比例：15%）...")
    df_all_sessions = pd.DataFrame(labeled_sessions)

    # 按设备聚合，保留 proxy_label 用于分层
    device_df = df_all_sessions.groupby('device_id').agg({
        'proxy_label': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],  # 取众数
        'session_id': 'count'  # 计数
    }).reset_index()
    device_df.columns = ['device_id', 'proxy_label', 'session_count']

    # 分层采样设备
    sampled_device_df = stratified_sample_for_teacher_labeling(
        device_df,
        sample_ratio=0.15,
        stratify_column='proxy_label',
        random_state=42
    )

    # 获取采样后的设备 sessions
    sampled_device_ids = sampled_device_df['device_id'].tolist()
    sampled_device_sessions = {
        device_id: device_sessions[device_id]
        for device_id in sampled_device_ids
    }

    total_sessions = sum(len(sessions) for sessions in sampled_device_sessions.values())
    print(f"  采样了 {len(sampled_device_ids)} 个设备，共 {total_sessions} 个 Session")

    # 加载预生成的 session_texts
    print(f"加载预生成的 session_texts...")
    df_session_texts = pd.read_csv(session_texts_file)
    session_texts_dict = dict(zip(df_session_texts["session_id"], df_session_texts["session_text"]))
    print(f"  加载了 {len(session_texts_dict)} 个 session_text")

    # 设备级别标注（传入预生成的文本）
    labeled_devices = teacher.label_devices_batch(
        sampled_device_sessions,
        session_texts_dict=session_texts_dict,
        show_progress=True
    )

    # 保存标注结果
    teacher_labeled_file = PROJECT_ROOT / "data" / "processed" / "teacher_labeled.csv"

    df_labeled = pd.DataFrame(labeled_devices)
    df_labeled.to_csv(teacher_labeled_file, index=False)

    print(f"✓ Teacher 标注完成，共 {len(labeled_devices)} 个设备（15% 子集）")
    print(f"  标注结果已保存到：{teacher_labeled_file}")
    print(f"  平均每个设备 {total_sessions / len(labeled_devices):.1f} 个 Session")

    # ========== Step 5: Student Model 训练（知识蒸馏）==========
    print_step(5, total_steps, "Student Model 训练（知识蒸馏，从 Teacher 子集学习）")

    student_model_path = PROJECT_ROOT / "data" / "models" / "intent_student_model.pth"

    print(f"训练数据：{teacher_labeled_file}")
    print(f"模型保存路径：{student_model_path}")

    # 训练 Student Model（使用较少的 epochs 进行测试）
    train_student_model_cpu(
        train_data_path=str(teacher_labeled_file),
        model_save_path=str(student_model_path),
        epochs=5,  # 测试模式：5 epochs（实际使用 30）
        batch_size=32,
        learning_rate=0.001,
    )

    print(f"✓ Student Model 训练完成")

    # ========== Step 6: SupCon 模型训练（基于二分类 lead/non-lead 标签）==========
    print_step(6, total_steps, "SupCon 模型训练（基于二分类 lead/non-lead 标签）")

    supcon_model_path = PROJECT_ROOT / "data" / "models" / "supcon_model.pth"

    print(f"训练数据：{labeled_sessions_file}")  # 使用全量带标签的 sessions
    print(f"模型保存路径：{supcon_model_path}")

    # 训练 SupCon Model（使用二分类 lead/non-lead 标签）
    train_supcon_model_cpu(
        train_data_path=str(labeled_sessions_file),
        model_save_path=str(supcon_model_path),
        epochs=5,  # 测试模式：5 epochs（实际使用 30）
        batch_size=16,
        learning_rate=0.001,
        temperature=0.07,
        use_balanced_sampling=True,  # 使用平衡采样
    )

    print(f"✓ SupCon 模型训练完成")

    # ========== Step 7: 模型验证和保存 ==========
    print_step(7, total_steps, "模型验证和保存")

    print("\n模型文件：")
    print(f"  - Student Model: {student_model_path}")
    print(f"  - SupCon Model: {supcon_model_path}")

    # 验证模型文件是否存在
    if student_model_path.exists():
        size = student_model_path.stat().st_size / 1024
        print(f"    ✓ Student Model 已保存（{size:.2f} KB）")
    else:
        print(f"    ✗ Student Model 未找到")

    if supcon_model_path.exists():
        size = supcon_model_path.stat().st_size / 1024
        print(f"    ✓ SupCon Model 已保存（{size:.2f} KB）")
    else:
        print(f"    ✗ SupCon Model 未找到")

    # ========== 完成 ==========
    print("\n" + "=" * 70)
    print("训练流程完成！")
    print("=" * 70)
    print(f"\n结束时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n下一步：启动推理服务")
    print("  python src/serving/api.py")


if __name__ == "__main__":
    main()
