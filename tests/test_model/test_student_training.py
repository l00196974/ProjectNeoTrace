"""Student Model 训练测试

测试 Student 模型训练的简化流程和子集采样。
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

from src.model.train_student_model import (
    IntentDistillationDataset,
    stratified_sample_for_teacher_labeling
)
from src.model.distillation_loss import IntentDistillationLoss


class TestIntentDistillationDataset:
    """测试知识蒸馏数据集（简化版）"""

    def test_dataset_initialization(self):
        """测试数据集初始化"""
        # 创建临时 CSV 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,intent_probs\n")
            f.write("device_001,10,3600,high,\"[0.8, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1]\"\n")
            f.write("device_002,5,1800,medium,\"[0.5, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2]\"\n")
            temp_path = f.name

        try:
            dataset = IntentDistillationDataset(temp_path)

            # 验证数据集大小
            assert len(dataset) == 2

            # 验证数据格式
            features, teacher_probs = dataset[0]
            assert features.shape == (256,), "特征应该是 256 维"
            assert teacher_probs.shape == (11,), "Teacher 概率应该是 11 维"

        finally:
            Path(temp_path).unlink()

    def test_dataset_no_teacher_embedding(self):
        """测试数据集不包含 Teacher embedding"""
        # 创建临时 CSV 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,intent_probs\n")
            f.write("device_001,10,3600,high,\"[0.8, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1]\"\n")
            temp_path = f.name

        try:
            dataset = IntentDistillationDataset(temp_path)

            # 验证 __getitem__ 只返回 2 个元素（不包含 teacher_embedding）
            item = dataset[0]
            assert len(item) == 2, "应该只返回 (features, teacher_probs)"
            assert isinstance(item[0], torch.Tensor), "第一个元素应该是特征张量"
            assert isinstance(item[1], torch.Tensor), "第二个元素应该是 Teacher 概率张量"

        finally:
            Path(temp_path).unlink()

    def test_urgency_level_conversion(self):
        """测试 urgency_level 转换为浮点数"""
        # 创建临时 CSV 文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,intent_probs\n")
            f.write("device_001,10,3600,high,\"[0.8, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1]\"\n")
            f.write("device_002,5,1800,medium,\"[0.5, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2]\"\n")
            f.write("device_003,3,900,low,\"[0.3, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5]\"\n")
            temp_path = f.name

        try:
            dataset = IntentDistillationDataset(temp_path)

            # 验证 urgency_level 转换
            # high -> 1.0, medium -> 0.5, low -> 0.0
            features_high, _ = dataset[0]
            features_medium, _ = dataset[1]
            features_low, _ = dataset[2]

            # urgency_level 是特征的第 3 个元素（索引 2）
            assert features_high[2].item() == 1.0, "high 应该转换为 1.0"
            assert features_medium[2].item() == 0.5, "medium 应该转换为 0.5"
            assert features_low[2].item() == 0.0, "low 应该转换为 0.0"

        finally:
            Path(temp_path).unlink()


class TestStratifiedSampling:
    """测试分层采样"""

    def test_stratified_sampling_ratio(self):
        """测试采样比例"""
        # 创建测试数据
        df = pd.DataFrame({
            'device_id': [f'device_{i:03d}' for i in range(100)],
            'proxy_label': [0] * 25 + [1] * 50 + [2] * 20 + [3] * 5,
            'session_count': np.random.randint(1, 20, 100)
        })

        # 15% 采样
        sampled_df = stratified_sample_for_teacher_labeling(
            df,
            sample_ratio=0.15,
            stratify_column='proxy_label',
            random_state=42
        )

        # 验证采样比例
        assert len(sampled_df) == 15, f"应该采样 15 个设备，实际采样了 {len(sampled_df)} 个"

    def test_stratified_sampling_distribution(self):
        """测试分层采样保持标签分布"""
        # 创建测试数据
        df = pd.DataFrame({
            'device_id': [f'device_{i:03d}' for i in range(100)],
            'proxy_label': [0] * 25 + [1] * 50 + [2] * 20 + [3] * 5,
            'session_count': np.random.randint(1, 20, 100)
        })

        # 15% 采样
        sampled_df = stratified_sample_for_teacher_labeling(
            df,
            sample_ratio=0.15,
            stratify_column='proxy_label',
            random_state=42
        )

        # 验证标签分布比例接近原始分布
        original_dist = df['proxy_label'].value_counts(normalize=True).sort_index()
        sampled_dist = sampled_df['proxy_label'].value_counts(normalize=True).sort_index()

        # 允许一定的误差（由于样本量小）
        for label in original_dist.index:
            if label in sampled_dist.index:
                diff = abs(original_dist[label] - sampled_dist[label])
                assert diff < 0.2, f"标签 {label} 的分布差异过大：{diff}"

    def test_stratified_sampling_random_state(self):
        """测试随机种子的可重复性"""
        df = pd.DataFrame({
            'device_id': [f'device_{i:03d}' for i in range(100)],
            'proxy_label': [0] * 25 + [1] * 50 + [2] * 20 + [3] * 5,
            'session_count': np.random.randint(1, 20, 100)
        })

        # 使用相同的随机种子采样两次
        sampled_df1 = stratified_sample_for_teacher_labeling(
            df, sample_ratio=0.15, random_state=42
        )
        sampled_df2 = stratified_sample_for_teacher_labeling(
            df, sample_ratio=0.15, random_state=42
        )

        # 验证结果一致
        assert sampled_df1['device_id'].tolist() == sampled_df2['device_id'].tolist()


class TestDistillationLossSimplified:
    """测试简化的蒸馏损失函数"""

    def test_loss_initialization(self):
        """测试损失函数初始化（简化版）"""
        criterion = IntentDistillationLoss()

        # 验证不再需要 alpha 参数
        assert hasattr(criterion, 'bce_loss'), "应该有 BCE 损失"
        assert not hasattr(criterion, 'mse_loss'), "不应该有 MSE 损失（已移除）"
        assert not hasattr(criterion, 'alpha'), "不应该有 alpha 参数（已移除）"

    def test_loss_forward_simplified(self):
        """测试简化的前向传播（只使用分类损失）"""
        criterion = IntentDistillationLoss()

        # 创建测试数据
        batch_size = 4
        student_probs = torch.rand(batch_size, 11)
        teacher_probs = torch.rand(batch_size, 11)

        # 计算损失（不再需要 embedding）
        loss = criterion(student_probs, teacher_probs)

        # 验证损失
        assert isinstance(loss, torch.Tensor), "损失应该是张量"
        assert loss.item() >= 0, "损失应该是非负数"
        assert not torch.isnan(loss), "损失不应该是 NaN"

    def test_loss_components_simplified(self):
        """测试简化的损失组成部分"""
        criterion = IntentDistillationLoss()

        batch_size = 4
        student_probs = torch.rand(batch_size, 11)
        teacher_probs = torch.rand(batch_size, 11)

        # 获取损失组成部分
        loss_components = criterion.get_loss_components(student_probs, teacher_probs)

        # 验证只有分类损失
        assert "total_loss" in loss_components
        assert "classification_loss" in loss_components
        assert "embedding_loss" not in loss_components, "不应该有 embedding_loss（已移除）"

        # 验证 total_loss 等于 classification_loss
        assert loss_components["total_loss"] == loss_components["classification_loss"]


class TestStudentModelTraining:
    """测试 Student 模型训练流程"""

    def test_training_with_subset(self):
        """测试使用子集训练"""
        # 这是一个集成测试，验证训练流程可以正常运行
        # 实际训练在 CI 环境中可能太慢，这里只验证接口

        # 创建临时训练数据
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,intent_probs\n")
            for i in range(10):
                intent_probs = [0.0] * 11
                intent_probs[i % 11] = 0.8
                f.write(f"device_{i:03d},10,3600,high,\"{intent_probs}\"\n")
            temp_path = f.name

        try:
            # 验证数据集可以正常加载
            dataset = IntentDistillationDataset(temp_path)
            assert len(dataset) == 10

            # 验证数据格式
            features, teacher_probs = dataset[0]
            assert features.shape == (256,)
            assert teacher_probs.shape == (11,)

        finally:
            Path(temp_path).unlink()

    def test_no_embedding_in_training_data(self):
        """测试训练数据不包含 Teacher embedding"""
        # 创建临时训练数据（不包含 intent_embedding 列）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("device_id,session_count,total_duration,urgency_level,intent_probs\n")
            f.write("device_001,10,3600,high,\"[0.8, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1]\"\n")
            temp_path = f.name

        try:
            # 验证数据集可以正常加载（即使没有 intent_embedding 列）
            dataset = IntentDistillationDataset(temp_path)
            assert len(dataset) == 1

            # 验证 __getitem__ 只返回 2 个元素
            item = dataset[0]
            assert len(item) == 2

        finally:
            Path(temp_path).unlink()
