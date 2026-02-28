"""测试 Teacher Model 标注功能

使用 Mock LLM 客户端测试标注流程。
"""

import sys
from pathlib import Path
import pandas as pd

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.llm_client import create_llm_client
from src.agent.teacher_labeling import TeacherLabeler


def test_teacher_labeling():
    """测试 Teacher Model 标注"""
    print("=" * 60)
    print("测试 Teacher Model 标注")
    print("=" * 60)

    # 1. 加载 Session 数据
    sessions_file = PROJECT_ROOT / "data" / "processed" / "sessions.csv"
    print(f"\n加载 Session 数据：{sessions_file}")

    df = pd.read_csv(sessions_file)
    sessions = df.head(10).to_dict("records")  # 只测试前 10 个
    print(f"加载了 {len(sessions)} 个 Session")

    # 2. 创建 Mock LLM 客户端
    print("\n创建 Mock LLM 客户端...")
    llm_client = create_llm_client(provider="mock")

    # 3. 创建 Teacher 标注器
    print("创建 Teacher 标注器...")
    teacher = TeacherLabeler(llm_client, use_mock_embedding=True)

    # 4. 标注单个 Session
    print("\n=== 测试单个 Session 标注 ===")
    session = sessions[0]
    print(f"Session ID: {session['session_id']}")

    label = teacher.label_session(session)

    print(f"\nSession 文本：{label['session_text']}")
    print(f"主要意图：{label['primary_intent']}")
    print(f"紧急度：{label['urgency_score']}")
    print(f"意图向量维度：{len(label['intent_vector'])}")
    print(f"意图向量：{label['intent_vector']}")
    print(f"意图嵌入维度：{len(label['intent_embedding'])}")

    # 5. 批量标注
    print("\n=== 测试批量标注 ===")
    labeled_sessions = teacher.label_sessions_batch(sessions[:5], show_progress=True)

    print(f"\n标注完成，共 {len(labeled_sessions)} 个 Session")

    # 6. 保存结果
    output_file = PROJECT_ROOT / "data" / "processed" / "teacher_labeled_sample.csv"
    df_labeled = pd.DataFrame(labeled_sessions)
    df_labeled.to_csv(output_file, index=False)
    print(f"\n标注结果已保存到：{output_file}")

    # 7. 统计信息
    print("\n=== 统计信息 ===")
    print(f"标注成功率：{len(labeled_sessions) / len(sessions) * 100:.2f}%")

    # 统计主要意图分布
    primary_intents = [s["primary_intent"] for s in labeled_sessions]
    intent_counts = {}
    for intent in primary_intents:
        intent_counts[intent] = intent_counts.get(intent, 0) + 1

    print("\n主要意图分布：")
    for intent, count in sorted(intent_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {intent}: {count}")


if __name__ == "__main__":
    test_teacher_labeling()
