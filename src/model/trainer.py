"""SupCon 模型训练脚本（CPU 优化）

使用 Supervised Contrastive Loss 训练 Projection Head。
基于二分类 lead/non-lead 标签进行对比学习。
"""

import sys
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import pandas as pd
import numpy as np

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.model.projection_head import create_projection_head
from src.model.supcon_loss import SupConLoss


class SupConDataset(Dataset):
    """SupCon 训练数据集 - 基于二分类 lead/non-lead 标签"""

    def __init__(self, data_path: str):
        """
        初始化数据集

        Args:
            data_path: 数据文件路径（CSV 格式，设备级别数据）
        """
        self.df = pd.read_csv(data_path)

        # 提取特征和标签
        self.vectors = self._extract_vectors()
        self.labels = self._extract_lead_labels()

        # 统计标签分布
        self._print_label_distribution()

    def _extract_vectors(self) -> torch.Tensor:
        """提取设备特征向量（256-dim）"""
        vectors = []
        for _, row in self.df.iterrows():
            # 使用 urgency_level 替代 urgency_score
            urgency_value = self._urgency_level_to_float(row.get("urgency_level", "low"))

            vector = [
                float(row.get("session_count", 0)) / 100.0,  # 归一化 session 数量
                float(row.get("total_duration", 0)) / 3600.0,  # 归一化总时长（小时）
                urgency_value,  # 归一化紧急度
            ]
            # 填充到 256 维
            while len(vector) < 256:
                vector.append(0.0)
            vectors.append(vector[:256])

        return torch.tensor(vectors, dtype=torch.float32)

    def _urgency_level_to_float(self, urgency_level: str) -> float:
        """将 urgency_level 转换为浮点数"""
        mapping = {"high": 1.0, "medium": 0.5, "low": 0.0}
        return mapping.get(str(urgency_level).lower(), 0.0)

    def _extract_lead_labels(self) -> torch.Tensor:
        """提取二分类 lead/non-lead 标签"""
        labels = []
        for _, row in self.df.iterrows():
            # 优先使用 is_lead 列，如果不存在则从 proxy_label 转换
            if "is_lead" in self.df.columns:
                is_lead = int(row.get("is_lead", 0))
            else:
                # 从 proxy_label 转换：Label 3 → 1 (lead), 其他 → 0 (non-lead)
                proxy_label = int(row.get("proxy_label", 0))
                is_lead = 1 if proxy_label == 3 else 0

            labels.append(is_lead)

        return torch.tensor(labels, dtype=torch.long)

    def _print_label_distribution(self):
        """打印标签分布"""
        unique, counts = torch.unique(self.labels, return_counts=True)
        print("\n标签分布：")
        for label, count in zip(unique.tolist(), counts.tolist()):
            label_name = "Lead" if label == 1 else "Non-lead"
            percentage = count / len(self.labels) * 100
            print(f"  {label_name} (label={label}): {count} ({percentage:.2f}%)")

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
    use_balanced_sampling: bool = True,
):
    """
    CPU 训练 SupCon 模型（使用二分类 lead/non-lead 标签）

    Args:
        train_data_path: 训练数据路径
        val_data_path: 验证数据路径（可选）
        model_save_path: 模型保存路径
        epochs: 训练轮数
        batch_size: 批次大小
        learning_rate: 学习率
        temperature: SupCon 温度参数
        use_balanced_sampling: 是否使用平衡采样（确保每个 batch 中 lead/non-lead 比例均衡）
    """
    print("=" * 60)
    print("SupCon 模型训练（CPU）- 二分类 Lead/Non-lead")
    print("=" * 60)

    # 强制使用 CPU
    device = torch.device("cpu")
    print(f"\n设备：{device}")

    # 数据加载
    print(f"\n加载训练数据：{train_data_path}")
    train_dataset = SupConDataset(train_data_path)

    # 创建平衡采样器（可选）
    sampler = None
    if use_balanced_sampling:
        print("\n使用平衡采样器（确保 lead/non-lead 比例均衡）...")
        # 计算每个类别的权重
        labels = train_dataset.labels.numpy()
        class_counts = np.bincount(labels)
        class_weights = 1.0 / class_counts
        sample_weights = class_weights[labels]

        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True
        )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=(sampler is None),  # 如果使用 sampler 则不 shuffle
        sampler=sampler,
        num_workers=4,  # CPU 多线程加速
        pin_memory=False,  # CPU 不需要 pin_memory
    )
    print(f"训练样本数：{len(train_dataset)}")

    # 验证数据（可选）
    val_loader = None
    if val_data_path:
        print(f"\n加载验证数据：{val_data_path}")
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
