"""SupCon 训练测试（二分类版本）

测试 SupCon 模型使用二分类 lead/non-lead 标签进行训练。
"""
import pytest
import torch
import pandas as pd
import numpy as np
import sys
from pathlib import Path
import tempfile

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.model.trainer import SupConDataset
from src.model.supcon_loss import SupConLoss


class TestSupConDatasetBinaryLabels:
    """测试 SupCon 数据集（二分类标签）"""

    def test_dataset_binary_labels(self):
        """测试数据集使用二分类 lead/non-lead 标签"""
        # 创建临时 CSV 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,proxy_label,is_lead\n")
            f.write("device_001,10,3600,high,3,1\n")  # Lead
            f.write("device_002,5,1800,medium,2,0\n")  # Non-lead
            f.write("device_003,3,900,low,1,0\n")  # Non-lead
            temp_path = f.name

        try:
            dataset = SupConDataset(temp_path)

            # 验证数据集大小
            assert len(dataset) == 3

            # 验证标签是二分类（0 或 1）
            for i in range(len(dataset)):
                _, label = dataset[i]
                assert label.item() in [0, 1], f"标签应该是 0 或 1，实际是 {label.item()}"

        finally:
            Path(temp_path).unlink()

    def test_dataset_label_conversion(self):
        """测试从 proxy_label 转换为 is_lead"""
        # 创建临时 CSV 文件（只有 proxy_label，没有 is_lead）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,proxy_label\n")
            f.write("device_001,10,3600,high,3\n")  # Label 3 -> is_lead = 1
            f.write("device_002,5,1800,medium,2\n")  # Label 2 -> is_lead = 0
            f.write("device_003,3,900,low,1\n")  # Label 1 -> is_lead = 0
            f.write("device_004,2,600,low,0\n")  # Label 0 -> is_lead = 0
            temp_path = f.name

        try:
            dataset = SupConDataset(temp_path)

            # 验证标签转换
            _, label_0 = dataset[0]
            _, label_1 = dataset[1]
            _, label_2 = dataset[2]
            _, label_3 = dataset[3]

            assert label_0.item() == 1, "proxy_label=3 应该转换为 is_lead=1"
            assert label_1.item() == 0, "proxy_label=2 应该转换为 is_lead=0"
            assert label_2.item() == 0, "proxy_label=1 应该转换为 is_lead=0"
            assert label_3.item() == 0, "proxy_label=0 应该转换为 is_lead=0"

        finally:
            Path(temp_path).unlink()

    def test_dataset_label_distribution(self):
        """测试数据集打印标签分布"""
        # 创建临时 CSV 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,is_lead\n")
            # 10 个 lead, 90 个 non-lead（不平衡）
            for i in range(10):
                f.write(f"device_{i:03d},10,3600,high,1\n")
            for i in range(10, 100):
                f.write(f"device_{i:03d},5,1800,low,0\n")
            temp_path = f.name

        try:
            # 数据集初始化时会打印标签分布
            dataset = SupConDataset(temp_path)

            # 验证标签分布
            labels = dataset.labels.numpy()
            unique, counts = np.unique(labels, return_counts=True)

            assert len(unique) == 2, "应该有 2 个类别"
            assert 1 in unique, "应该有 lead 类别"
            assert 0 in unique, "应该有 non-lead 类别"

            # 验证比例
            lead_count = counts[unique == 1][0]
            non_lead_count = counts[unique == 0][0]
            assert lead_count == 10
            assert non_lead_count == 90

        finally:
            Path(temp_path).unlink()

    def test_dataset_urgency_level_feature(self):
        """测试数据集使用 urgency_level 而不是 urgency_score"""
        # 创建临时 CSV 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,is_lead\n")
            f.write("device_001,10,3600,high,1\n")
            f.write("device_002,5,1800,medium,0\n")
            f.write("device_003,3,900,low,0\n")
            temp_path = f.name

        try:
            dataset = SupConDataset(temp_path)

            # 验证特征提取使用 urgency_level
            vectors, _ = dataset[0]
            assert vectors.shape == (256,), "特征应该是 256 维"

            # urgency_level 应该被转换为数值（high=1.0, medium=0.5, low=0.0）
            # 特征的第 3 个元素（索引 2）是 urgency_level
            assert vectors[2].item() == 1.0, "high 应该转换为 1.0"

            vectors_medium, _ = dataset[1]
            assert vectors_medium[2].item() == 0.5, "medium 应该转换为 0.5"

            vectors_low, _ = dataset[2]
            assert vectors_low[2].item() == 0.0, "low 应该转换为 0.0"

        finally:
            Path(temp_path).unlink()


class TestSupConLossBinaryLabels:
    """测试 SupConLoss 使用二分类标签"""

    def test_supcon_loss_binary_labels(self):
        """测试 SupConLoss 可以处理二分类标签"""
        loss_fn = SupConLoss(temperature=0.07)

        # 创建测试数据（二分类标签）
        features = torch.randn(8, 128)
        labels = torch.tensor([0, 0, 0, 0, 1, 1, 1, 1])  # 4 个 non-lead, 4 个 lead

        # 计算损失
        loss = loss_fn(features, labels)

        # 验证损失
        assert isinstance(loss, torch.Tensor)
        assert loss.item() >= 0
        assert not torch.isnan(loss)

    def test_supcon_loss_lead_clustering(self):
        """测试 SupConLoss 促进 lead 用户聚类"""
        loss_fn = SupConLoss(temperature=0.07)

        # 创建测试数据：lead 用户的特征接近，non-lead 用户的特征接近
        lead_features = torch.tensor([
            [1.0, 0.0, 0.0],
            [0.99, 0.01, 0.0],
            [0.98, 0.02, 0.0],
        ], dtype=torch.float32)

        non_lead_features = torch.tensor([
            [-1.0, 0.0, 0.0],
            [-0.99, 0.01, 0.0],
            [-0.98, 0.02, 0.0],
        ], dtype=torch.float32)

        features = torch.cat([lead_features, non_lead_features], dim=0)
        labels = torch.tensor([1, 1, 1, 0, 0, 0])

        # 计算损失
        loss = loss_fn(features, labels)

        # 由于同类样本已经很接近，损失应该较小
        assert loss.item() < 2.0, f"同类聚集的损失应该较小，实际损失：{loss.item()}"

    def test_supcon_loss_lead_separation(self):
        """测试 SupConLoss 促进 lead 和 non-lead 分离"""
        loss_fn = SupConLoss(temperature=0.07)

        # 创建测试数据：lead 和 non-lead 用户的特征混在一起
        features = torch.tensor([
            [1.0, 0.0, 0.0],   # lead
            [0.99, 0.01, 0.0], # non-lead（接近 lead）
            [-1.0, 0.0, 0.0],  # non-lead
            [-0.99, 0.01, 0.0],# lead（接近 non-lead）
        ], dtype=torch.float32)

        labels = torch.tensor([1, 0, 0, 1])

        # 计算损失
        loss = loss_fn(features, labels)

        # 由于不同类样本混在一起，损失应该较大
        assert loss.item() > 0.5, f"混合样本的损失应该较大，实际损失：{loss.item()}"


class TestBalancedSampling:
    """测试平衡采样"""

    def test_balanced_sampling_concept(self):
        """测试平衡采样的概念（不实际运行训练）"""
        # 创建不平衡的标签分布
        labels = np.array([0] * 90 + [1] * 10)  # 90% non-lead, 10% lead

        # 计算类别权重
        unique, counts = np.unique(labels, return_counts=True)
        class_weights = 1.0 / counts

        # 验证权重计算
        assert class_weights[0] < class_weights[1], "少数类应该有更高的权重"

        # 计算样本权重
        sample_weights = class_weights[labels]

        # 验证样本权重
        assert np.all(sample_weights[labels == 1] > sample_weights[labels == 0]), \
            "lead 样本应该有更高的权重"

    def test_weighted_random_sampler_usage(self):
        """测试 WeightedRandomSampler 的使用"""
        from torch.utils.data import WeightedRandomSampler

        # 创建不平衡的标签
        labels = np.array([0] * 90 + [1] * 10)

        # 计算样本权重
        unique, counts = np.unique(labels, return_counts=True)
        class_weights = 1.0 / counts
        sample_weights = class_weights[labels]

        # 创建采样器
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True
        )

        # 验证采样器可以正常创建
        assert sampler is not None
        assert len(sampler) == len(labels)


class TestSupConTrainingBinaryLabels:
    """测试 SupCon 训练流程（二分类标签）"""

    def test_training_data_format(self):
        """测试训练数据格式"""
        # 创建临时训练数据
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,is_lead\n")
            for i in range(20):
                is_lead = 1 if i < 5 else 0  # 5 个 lead, 15 个 non-lead
                urgency = "high" if is_lead else "low"
                f.write(f"device_{i:03d},10,3600,{urgency},{is_lead}\n")
            temp_path = f.name

        try:
            # 验证数据集可以正常加载
            dataset = SupConDataset(temp_path)
            assert len(dataset) == 20

            # 验证数据格式
            vectors, label = dataset[0]
            assert vectors.shape == (256,)
            assert label.item() in [0, 1]

            # 验证标签分布
            labels = dataset.labels.numpy()
            lead_count = np.sum(labels == 1)
            non_lead_count = np.sum(labels == 0)
            assert lead_count == 5
            assert non_lead_count == 15

        finally:
            Path(temp_path).unlink()

    def test_binary_label_clustering_goal(self):
        """测试二分类标签的聚类目标"""
        # 这是一个概念测试，验证训练目标
        # 目标：lead 用户聚集在一起，non-lead 用户聚集在一起

        # 模拟训练后的向量空间
        lead_center = np.array([1.0, 0.0])
        non_lead_center = np.array([-1.0, 0.0])

        # 验证两个中心距离较远
        distance = np.linalg.norm(lead_center - non_lead_center)
        assert distance > 1.0, "lead 和 non-lead 中心应该距离较远"

        # 模拟 lead 用户的向量（应该接近 lead_center）
        lead_vectors = np.array([
            [0.9, 0.1],
            [1.0, -0.1],
            [1.1, 0.0],
        ])

        # 验证 lead 用户接近 lead_center
        for vec in lead_vectors:
            dist_to_lead = np.linalg.norm(vec - lead_center)
            dist_to_non_lead = np.linalg.norm(vec - non_lead_center)
            assert dist_to_lead < dist_to_non_lead, "lead 用户应该更接近 lead_center"
