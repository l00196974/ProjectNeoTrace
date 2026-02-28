"""在线推理逻辑

集成 Student Model + SupCon Model 进行在线推理。
"""

import sys
from pathlib import Path
import torch
import numpy as np
from typing import Dict, List

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.model.intent_student_model import IntentStudentModel
from src.model.projection_head import ProjectionHead
from src.agent.embedding import create_text_embedding


class ProductionInference:
    """生产环境推理（CPU）"""

    def __init__(
        self,
        student_model_path: str,
        supcon_model_path: str,
        use_mock_embedding: bool = False,
    ):
        """
        初始化推理引擎

        Args:
            student_model_path: Student Model 路径
            supcon_model_path: SupCon Model 路径
            use_mock_embedding: 是否使用 Mock 向量化器
        """
        self.device = torch.device("cpu")

        # 加载 Student Model
        print(f"加载 Student Model：{student_model_path}")
        self.student_model = IntentStudentModel(
            input_dim=256, hidden_dim=64, intent_dim=11, embedding_dim=128
        ).to(self.device)

        try:
            self.student_model.load_state_dict(torch.load(student_model_path, map_location=self.device))
            self.student_model.eval()
            print("Student Model 加载成功")
        except Exception as e:
            print(f"警告：无法加载 Student Model（{e}），使用未训练模型")

        # 加载 SupCon Model
        print(f"加载 SupCon Model：{supcon_model_path}")
        self.supcon_model = ProjectionHead(input_dim=256, hidden_dim=128, output_dim=128).to(
            self.device
        )

        try:
            self.supcon_model.load_state_dict(torch.load(supcon_model_path, map_location=self.device))
            self.supcon_model.eval()
            print("SupCon Model 加载成功")
        except Exception as e:
            print(f"警告：无法加载 SupCon Model（{e}），使用未训练模型")

        # 文本向量化器
        self.text_embedding = create_text_embedding(use_mock=use_mock_embedding)

        # Label 3 中心向量（用于计算 lead_score）
        # 这个向量应该在训练后从训练数据中计算得出
        # 这里使用随机初始化作为占位符
        self.label_3_center = torch.randn(128).to(self.device)
        self.label_3_center = torch.nn.functional.normalize(self.label_3_center, p=2, dim=0)

    def get_combined_vector(
        self, session_text: str, session_features: np.ndarray
    ) -> np.ndarray:
        """
        生成融合向量（256-dim）

        流程：
        1. 文本向量：BGE-m3(session_text) → 128-dim
        2. 意图向量：Student Model(session_features) → 128-dim
        3. 融合：Concat(文本向量, 意图向量) → 256-dim

        Args:
            session_text: Session 文本描述
            session_features: Session 特征（256-dim）

        Returns:
            融合向量（256-dim）
        """
        with torch.no_grad():
            # 1. 文本向量（BGE-m3 CPU）
            text_embedding = self.text_embedding.encode(session_text, normalize=True)
            text_embedding_128 = self.text_embedding.reduce_dimension(
                text_embedding, target_dim=128
            )

            # 2. 意图向量（Student Model CPU）
            x = torch.tensor(session_features, dtype=torch.float32).unsqueeze(0).to(self.device)
            _, intent_embedding = self.student_model(x)
            intent_embedding = intent_embedding.cpu().numpy()[0]  # [128-dim]

            # 3. 融合
            combined_vector = np.concatenate([text_embedding_128, intent_embedding])

            return combined_vector  # [256-dim]

    def predict_lead_score(
        self, session_text: str, session_features: np.ndarray
    ) -> Dict:
        """
        预测 lead_score

        Args:
            session_text: Session 文本描述
            session_features: Session 特征（256-dim）

        Returns:
            预测结果字典
        """
        with torch.no_grad():
            # 1. 生成融合向量
            combined_vector = self.get_combined_vector(session_text, session_features)

            # 2. SupCon 模型推理
            x = torch.tensor(combined_vector, dtype=torch.float32).unsqueeze(0).to(self.device)
            projection = self.supcon_model(x)
            projection = projection.squeeze(0)  # [128-dim]

            # 3. 计算与 Label 3 中心的相似度（作为 lead_score）
            similarity = torch.cosine_similarity(
                projection.unsqueeze(0), self.label_3_center.unsqueeze(0)
            )
            lead_score = (similarity.item() + 1) / 2  # 归一化到 [0, 1]

            # 4. 获取意图概率
            x_features = torch.tensor(session_features, dtype=torch.float32).unsqueeze(0).to(
                self.device
            )
            intent_probs, _ = self.student_model(x_features)
            intent_probs = intent_probs.squeeze(0).cpu().numpy()

            return {
                "lead_score": float(lead_score),
                "intent_probs": intent_probs.tolist(),
                "projection": projection.cpu().numpy().tolist(),
            }


def main():
    """测试函数"""
    print("=" * 60)
    print("测试在线推理")
    print("=" * 60)

    # 模型路径
    student_model_path = PROJECT_ROOT / "data" / "models" / "intent_student_model.pth"
    supcon_model_path = PROJECT_ROOT / "data" / "models" / "supcon_model.pth"

    # 创建推理引擎
    print("\n创建推理引擎...")
    inference = ProductionInference(
        student_model_path=str(student_model_path),
        supcon_model_path=str(supcon_model_path),
        use_mock_embedding=True,  # 使用 Mock 向量化器
    )

    # 测试数据
    session_text = "用户在 5 分钟 内，使用了汽车之家，在配置页停留了 3 分钟，位置：汽车市场。"
    session_features = np.random.randn(256)  # 模拟特征

    # 预测
    print("\n预测 lead_score...")
    result = inference.predict_lead_score(session_text, session_features)

    print(f"\nSession 文本：{session_text}")
    print(f"Lead Score：{result['lead_score']:.4f}")
    print(f"意图概率（前 5 个）：{result['intent_probs'][:5]}")


if __name__ == "__main__":
    main()
