"""知识蒸馏损失函数

Student Model 学习 Teacher Model（LLM）的输出。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class IntentDistillationLoss(nn.Module):
    """
    知识蒸馏损失：Student 学习 Teacher (LLM) 的输出

    损失包含两部分：
    1. 多标签分类损失（BCE Loss）
    2. 向量蒸馏损失（MSE Loss）
    """

    def __init__(self, alpha: float = 0.5):
        """
        初始化蒸馏损失

        Args:
            alpha: 分类损失权重（1-alpha 为向量损失权重）
        """
        super(IntentDistillationLoss, self).__init__()
        self.alpha = alpha
        self.bce_loss = nn.BCELoss()
        self.mse_loss = nn.MSELoss()

    def forward(
        self,
        student_probs: torch.Tensor,  # Student 的意图概率 [B, 11]
        student_embedding: torch.Tensor,  # Student 的意图向量 [B, 128]
        teacher_probs: torch.Tensor,  # Teacher (LLM) 的意图概率 [B, 11]
        teacher_embedding: torch.Tensor,  # Teacher (LLM) 的意图向量 [B, 128]
    ) -> torch.Tensor:
        """
        计算蒸馏损失

        Args:
            student_probs: Student 的意图概率
            student_embedding: Student 的意图向量
            teacher_probs: Teacher 的意图概率
            teacher_embedding: Teacher 的意图向量

        Returns:
            总损失
        """
        # 1. 多标签分类损失
        classification_loss = self.bce_loss(student_probs, teacher_probs)

        # 2. 向量蒸馏损失
        embedding_loss = self.mse_loss(student_embedding, teacher_embedding)

        # 总损失
        total_loss = self.alpha * classification_loss + (1 - self.alpha) * embedding_loss

        return total_loss

    def get_loss_components(
        self,
        student_probs: torch.Tensor,
        student_embedding: torch.Tensor,
        teacher_probs: torch.Tensor,
        teacher_embedding: torch.Tensor,
    ) -> dict:
        """
        获取损失各组成部分（用于监控）

        Returns:
            损失字典
        """
        classification_loss = self.bce_loss(student_probs, teacher_probs)
        embedding_loss = self.mse_loss(student_embedding, teacher_embedding)
        total_loss = self.alpha * classification_loss + (1 - self.alpha) * embedding_loss

        return {
            "total_loss": total_loss.item(),
            "classification_loss": classification_loss.item(),
            "embedding_loss": embedding_loss.item(),
        }


if __name__ == "__main__":
    # 测试损失函数
    print("=" * 60)
    print("测试知识蒸馏损失函数")
    print("=" * 60)

    # 创建损失函数
    criterion = IntentDistillationLoss(alpha=0.5)

    # 模拟数据
    batch_size = 4
    student_probs = torch.rand(batch_size, 11)
    student_embedding = torch.randn(batch_size, 128)
    teacher_probs = torch.rand(batch_size, 11)
    teacher_embedding = torch.randn(batch_size, 128)

    # 计算损失
    loss = criterion(student_probs, student_embedding, teacher_probs, teacher_embedding)

    print(f"\n总损失：{loss.item():.4f}")

    # 获取损失组成部分
    loss_components = criterion.get_loss_components(
        student_probs, student_embedding, teacher_probs, teacher_embedding
    )

    print("\n损失组成部分：")
    for key, value in loss_components.items():
        print(f"  {key}: {value:.4f}")
