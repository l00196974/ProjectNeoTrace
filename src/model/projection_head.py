"""Projection Head 网络

将融合向量（256-dim）映射到对比学习空间（128-dim）。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ProjectionHead(nn.Module):
    """
    极度简化的 Projection Head（CPU 优化）

    参数量：~30K（原设计 ~200K）
    """

    def __init__(self, input_dim: int = 256, hidden_dim: int = 128, output_dim: int = 128):
        """
        初始化 Projection Head

        Args:
            input_dim: 输入维度
            hidden_dim: 隐藏层维度
            output_dim: 输出维度
        """
        super(ProjectionHead, self).__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim

        # 只用 2 层 MLP（去掉 BatchNorm 加速 CPU 推理）
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        """
        前向传播

        Args:
            x: 输入向量 [batch_size, input_dim]

        Returns:
            输出向量 [batch_size, output_dim]（L2 归一化）
        """
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return F.normalize(x, p=2, dim=1)

    def count_parameters(self):
        """计算模型参数量"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def create_projection_head(
    input_dim: int = 256, hidden_dim: int = 128, output_dim: int = 128
) -> ProjectionHead:
    """
    创建 Projection Head

    Args:
        input_dim: 输入维度
        hidden_dim: 隐藏层维度
        output_dim: 输出维度

    Returns:
        Projection Head 实例
    """
    model = ProjectionHead(input_dim=input_dim, hidden_dim=hidden_dim, output_dim=output_dim)

    print(f"Projection Head 参数量：{model.count_parameters():,}")

    return model


if __name__ == "__main__":
    # 测试模型
    print("=" * 60)
    print("测试 Projection Head")
    print("=" * 60)

    # 创建模型
    model = create_projection_head()

    # 测试前向传播
    batch_size = 4
    x = torch.randn(batch_size, 256)

    output = model(x)

    print(f"\n输入形状：{x.shape}")
    print(f"输出形状：{output.shape}")
    print(f"输出示例（前 10 维）：{output[0][:10]}")

    # 验证 L2 归一化
    norms = torch.norm(output, p=2, dim=1)
    print(f"\nL2 范数（应该全为 1.0）：{norms}")
