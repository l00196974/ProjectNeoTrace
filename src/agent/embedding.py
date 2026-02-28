"""文本向量化模块

使用 BGE-m3 模型进行文本向量化。
"""

from typing import List
import numpy as np


class TextEmbedding:
    """文本向量化器"""

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu"):
        """
        初始化向量化器

        Args:
            model_name: 模型名称
            device: 设备（cpu 或 cuda）
        """
        self.model_name = model_name
        self.device = device
        self.model = None

    def _load_model(self):
        """延迟加载模型"""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer

                print(f"加载向量化模型：{self.model_name}")
                self.model = SentenceTransformer(self.model_name, device=self.device)
                print("模型加载完成")
            except ImportError:
                raise ImportError(
                    "请安装 sentence-transformers 库：pip install sentence-transformers"
                )

    def encode(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        将文本转换为向量

        Args:
            text: 输入文本
            normalize: 是否归一化

        Returns:
            向量（1024-dim，BGE-m3 原始维度）
        """
        self._load_model()

        # 编码
        embedding = self.model.encode(text, normalize_embeddings=normalize)

        return embedding

    def encode_batch(
        self, texts: List[str], normalize: bool = True, batch_size: int = 32
    ) -> np.ndarray:
        """
        批量将文本转换为向量

        Args:
            texts: 文本列表
            normalize: 是否归一化
            batch_size: 批次大小

        Returns:
            向量矩阵（N x 1024）
        """
        self._load_model()

        # 批量编码
        embeddings = self.model.encode(
            texts, normalize_embeddings=normalize, batch_size=batch_size, show_progress_bar=True
        )

        return embeddings

    def reduce_dimension(self, embedding: np.ndarray, target_dim: int = 128) -> np.ndarray:
        """
        降维（简单截取前 N 维）

        Args:
            embedding: 原始向量
            target_dim: 目标维度

        Returns:
            降维后的向量
        """
        if len(embedding.shape) == 1:
            # 单个向量
            return embedding[:target_dim]
        else:
            # 批量向量
            return embedding[:, :target_dim]


class MockTextEmbedding:
    """Mock 文本向量化器（用于测试）"""

    def __init__(self, model_name: str = "mock", device: str = "cpu"):
        """初始化 Mock 向量化器"""
        self.model_name = model_name
        self.device = device

    def encode(self, text: str, normalize: bool = True) -> np.ndarray:
        """返回模拟向量"""
        import random

        random.seed(hash(text) % (2**32))
        embedding = np.array([random.random() for _ in range(1024)])

        if normalize:
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

        return embedding

    def encode_batch(
        self, texts: List[str], normalize: bool = True, batch_size: int = 32
    ) -> np.ndarray:
        """批量返回模拟向量"""
        embeddings = [self.encode(text, normalize) for text in texts]
        return np.array(embeddings)

    def reduce_dimension(self, embedding: np.ndarray, target_dim: int = 128) -> np.ndarray:
        """降维"""
        if len(embedding.shape) == 1:
            return embedding[:target_dim]
        else:
            return embedding[:, :target_dim]


def create_text_embedding(
    model_name: str = "BAAI/bge-m3", device: str = "cpu", use_mock: bool = False
) -> TextEmbedding:
    """
    创建文本向量化器

    Args:
        model_name: 模型名称
        device: 设备
        use_mock: 是否使用 Mock 模型

    Returns:
        文本向量化器实例
    """
    if use_mock:
        return MockTextEmbedding(model_name, device)
    else:
        return TextEmbedding(model_name, device)
