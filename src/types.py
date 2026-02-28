"""
Type definitions for ProjectNeoTrace.

This module contains TypedDict definitions for all core data structures
to improve type safety and code maintainability.
"""

from typing import TypedDict, List, Dict, Any


class OSEventLog(TypedDict):
    """原始操作系统事件日志"""
    device_id: str
    timestamp: int
    app_pkg: str
    action: str
    payload: Dict[str, Any]


class SessionDict(TypedDict):
    """Session 切片特征"""
    session_id: str
    device_id: str
    start_time: int
    end_time: int
    session_duration: int
    app_switch_freq: int
    config_page_dwell: int
    finance_page_dwell: int
    time_tension_bucket: int
    lbs_poi_list: List[str]
    app_pkg_list: List[str]


class IntentLabel(TypedDict):
    """意图标签（Teacher Model 输出）"""
    intent_vector: List[float]  # 11-dim 多标签向量
    intent_embedding: List[float]  # 128-dim 意图向量
    primary_intent: str  # 主要意图名称
    urgency_score: int  # 紧急度评分 (0-10)


class TraceabilityRecord(TypedDict):
    """可追溯性记录"""
    session_id: str
    device_id: str
    raw_event_ids: List[str]  # 原始事件 ID 列表
    semantic_text: str  # 语义化文本
    intent_labels: List[str]  # 意图标签
    raw_vector: List[float]  # 原始向量
    optimized_vector: List[float]  # 优化后向量
    model_version: str  # 模型版本
    timestamp: int  # 生成时间
