"""Student Model 训练脚本（CPU 优化）

使用知识蒸馏训练轻量级 Student Model。
"""

import sys
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import pandas as pd
import numpy as np

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.model.intent_student_model import create_student_model
from src.model.distillation_loss import IntentDistillationLoss


class IntentDistillationDataset(Dataset):
    """知识蒸馏数据集"""

    def __init__(self, data_path: str):
        """
        初始化数据集

        Args:
            data_path: 数据文件路径（CSV 格式）
        """
        self.df = pd.read_csv(data_path)

        # 提取特征和标签
        self.session_features = self._extract_session_features()
        self.teacher_probs = self._extract_teacher_probs()
        self.teacher_embeddings = self._extract_teacher_embeddings()

    def _extract_session_features(self) -> torch.Tensor:
        """提取 Session 特征（256-dim）"""
        # 简化版本：使用基础特征
        features = []
        for _, row in self.df.iterrows():
            feature = [
                float(row.get("app_switch_freq", 0)),
                float(row.get("config_page_dwell", 0)) / 60.0,
                float(row.get("finance_page_dwell", 0)) / 60.0,
                float(row.get("time_tension_bucket", 0)),
                float(row.get("session_duration", 0)) / 3600.0,
                float(row.get("event_count", 0)) / 100.0,
            ]
            # 填充到 256 维
            while len(feature) < 256:
                feature.append(0.0)
            features.append(feature[:256])

        return torch.tensor(features, dtype=torch.float32)

    def _extract_teacher_probs(self) -> torch.Tensor:
        """提取 Teacher 的意图概率（11-dim）"""
        probs = []
        for _, row in self.df.iterrows():
            # 从 intent_vector 列解析
            intent_vector_str = row.get("intent_vector", "[0.0]*11")
            try:
                intent_vector = eval(intent_vector_str)
                if len(intent_vector) != 11:
                    intent_vector = [0.0] * 11
            except:
                intent_vector = [0.0] * 11

            probs.append(intent_vector)

        return torch.tensor(probs, dtype=torch.float32)

    def _extract_teacher_embeddings(self) -> torch.Tensor:
        """提取 Teacher 的意图向量（128-dim）"""
        embeddings = []
        for _, row in self.df.iterrows():
            # 从 intent_embedding 列解析
            intent_embedding_str = row.get("intent_embedding", "[0.0]*128")
            try:
                intent_embedding = eval(intent_embedding_str)
                if len(intent_embedding) != 128:
                    intent_embedding = [0.0] * 128
            except:
                intent_embedding = [0.0] * 128

            embeddings.append(intent_embedding)

        return torch.tensor(embeddings, dtype=torch.float32)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        return (
            self.session_features[idx],
            self.teacher_probs[idx],
            self.teacher_embeddings[idx],
        )


def train_student_model_cpu(
    train_data_path: str,
    val_data_path: str = None,
    model_save_path: str = None,
    epochs: int = 30,
    batch_size: int = 32,
    learning_rate: float = 0.001,
    alpha: float = 0.5,
):
    """
    CPU 训练 Student Model

    Args:
        train_data_path: 训练数据路径
        val_data_path: 验证数据路径（可选）
        model_save_path: 模型保存路径
        epochs: 训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
        alpha: 蒸馏损失权重
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

    # 损失函数和优化器
    criterion = IntentDistillationLoss(alpha=alpha)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    # 训练循环
    print(f"\n开始训练（{epochs} epochs）...")
    best_val_loss = float("inf")

    for epoch in range(epochs):
        # 训练阶段
        model.train()
        train_loss = 0.0
        train_cls_loss = 0.0
        train_emb_loss = 0.0

        for batch_idx, (session_features, teacher_probs, teacher_embedding) in enumerate(
            train_loader
        ):
            session_features = session_features.to(device)
            teacher_probs = teacher_probs.to(device)
            teacher_embedding = teacher_embedding.to(device)

            # Forward
            student_probs, student_embedding = model(session_features)

            # Loss
            loss = criterion(
                student_probs, student_embedding, teacher_probs, teacher_embedding
            )

            # 获取损失组成部分
            loss_components = criterion.get_loss_components(
                student_probs, student_embedding, teacher_probs, teacher_embedding
            )

            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_cls_loss += loss_components["classification_loss"]
            train_emb_loss += loss_components["embedding_loss"]

        avg_train_loss = train_loss / len(train_loader)
        avg_train_cls_loss = train_cls_loss / len(train_loader)
        avg_train_emb_loss = train_emb_loss / len(train_loader)

        # 验证阶段
        val_loss_str = ""
        if val_loader:
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for session_features, teacher_probs, teacher_embedding in val_loader:
                    session_features = session_features.to(device)
                    teacher_probs = teacher_probs.to(device)
                    teacher_embedding = teacher_embedding.to(device)

                    student_probs, student_embedding = model(session_features)
                    loss = criterion(
                        student_probs, student_embedding, teacher_probs, teacher_embedding
                    )
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
            f"Train Loss: {avg_train_loss:.4f} "
            f"(Cls: {avg_train_cls_loss:.4f}, Emb: {avg_train_emb_loss:.4f})"
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
        alpha=0.5,
    )


if __name__ == "__main__":
    main()
