"""Teacher Model 标注模块

使用 LLM 作为 Teacher Model 进行离线标注。
"""

import json
import logging
from typing import Dict, List
import numpy as np

from src.agent.llm_client import LLMClient, create_llm_client
from src.agent.prompt_templates import format_multi_intent_prompt
from src.agent.log_to_text import LogToTextConverter
from src.agent.embedding import create_text_embedding
from src.agent.intent_taxonomy import ALL_INTENTS, NUM_INTENTS
from src.types import IntentLabel, SessionDict
from src.utils.traceability import TraceabilityManager

logger = logging.getLogger(__name__)


class TeacherLabeler:
    """Teacher Model 标注器（使用 LLM）"""

    def __init__(
        self,
        llm_client: LLMClient,
        text_embedding=None,
        use_mock_embedding: bool = False,
        enable_traceability: bool = True,
    ):
        """初始化 Teacher 标注器。

        Args:
            llm_client: LLM 客户端
            text_embedding: 文本向量化器（可选）
            use_mock_embedding: 是否使用 Mock 向量化器
            enable_traceability: 是否启用可追溯性记录
        """
        self.llm_client = llm_client
        self.log_to_text = LogToTextConverter()
        self.enable_traceability = enable_traceability

        # 文本向量化器
        if text_embedding is None:
            self.text_embedding = create_text_embedding(use_mock=use_mock_embedding)
        else:
            self.text_embedding = text_embedding

        if self.enable_traceability:
            self.traceability_mgr = TraceabilityManager()

    def _get_default_intent(self) -> IntentLabel:
        """LLM 失败时的默认意图。

        Returns:
            默认意图标签
        """
        return {
            "intent_vector": [0.0] * NUM_INTENTS,
            "intent_embedding": [0.0] * 128,
            "primary_intent": "unknown",
            "urgency_score": 0
        }

    def label_session(self, session: SessionDict) -> Dict:
        """使用 LLM 标注单个 Session。

        Args:
            session: Session 字典

        Returns:
            标注结果：
            {
                "intent_vector": [11-dim 多标签向量],
                "intent_embedding": [128-dim 意图向量],
                "primary_intent": "automotive_purchase",
                "urgency_score": 7,
                "session_text": "用户行为文本描述"
            }
        """
        # 1. Log-to-Text 转换
        session_text = self.log_to_text.convert_session(session)

        # 2. 调用 LLM 进行意图识别（带重试机制）
        try:
            prompt = format_multi_intent_prompt(session_text)
            response = self.llm_client.call_with_retry(prompt, max_retries=3)

            # 3. 解析 LLM 响应
            result = self._parse_llm_response(response)

        except Exception as e:
            logger.error(f"LLM 标注失败，使用默认意图: {e}")
            # 使用默认意图
            default_intent = self._get_default_intent()
            return {
                **default_intent,
                "session_text": session_text,
            }

        # 4. 构建多标签向量（11-dim）
        intent_vector = self._build_intent_vector(result["intents"])

        # 5. 生成意图向量（128-dim）
        intent_text = self._format_intent_text(result)
        intent_embedding = self._get_intent_embedding(intent_text)

        # 6. 更新可追溯性记录
        if self.enable_traceability:
            try:
                session_id = session.get("session_id", "")
                if session_id:
                    intent_labels = [item["name"] for item in result.get("intents", [])]
                    self.traceability_mgr.update_record(
                        session_id,
                        {
                            "semantic_text": session_text,
                            "intent_labels": intent_labels,
                        }
                    )
            except Exception as e:
                logger.warning(f"更新可追溯性记录失败: {e}")

        return {
            "intent_vector": intent_vector,  # [11-dim]
            "intent_embedding": intent_embedding,  # [128-dim]
            "primary_intent": result["primary_intent"],
            "urgency_score": result["urgency_score"],
            "session_text": session_text,
        }

    def label_sessions_batch(
        self, sessions: List[Dict], show_progress: bool = True
    ) -> List[Dict]:
        """
        批量标注 Session

        Args:
            sessions: Session 列表
            show_progress: 是否显示进度

        Returns:
            标注结果列表
        """
        labeled_sessions = []

        for i, session in enumerate(sessions):
            if show_progress and i % 10 == 0:
                print(f"  进度：{i}/{len(sessions)}")

            try:
                label = self.label_session(session)

                # 合并 Session 和标注结果
                labeled_session = {**session, **label}
                labeled_sessions.append(labeled_session)

            except Exception as e:
                print(f"标注 Session {session.get('session_id', 'unknown')} 失败：{e}")
                continue

        return labeled_sessions

    def _parse_llm_response(self, response: str) -> Dict:
        """
        解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的结果字典
        """
        # 尝试提取 JSON
        response = response.strip()

        # 移除可能的 markdown 代码块标记
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        # 解析 JSON
        result = json.loads(response)

        return result

    def _build_intent_vector(self, intents: List[Dict]) -> List[float]:
        """
        构建多标签向量（11-dim）

        Args:
            intents: 意图列表

        Returns:
            多标签向量
        """
        intent_vector = [0.0] * NUM_INTENTS

        for intent_item in intents:
            intent_name = intent_item["name"]
            confidence = intent_item["confidence"]

            if intent_name in ALL_INTENTS:
                idx = ALL_INTENTS.index(intent_name)
                intent_vector[idx] = confidence

        return intent_vector

    def _format_intent_text(self, result: Dict) -> str:
        """
        格式化意图文本（用于生成向量）

        Args:
            result: LLM 解析结果

        Returns:
            意图文本
        """
        parts = []

        # 主要意图
        parts.append(f"主要意图：{result['primary_intent']}")

        # 所有意图
        intent_names = [item["name"] for item in result["intents"]]
        parts.append(f"所有意图：{', '.join(intent_names)}")

        # 紧急度
        if result["urgency_score"] > 0:
            parts.append(f"紧急度：{result['urgency_score']}/10")

        return "；".join(parts)

    def _get_intent_embedding(self, intent_text: str) -> List[float]:
        """
        获取意图向量

        Args:
            intent_text: 意图文本

        Returns:
            意图向量（128-dim）
        """
        # 使用文本向量化器
        embedding = self.text_embedding.encode(intent_text, normalize=True)

        # 降维到 128 维
        embedding_128 = self.text_embedding.reduce_dimension(embedding, target_dim=128)

        return embedding_128.tolist()
