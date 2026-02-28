"""完整的离线训练流程（CPU 环境）

整合所有模块，实现端到端训练流程。

流程：
1. Session 切片
2. Teacher Model 标注（LLM 批量标注）
3. Student Model 训练（知识蒸馏）
4. 弱监督标签挖掘
5. SupCon 模型训练
6. 模型验证和保存
"""

import sys
from pathlib import Path
import time

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.session_slicer import SessionSlicer
from src.agent.llm_client import create_llm_client
from src.agent.teacher_labeling import TeacherLabeler
from src.labeling.proxy_label_miner import ProxyLabelMiner
from src.model.train_student_model import train_student_model_cpu
from src.model.trainer import train_supcon_model_cpu


def print_step(step_num: int, total_steps: int, title: str):
    """打印步骤标题"""
    print("\n" + "=" * 70)
    print(f"Step {step_num}/{total_steps}: {title}")
    print("=" * 70)


def main():
    """主函数"""
    print("=" * 70)
    print("ProjectNeoTrace 离线训练流程（CPU 环境）")
    print("=" * 70)
    print(f"\n开始时间：{time.strftime('%Y-%m-%d %H:%M:%S')}")

    total_steps = 6

    # ========== Step 1: Session 切片 ==========
    print_step(1, total_steps, "Session 切片")

    input_file = PROJECT_ROOT / "data" / "raw" / "events.json"
    sessions_file = PROJECT_ROOT / "data" / "processed" / "sessions.csv"

    print(f"输入文件：{input_file}")
    print(f"输出文件：{sessions_file}")

    slicer = SessionSlicer(screen_off_threshold=600)
    sessions = slicer.slice_from_file(str(input_file))
    slicer.save_to_parquet(sessions, str(sessions_file))

    print(f"✓ Session 切片完成，共 {len(sessions)} 个 Session")

    # ========== Step 2: Teacher Model 标注（LLM 批量标注）==========
    print_step(2, total_steps, "Teacher Model 标注（LLM 批量标注）")

    # 使用 Mock LLM 进行测试（实际使用时替换为真实 LLM）
    print("创建 LLM 客户端（Mock 模式）...")
    llm_client = create_llm_client(provider="mock")

    print("创建 Teacher 标注器...")
    teacher = TeacherLabeler(llm_client, use_mock_embedding=True)

    # 只标注前 100 个 Session（测试用）
    print(f"标注前 100 个 Session（测试模式）...")
    labeled_sessions = teacher.label_sessions_batch(sessions[:100], show_progress=True)

    # 保存标注结果
    teacher_labeled_file = PROJECT_ROOT / "data" / "processed" / "teacher_labeled.csv"
    import pandas as pd

    df_labeled = pd.DataFrame(labeled_sessions)
    df_labeled.to_csv(teacher_labeled_file, index=False)

    print(f"✓ Teacher 标注完成，共 {len(labeled_sessions)} 个 Session")
    print(f"  标注结果已保存到：{teacher_labeled_file}")

    # ========== Step 3: Student Model 训练（知识蒸馏）==========
    print_step(3, total_steps, "Student Model 训练（知识蒸馏）")

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
        alpha=0.5,
    )

    print(f"✓ Student Model 训练完成")

    # ========== Step 4: 弱监督标签挖掘 ==========
    print_step(4, total_steps, "弱监督标签挖掘")

    print("创建标签挖掘器...")
    miner = ProxyLabelMiner()

    print("挖掘标签...")
    labeled_sessions_with_proxy = miner.mine_labels(sessions[:100])

    # 统计标签分布
    distribution = miner.get_label_distribution(labeled_sessions_with_proxy)
    print("\n标签分布：")
    label_names = {
        0: "Label 0 (Noise)",
        1: "Label 1 (Fans)",
        2: "Label 2 (Consider)",
        3: "Label 3 (Leads)",
    }
    for label, count in sorted(distribution.items()):
        percentage = count / len(labeled_sessions_with_proxy) * 100
        print(f"  {label_names[label]}: {count} ({percentage:.2f}%)")

    # 保存结果
    labeled_sessions_file = PROJECT_ROOT / "data" / "processed" / "labeled_sessions.csv"
    df_labeled_proxy = pd.DataFrame(labeled_sessions_with_proxy)
    df_labeled_proxy.to_csv(labeled_sessions_file, index=False)

    print(f"✓ 标签挖掘完成，共 {len(labeled_sessions_with_proxy)} 个 Session")
    print(f"  标注结果已保存到：{labeled_sessions_file}")

    # ========== Step 5: SupCon 模型训练 ==========
    print_step(5, total_steps, "SupCon 模型训练")

    supcon_model_path = PROJECT_ROOT / "data" / "models" / "supcon_model.pth"

    print(f"训练数据：{labeled_sessions_file}")
    print(f"模型保存路径：{supcon_model_path}")

    # 训练 SupCon Model（使用较少的 epochs 进行测试）
    train_supcon_model_cpu(
        train_data_path=str(labeled_sessions_file),
        model_save_path=str(supcon_model_path),
        epochs=5,  # 测试模式：5 epochs（实际使用 30）
        batch_size=16,
        learning_rate=0.001,
        temperature=0.07,
    )

    print(f"✓ SupCon 模型训练完成")

    # ========== Step 6: 模型验证和保存 ==========
    print_step(6, total_steps, "模型验证和保存")

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
