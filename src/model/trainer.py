"""SupCon 模型训练脚本（CPU 优化）

使用 Supervised Contrastive Loss 训练 Projection Head。
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

from src.model.projection_head import create_projection_head
from src.model.supcon_loss import SupConLoss


class SupConDataset(Dataset):
    """SupCon 训练数据集"""

    def __init__(self, data_path: str):
        """
        初始化数据集

        Args:
            data_path: 数据文件路径（CSV 格式）
        """
        self.df = pd.read_csv(data_path)

        # 提取特征和标签
        self.vectors = self._extract_vectors()
        self.labels = self._extract_labels()

    def _extract_vectors(self) -> torch.Tensor:
        """提取融合向量（256-dim）"""
        # 简化版本：使用基础特征
        vectors = []
        for _, row in self.df.iterrows():
            vector = [
                float(row.get("app_switch_freq", 0)),
                float(row.get("config_page_dwell", 0)) / 60.0,
                float(row.get("finance_page_dwell", 0)) / 60.0,
                float(row.get("time_tension_bucket", 0)),
                float(row.get("session_duration", 0)) / 3600.0,
                float(row.get("event_count", 0)) / 100.0,
            ]
            # 填充到 256 维
            while len(vector) < 256:
                vector.append(0.0)
            vectors.append(vector[:256])

        return torch.tensor(vectors, dtype=torch.float32)

    def _extract_labels(self) -> torch.Tensor:
        """提取标签"""
        labels = []
        for _, row in self.df.iterrows():
            label = int(row.get("proxy_label", 0))
            labels.append(label)

        return torch.tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        return self.vectors[idx], self.labels[idx]


def train_supcon_model_cpu(
    train_data_path: str,
    val_data_path: str = None,
    model_save_path: str = None,
    epochs: int = 30,
    batch_size: int = 16,
    learning_rate: float = 0.001,
    temperature: float = 0.07,
):
    """
    CPU 训练 SupCon 模型

    Args:
        train_data_path: 训练数据路径
        val_data_path: 验证数据路径（可选）
        model_save_path: 模型保存路径
        epochs: 训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
        temperature: SupCon 温度参数
    """
    print("=" * 60)
    print("SupCon 模型训练（CPU）")
    print("=" * 60)

    # 强制使用 CPU
    device = torch.device("cpu")
    print(f"\n设备：{device}")

    # 数据加载
    print(f"\n加载训练数据：{train_data_path}")
    train_dataset = SupConDataset(train_data_path)
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=4,  # CPU 多线程加速
        pin_memory=False,  # CPU 不需要 pin_memory
    )
    print(f"训练样本数：{len(train_dataset)}")

    # 验证数据（可选）
    val_loader = None
    if val_data_path:
        print(f"加载验证数据：{val_data_path}")
        val_dataset = SupConDataset(val_data_path)
        val_loader = DataLoader(
            val_dataset, batch_size=batch_size, shuffle=False, num_workers=4
        )
        print(f"验证样本数：{len(val_dataset)}")

    # 模型初始化（轻量级）
    print("\n创建 Projection Head...")
    model = create_projection_head(input_dim=256, hidden_dim=128, output_dim=128).to(device)

    # 损失函数和优化器
    criterion = SupConLoss(temperature=temperature)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    # 训练循环
    print(f"\n开始训练（{epochs} epochs）...")
    best_val_loss = float("inf")

    for epoch in range(epochs):
        # 训练阶段
        model.train()
        train_loss = 0.0

        for batch_idx, (vectors, labels) in enumerate(train_loader):
            vectors = vectors.to(device)
            labels = labels.to(device)

            # Forward
            projections = model(vectors)
            loss = criterion(projections, labels)

            # Backward
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

            # 每 10 个 batch 打印一次（CPU 训练慢）
            if (batch_idx + 1) % 10 == 0:
                print(
                    f"  Epoch {epoch+1}/{epochs}, Batch {batch_idx+1}/{len(train_loader)}, Loss: {loss.item():.4f}"
                )

        avg_train_loss = train_loss / len(train_loader)

        # 验证阶段
        val_loss_str = ""
        if val_loader:
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for vectors, labels in val_loader:
                    vectors = vectors.to(device)
                    labels = labels.to(device)

                    projections = model(vectors)
                    loss = criterion(projections, labels)
                    val_loss += loss.item()

            avg_val_loss = val_loss / len(val_loader)
            val_loss_str = f", Val Loss: {avg_val_loss:.4f}"

            # 保存最佳模型
            if avg_val_loss < best_val_loss:
                best_val_loss = avg_val_loss
                if model_save_path:
                    torch.save(model.state_dict(), model_save_path)
                    print(f"  → 保存最佳模型（Val Loss: {avg_val_loss:.4f}）")

        print(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.4f}{val_loss_str}")

    # 保存最终模型
    if model_save_path and not val_loader:
        torch.save(model.state_dict(), model_save_path)
        print(f"\n模型已保存到：{model_save_path}")

    print("\n训练完成！")
    return model


def main():
    """主函数"""
    # 训练数据路径
    train_data_path = PROJECT_ROOT / "data" / "processed" / "labeled_sessions_sample.csv"
    model_save_path = PROJECT_ROOT / "data" / "models" / "supcon_model.pth"

    # 确保模型目录存在
    model_save_path.parent.mkdir(parents=True, exist_ok=True)

    # 训练模型
    model = train_supcon_model_cpu(
        train_data_path=str(train_data_path),
        model_save_path=str(model_save_path),
        epochs=30,
        batch_size=16,
        learning_rate=0.001,
        temperature=0.07,
    )


if __name__ == "__main__":
    main()
