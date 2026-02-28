"""Supervised Contrastive Loss

SupCon Loss 用于对比学习，让同标签样本聚集，异标签样本推开。

参考论文：Supervised Contrastive Learning (Khosla et al., 2020)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class SupConLoss(nn.Module):
    """
    Supervised Contrastive Loss

    让同标签样本在向量空间中聚集，异标签样本推开。
    """

    def __init__(self, temperature: float = 0.07):
        """
        初始化 SupCon Loss

        Args:
            temperature: 温度参数，控制分布的平滑度
        """
        super(SupConLoss, self).__init__()
        self.temperature = temperature

    def forward(self, features: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        """
        计算 SupCon Loss

        Args:
            features: 特征向量 [batch_size, feature_dim]
            labels: 标签 [batch_size]

        Returns:
            损失值
        """
        # 1. L2 Normalize
        features = F.normalize(features, p=2, dim=1)

        # 2. Compute Similarity Matrix
        logits = torch.div(torch.matmul(features, features.T), self.temperature)

        # 3. Create Label Mask (Find same label pairs)
        labels = labels.view(-1, 1)
        mask = torch.eq(labels, labels.T).float().to(features.device)

        # 4. Remove self-contrast
        logits_mask = torch.ones_like(mask) - torch.eye(features.shape[0]).to(
            features.device
        )
        mask = mask * logits_mask

        # 5. Compute Log Probability with Hard Negative Mining
        exp_logits = torch.exp(logits) * logits_mask
        log_prob = logits - torch.log(exp_logits.sum(1, keepdim=True))

        # 6. Mean Log Prob of Positive Pairs
        # 避免除以 0
        mask_sum = mask.sum(1)
        mask_sum = torch.where(mask_sum == 0, torch.ones_like(mask_sum), mask_sum)

        loss = -(mask * log_prob).sum(1) / mask_sum
        return loss.mean()


if __name__ == "__main__":
    # 测试损失函数
    print("=" * 60)
    print("测试 SupCon Loss")
    print("=" * 60)

    # 创建损失函数
    criterion = SupConLoss(temperature=0.07)

    # 模拟数据
    batch_size = 8
    feature_dim = 128
    features = torch.randn(batch_size, feature_dim)
    labels = torch.tensor([0, 0, 1, 1, 2, 2, 3, 3])  # 4 个类别，每类 2 个样本

    # 计算损失
    loss = criterion(features, labels)

    print(f"\nBatch size: {batch_size}")
    print(f"Feature dim: {feature_dim}")
    print(f"Labels: {labels.tolist()}")
    print(f"Loss: {loss.item():.4f}")

    # 测试边界情况：所有样本同一标签
    print("\n测试边界情况：所有样本同一标签")
    labels_same = torch.zeros(batch_size, dtype=torch.long)
    loss_same = criterion(features, labels_same)
    print(f"Loss (all same label): {loss_same.item():.4f}")

    # 测试边界情况：所有样本不同标签
    print("\n测试边界情况：所有样本不同标签")
    labels_diff = torch.arange(batch_size)
    loss_diff = criterion(features, labels_diff)
    print(f"Loss (all different labels): {loss_diff.item():.4f}")
