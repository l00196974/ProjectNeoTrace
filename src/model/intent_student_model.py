"""轻量级 Student Model - 意图预测

用于在线推理，替代 Teacher Model（LLM）。

模型特点：
- 参数量 < 50K（极度轻量）
- CPU 推理 < 1ms
- 输出：11-dim 意图概率 + 128-dim 意图向量
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class IntentStudentModel(nn.Module):
    """
    轻量级意图预测模型（CPU 优化）

    输入：Session 特征（256-dim）
    输出：
      1. 多意图概率分布（11-dim）
      2. 意图向量（128-dim，用于融合）
    """

    def __init__(
        self,
        input_dim: int = 256,
        hidden_dim: int = 64,  # 减小隐藏层（CPU 优化）
        intent_dim: int = 11,
        embedding_dim: int = 128,
        dropout: float = 0.2,
    ):
        """
        初始化 Student Model

        Args:
            input_dim: 输入维度
            hidden_dim: 隐藏层维度
            intent_dim: 意图类别数量
            embedding_dim: 意图向量维度
            dropout: Dropout 比例
        """
        super(IntentStudentModel, self).__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.intent_dim = intent_dim
        self.embedding_dim = embedding_dim

        # 特征编码器（2 层 MLP，去掉 BatchNorm）
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        # 多标签分类头
        self.intent_classifier = nn.Linear(hidden_dim, intent_dim)

        # 意图向量投影头
        self.intent_projector = nn.Sequential(
            nn.Linear(hidden_dim, embedding_dim),
            nn.ReLU(),
            nn.Linear(embedding_dim, embedding_dim),
        )

    def forward(self, x):
        """
        前向传播

        Args:
            x: 输入特征 [batch_size, input_dim]

        Returns:
            intent_probs: 意图概率 [batch_size, intent_dim]
            intent_embedding: 意图向量 [batch_size, embedding_dim]
        """
        # 特征编码
        features = self.encoder(x)

        # 多标签分类（sigmoid）
        intent_logits = self.intent_classifier(features)
        intent_probs = torch.sigmoid(intent_logits)

        # 意图向量（L2 归一化）
        intent_embedding = self.intent_projector(features)
        intent_embedding = F.normalize(intent_embedding, p=2, dim=1)

        return intent_probs, intent_embedding

    def count_parameters(self):
        """计算模型参数量"""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def create_student_model(
    input_dim: int = 256,
    hidden_dim: int = 64,
    intent_dim: int = 11,
    embedding_dim: int = 128,
    dropout: float = 0.2,
) -> IntentStudentModel:
    """
    创建 Student Model

    Args:
        input_dim: 输入维度
        hidden_dim: 隐藏层维度
        intent_dim: 意图类别数量
        embedding_dim: 意图向量维度
        dropout: Dropout 比例

    Returns:
        Student Model 实例
    """
    model = IntentStudentModel(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        intent_dim=intent_dim,
        embedding_dim=embedding_dim,
        dropout=dropout,
    )

    print(f"Student Model 参数量：{model.count_parameters():,}")

    return model


if __name__ == "__main__":
    # 测试模型
    print("=" * 60)
    print("测试 Student Model")
    print("=" * 60)

    # 创建模型
    model = create_student_model()

    # 测试前向传播
    batch_size = 4
    x = torch.randn(batch_size, 256)

    intent_probs, intent_embedding = model(x)

    print(f"\n输入形状：{x.shape}")
    print(f"意图概率形状：{intent_probs.shape}")
    print(f"意图向量形状：{intent_embedding.shape}")
    print(f"\n意图概率示例：{intent_probs[0]}")
    print(f"意图向量示例（前 10 维）：{intent_embedding[0][:10]}")
