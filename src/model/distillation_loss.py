"""知识蒸馏损失函数

Student Model 学习 Teacher Model（LLM）的输出。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class IntentDistillationLoss(nn.Module):
    """
    知识蒸馏损失：Student 学习 Teacher (LLM) 的输出

    损失只包含多标签分类损失（BCE Loss）。
    Teacher 不再生成 embedding，Student 的 embedding 通过分类任务自行学习。
    """

    def __init__(self):
        """初始化蒸馏损失"""
        super(IntentDistillationLoss, self).__init__()
        self.bce_loss = nn.BCELoss()

    def forward(
        self,
        student_probs: torch.Tensor,  # Student 的意图概率 [B, 11]
        teacher_probs: torch.Tensor,  # Teacher (LLM) 的意图概率 [B, 11]
    ) -> torch.Tensor:
        """
        计算蒸馏损失

        Args:
            student_probs: Student 的意图概率
            teacher_probs: Teacher 的意图概率

        Returns:
            分类损失
        """
        # 多标签分类损失
        classification_loss = self.bce_loss(student_probs, teacher_probs)

        return classification_loss

    def get_loss_components(
        self,
        student_probs: torch.Tensor,
        teacher_probs: torch.Tensor,
    ) -> dict:
        """
        获取损失各组成部分（用于监控）

        Returns:
            损失字典
        """
        classification_loss = self.bce_loss(student_probs, teacher_probs)

        return {
            "total_loss": classification_loss.item(),
            "classification_loss": classification_loss.item(),
        }


if __name__ == "__main__":
    # 测试损失函数
    print("=" * 60)
    print("测试知识蒸馏损失函数")
    print("=" * 60)

    # 创建损失函数
    criterion = IntentDistillationLoss()

    # 模拟数据
    batch_size = 4
    student_probs = torch.rand(batch_size, 11)
    teacher_probs = torch.rand(batch_size, 11)

    # 计算损失
    loss = criterion(student_probs, teacher_probs)

    print(f"\n总损失：{loss.item():.4f}")

    # 获取损失组成部分
    loss_components = criterion.get_loss_components(student_probs, teacher_probs)

    print("\n损失组成部分：")
    for key, value in loss_components.items():
        print(f"  {key}: {value:.4f}")
