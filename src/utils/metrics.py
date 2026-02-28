"""指标计算工具"""
import numpy as np
from typing import List, Tuple
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


def precision_at_k(y_true: np.ndarray, y_scores: np.ndarray, k: int) -> float:
    """
    计算 Precision@K

    Args:
        y_true: 真实标签 (0/1)
        y_scores: 预测分数
        k: Top-K

    Returns:
        Precision@K 值
    """
    # 获取 Top-K 索引
    top_k_indices = np.argsort(y_scores)[-k:]

    # 计算 Top-K 中的正样本数量
    num_positives = np.sum(y_true[top_k_indices])

    return num_positives / k


def recall_at_k(y_true: np.ndarray, y_scores: np.ndarray, k: int) -> float:
    """
    计算 Recall@K

    Args:
        y_true: 真实标签 (0/1)
        y_scores: 预测分数
        k: Top-K

    Returns:
        Recall@K 值
    """
    # 获取 Top-K 索引
    top_k_indices = np.argsort(y_scores)[-k:]

    # 计算 Top-K 中的正样本数量
    num_positives_in_topk = np.sum(y_true[top_k_indices])

    # 总正样本数量
    total_positives = np.sum(y_true)

    if total_positives == 0:
        return 0.0

    return num_positives_in_topk / total_positives


def compute_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, y_scores: np.ndarray = None
) -> dict:
    """
    计算分类指标

    Args:
        y_true: 真实标签
        y_pred: 预测标签
        y_scores: 预测分数（可选，用于计算 AUC）

    Returns:
        指标字典
    """
    metrics = {
        "precision": precision_score(y_true, y_pred, average="weighted", zero_division=0),
        "recall": recall_score(y_true, y_pred, average="weighted", zero_division=0),
        "f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
    }

    if y_scores is not None:
        try:
            metrics["auc"] = roc_auc_score(y_true, y_scores, multi_class="ovr")
        except ValueError:
            metrics["auc"] = 0.0

    return metrics


def compute_ranking_metrics(
    y_true: np.ndarray, y_scores: np.ndarray, k_list: List[int] = [100, 500, 1000]
) -> dict:
    """
    计算排序指标

    Args:
        y_true: 真实标签 (0/1)
        y_scores: 预测分数
        k_list: K 值列表

    Returns:
        指标字典
    """
    metrics = {}

    for k in k_list:
        if k > len(y_true):
            k = len(y_true)

        metrics[f"precision@{k}"] = precision_at_k(y_true, y_scores, k)
        metrics[f"recall@{k}"] = recall_at_k(y_true, y_scores, k)

    return metrics
