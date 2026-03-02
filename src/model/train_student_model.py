"""Student Model 训练脚本（CPU 优化）

使用知识蒸馏训练轻量级 Student Model。
支持从 Teacher 标注的子集（10-20%）进行训练。
"""

import sys
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.model.intent_student_model import create_student_model
from src.model.distillation_loss import IntentDistillationLoss


def stratified_sample_for_teacher_labeling(
    sessions_df: pd.DataFrame,
    sample_ratio: float = 0.15,
    stratify_column: str = "proxy_label",
    random_state: int = 42
) -> pd.DataFrame:
    """对 sessions 进行分层采样，选择子集用于 Teacher 标注。

    Args:
        sessions_df: 完整的 sessions DataFrame
        sample_ratio: 采样比例（默认 15%，即 10-20% 范围内）
        stratify_column: 用于分层的列名（默认使用 proxy_label）
        random_state: 随机种子

    Returns:
        采样后的 DataFrame
    """
    print(f"\n执行分层采样（采样比例：{sample_ratio*100:.1f}%）...")
    print(f"分层依据：{stratify_column}")

    # 确保分层列存在
    if stratify_column not in sessions_df.columns:
        print(f"警告：{stratify_column} 列不存在，使用随机采样")
        return sessions_df.sample(frac=sample_ratio, random_state=random_state)

    # 分层采样
    sampled_df, _ = train_test_split(
        sessions_df,
        train_size=sample_ratio,
        stratify=sessions_df[stratify_column],
        random_state=random_state
    )

    print(f"原始样本数：{len(sessions_df)}")
    print(f"采样后样本数：{len(sampled_df)}")

    # 显示标签分布
    if stratify_column in sampled_df.columns:
        print(f"\n采样后的 {stratify_column} 分布：")
        distribution = sampled_df[stratify_column].value_counts().sort_index()
        for label, count in distribution.items():
            percentage = count / len(sampled_df) * 100
            print(f"  Label {label}: {count} ({percentage:.2f}%)")

    return sampled_df


class IntentDistillationDataset(Dataset):
    """知识蒸馏数据集 - 支持设备级别的数据（简化版，不使用 Teacher embedding）"""

    def __init__(self, data_path: str):
        """
        初始化数据集

        Args:
            data_path: 数据文件路径（CSV 格式）
        """
        self.df = pd.read_csv(data_path)

        # 提取特征和标签
        self.device_features = self._extract_device_features()
        self.teacher_probs = self._extract_teacher_probs()

    def _extract_device_features(self) -> torch.Tensor:
        """提取设备特征（256-dim）"""
        # 简化版本：使用设备级别的基础特征
        features = []
        for _, row in self.df.iterrows():
            feature = [
                float(row.get("session_count", 0)) / 100.0,  # 归一化 session 数量
                float(row.get("total_duration", 0)) / 3600.0,  # 归一化总时长（小时）
                # urgency_level 转换为数值：high=1.0, medium=0.5, low=0.0
                self._urgency_level_to_float(row.get("urgency_level", "low")),
            ]
            # 填充到 256 维
            while len(feature) < 256:
                feature.append(0.0)
            features.append(feature[:256])

        return torch.tensor(features, dtype=torch.float32)

    def _urgency_level_to_float(self, urgency_level: str) -> float:
        """将 urgency_level 转换为浮点数"""
        mapping = {"high": 1.0, "medium": 0.5, "low": 0.0}
        return mapping.get(str(urgency_level).lower(), 0.0)

    def _extract_teacher_probs(self) -> torch.Tensor:
        """提取 Teacher 的意图概率（11-dim）"""
        probs = []
        for _, row in self.df.iterrows():
            # 从 intent_probs 列解析（新格式）
            intent_probs_str = row.get("intent_probs", row.get("intent_vector", "[0.0]*11"))
            try:
                intent_probs = eval(intent_probs_str)
                if len(intent_probs) != 11:
                    intent_probs = [0.0] * 11
            except:
                intent_probs = [0.0] * 11

            probs.append(intent_probs)

        return torch.tensor(probs, dtype=torch.float32)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        return (
            self.device_features[idx],
            self.teacher_probs[idx],
        )


def train_student_model_cpu(
    train_data_path: str,
    val_data_path: str = None,
    model_save_path: str = None,
    epochs: int = 30,
    batch_size: int = 32,
    learning_rate: float = 0.001,
):
    """
    CPU 训练 Student Model（简化版，不使用 Teacher embedding）

    Args:
        train_data_path: 训练数据路径
        val_data_path: 验证数据路径（可选）
        model_save_path: 模型保存路径
        epochs: 训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
    """
    print("=" * 60)
    print("Student Model 训练（CPU）")
    print("=" * 60)

    # 强制使用 CPU
    device = torch.device("cpu")
    print(f"\n设备：{device}")

    # 数据加载
    print(f"\n加载训练数据：{train_data_path}")
    train_dataset = IntentDistillationDataset(train_data_path)
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=4,  # CPU 多线程加速
    )
    print(f"训练样本数：{len(train_dataset)}")

    # 验证数据（可选）
    val_loader = None
    if val_data_path:
        print(f"加载验证数据：{val_data_path}")
        val_dataset = IntentDistillationDataset(val_data_path)
        val_loader = DataLoader(
            val_dataset, batch_size=batch_size, shuffle=False, num_workers=4
        )
        print(f"验证样本数：{len(val_dataset)}")

    # 模型初始化（轻量级）
    print("\n创建 Student Model...")
    model = create_student_model(
        input_dim=256, hidden_dim=64, intent_dim=11, embedding_dim=128, dropout=0.2
    ).to(device)

    # 损失函数和优化器（简化版，只使用分类损失）
    criterion = IntentDistillationLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    # 训练循环
    print(f"\n开始训练（{epochs} epochs）...")
    best_val_loss = float("inf")

    for epoch in range(epochs):
        # 训练阶段
        model.train()
        train_loss = 0.0

        for batch_idx, (session_features, teacher_probs) in enumerate(train_loader):
            session_features = session_features.to(device)
            teacher_probs = teacher_probs.to(device)

            # Forward
            student_probs, student_embedding = model(session_features)

            # Loss（只使用分类损失）
            loss = criterion(student_probs, teacher_probs)

            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

        avg_train_loss = train_loss / len(train_loader)

        # 验证阶段
        val_loss_str = ""
        if val_loader:
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for session_features, teacher_probs in val_loader:
                    session_features = session_features.to(device)
                    teacher_probs = teacher_probs.to(device)

                    student_probs, student_embedding = model(session_features)
                    loss = criterion(student_probs, teacher_probs)
                    val_loss += loss.item()

            avg_val_loss = val_loss / len(val_loader)
            val_loss_str = f", Val Loss: {avg_val_loss:.4f}"

            # 保存最佳模型
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                if model_save_path:
                    torch.save(model.state_dict(), model_save_path)
                    print(f"  → 保存最佳模型（Val Loss: {avg_val_loss:.4f}）")

        print(
            f"Epoch {epoch+1}/{epochs} - "
            f"Train Loss: {avg_train_loss:.4f}"
            f"{val_loss_str}"
        )

    # 保存最终模型
    if model_save_path and not val_loader:
        torch.save(model.state_dict(), model_save_path)
        print(f"\n模型已保存到：{model_save_path}")

    print("\n训练完成！")
    return model


def main():
    """主函数"""
    # 训练数据路径
    train_data_path = PROJECT_ROOT / "data" / "processed" / "teacher_labeled_sample.csv"
    model_save_path = PROJECT_ROOT / "data" / "models" / "intent_student_model.pth"

    # 确保模型目录存在
    model_save_path.parent.mkdir(parents=True, exist_ok=True)

    # 训练模型
    model = train_student_model_cpu(
        train_data_path=str(train_data_path),
        model_save_path=str(model_save_path),
        epochs=30,
        batch_size=32,
        learning_rate=0.001,
    )


if __name__ == "__main__":
    main()
