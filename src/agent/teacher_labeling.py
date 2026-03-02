"""Teacher Model 标注模块

使用 LLM 作为 Teacher Model 进行离线标注。
"""

import ast
import json
import logging
from typing import Dict, List

from src.agent.llm_client import LLMClient, create_llm_client
from src.agent.prompt_templates import format_multi_intent_prompt
from src.agent.log_to_text import LogToTextConverter
from src.agent.intent_taxonomy import ALL_INTENTS, NUM_INTENTS
from src.types import IntentLabel, SessionDict
from src.utils.traceability import TraceabilityManager

logger = logging.getLogger(__name__)


class TeacherLabeler:
    """Teacher Model 标注器（使用 LLM）"""

    def __init__(
        self,
        llm_client: LLMClient,
        enable_traceability: bool = True,
    ):
        """初始化 Teacher 标注器。

        Args:
            llm_client: LLM 客户端
            enable_traceability: 是否启用可追溯性记录
        """
        self.llm_client = llm_client
        self.log_to_text = LogToTextConverter()
        self.enable_traceability = enable_traceability

        if self.enable_traceability:
            self.traceability_mgr = TraceabilityManager()

    def _get_default_intent(self) -> IntentLabel:
        """LLM 失败时的默认意图。

        Returns:
            默认意图标签
        """
        return {
            "intent_probs": [0.0] * NUM_INTENTS,
            "primary_intent": "unknown",
            "urgency_level": "low",
            "confidence": 0.0
        }

    def label_session(self, session: SessionDict) -> Dict:
        """使用 LLM 标注单个 Session。

        Args:
            session: Session 字典

        Returns:
            标注结果：
            {
                "intent_probs": [11-dim 多标签概率向量],
                "primary_intent": "automotive_purchase",
                "urgency_level": "high",  # high/medium/low
                "confidence": 0.85,  # LLM 置信度
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

        # 4. 构建多标签概率向量（11-dim）
        intent_probs = self._build_intent_vector(result["intents"])

        # 5. 转换 urgency_score 到 urgency_level
        urgency_level = self._convert_urgency_to_level(result.get("urgency_score", 0))

        # 6. 提取置信度（如果 LLM 提供）
        confidence = result.get("confidence", 0.8)  # 默认 0.8

        # 7. 更新可追溯性记录
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
            "intent_probs": intent_probs,  # [11-dim]
            "primary_intent": result["primary_intent"],
            "urgency_level": urgency_level,  # high/medium/low
            "confidence": confidence,
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

    def label_device(
        self,
        device_id: str,
        sessions: List[Dict],
        session_texts_dict: Dict[str, str] = None
    ) -> Dict:
        """使用 LLM 标注单个设备的所有 sessions，生成设备级别的意图。

        Args:
            device_id: 设备 ID
            sessions: 该设备的所有 Session 列表
            session_texts_dict: 预生成的 session_id -> session_text 映射（可选）

        Returns:
            设备级别的标注结果：
            {
                "device_id": "device_000001",
                "session_count": 10,
                "total_duration": 3600,
                "intent_probs": [11-dim 多标签概率向量],
                "primary_intent": "automotive_purchase",
                "secondary_intents": ["automotive_comparison", "automotive_financing"],
                "urgency_level": "high",
                "confidence": 0.85,
                "device_summary": "设备行为总结文本"
            }
        """
        if not sessions:
            logger.warning(f"设备 {device_id} 没有 sessions")
            return self._get_default_device_intent(device_id)

        # 1. 聚合所有 sessions 的文本描述
        session_texts = []
        total_duration = 0

        for session in sessions:
            # 优先使用预生成的文本，否则实时转换
            if session_texts_dict and session.get("session_id") in session_texts_dict:
                session_text = session_texts_dict[session["session_id"]]
            else:
                session_text = self.log_to_text.convert_session(session)

            session_texts.append(session_text)
            total_duration += session.get("session_duration", 0)

        # 2. 构建设备级别的提示词
        device_summary = self._build_device_summary(device_id, sessions, session_texts)

        # 3. 调用 LLM 进行设备级别的意图识别
        try:
            prompt = self._format_device_intent_prompt(device_summary, len(sessions))
            response = self.llm_client.call_with_retry(prompt, max_retries=3)

            # 4. 解析 LLM 响应
            result = self._parse_llm_response(response)

        except Exception as e:
            logger.error(f"设备 {device_id} LLM 标注失败，使用默认意图: {e}")
            return self._get_default_device_intent(device_id, len(sessions), total_duration)

        # 5. 构建多标签概率向量（11-dim）
        intent_probs = self._build_intent_vector(result["intents"])

        # 6. 转换 urgency_score 到 urgency_level
        urgency_level = self._convert_urgency_to_level(result.get("urgency_score", 0))

        # 7. 提取置信度
        confidence = result.get("confidence", 0.8)

        # 8. 提取次要意图
        secondary_intents = [
            item["name"] for item in result["intents"]
            if item["name"] != result["primary_intent"]
        ][:3]  # 最多保留 3 个次要意图

        return {
            "device_id": device_id,
            "session_count": len(sessions),
            "total_duration": total_duration,
            "intent_probs": intent_probs,
            "primary_intent": result["primary_intent"],
            "secondary_intents": secondary_intents,
            "urgency_level": urgency_level,
            "confidence": confidence,
            "device_summary": device_summary,
        }

    def label_devices_batch(
        self,
        device_sessions: Dict[str, List[Dict]],
        session_texts_dict: Dict[str, str] = None,
        show_progress: bool = True
    ) -> List[Dict]:
        """批量标注设备级别的意图。

        Args:
            device_sessions: 设备 ID 到 sessions 列表的映射
            session_texts_dict: 预生成的 session_id -> session_text 映射（可选）
            show_progress: 是否显示进度

        Returns:
            设备级别的标注结果列表
        """
        labeled_devices = []

        device_ids = sorted(device_sessions.keys())
        total_devices = len(device_ids)

        for i, device_id in enumerate(device_ids):
            if show_progress:
                print(f"  进度：{i+1}/{total_devices} - 设备 {device_id}")

            try:
                sessions = device_sessions[device_id]
                device_label = self.label_device(device_id, sessions, session_texts_dict)
                labeled_devices.append(device_label)

            except Exception as e:
                logger.error(f"标注设备 {device_id} 失败：{e}")
                continue

        return labeled_devices

    def _build_device_summary(
        self, device_id: str, sessions: List[Dict], session_texts: List[str]
    ) -> str:
        """构建设备行为总结。

        Args:
            device_id: 设备 ID
            sessions: Session 列表
            session_texts: Session 文本描述列表

        Returns:
            设备行为总结文本
        """
        # 统计关键信息
        app_pkgs = set()
        poi_list = set()

        for session in sessions:
            app_list = session.get("app_pkg_list", [])
            if isinstance(app_list, str):
                import ast
                try:
                    app_list = ast.literal_eval(app_list)
                except:
                    app_list = []
            app_pkgs.update(app_list)

            poi = session.get("lbs_poi_list", [])
            if isinstance(poi, str):
                import ast
                try:
                    poi = ast.literal_eval(poi)
                except:
                    poi = []
            poi_list.update(poi)

        # 构建总结
        summary_parts = [
            f"设备 {device_id} 的行为分析：",
            f"- 总共 {len(sessions)} 个行为会话",
            f"- 使用了 {len(app_pkgs)} 个不同的应用",
            f"- 访问了 {len(poi_list)} 个不同的地点",
            "",
            "各会话详细行为：",
        ]

        # 添加前 5 个 session 的详细描述
        for i, text in enumerate(session_texts[:5]):
            summary_parts.append(f"{i+1}. {text}")

        if len(session_texts) > 5:
            summary_parts.append(f"... 还有 {len(session_texts) - 5} 个会话")

        return "\n".join(summary_parts)

    def _format_device_intent_prompt(self, device_summary: str, session_count: int) -> str:
        """格式化设备级别的意图识别提示词。

        Args:
            device_summary: 设备行为总结
            session_count: Session 数量

        Returns:
            提示词文本
        """
        prompt = f"""你是一个用户意图分析专家。请根据用户在设备上的所有行为会话，判断该用户的整体意图。

{device_summary}

请分析该用户的主要意图和次要意图，并给出紧急度评分（1-10）。

可选意图类别：
1. automotive_purchase - 购车意向
2. automotive_comparison - 车型对比
3. automotive_financing - 汽车金融
4. automotive_insurance - 车险
5. automotive_maintenance - 保养维修
6. automotive_accessories - 汽车用品
7. general_food_delivery - 外卖
8. general_shopping - 电商购物
9. general_social - 社交
10. general_entertainment - 娱乐
11. general_finance - 金融理财

请以 JSON 格式返回结果：
{{
  "primary_intent": "主要意图名称",
  "intents": [
    {{"name": "意图名称", "confidence": 0.9}},
    {{"name": "意图名称", "confidence": 0.6}}
  ],
  "urgency_score": 8
}}

注意：
- primary_intent 必须是置信度最高的意图
- intents 列表按置信度从高到低排序
- urgency_score 范围 1-10，表示用户需求的紧急程度
"""
        return prompt

    def _get_default_device_intent(
        self, device_id: str, session_count: int = 0, total_duration: int = 0
    ) -> Dict:
        """获取默认的设备级别意图。

        Args:
            device_id: 设备 ID
            session_count: Session 数量
            total_duration: 总时长

        Returns:
            默认设备意图
        """
        return {
            "device_id": device_id,
            "session_count": session_count,
            "total_duration": total_duration,
            "intent_probs": [0.0] * NUM_INTENTS,
            "primary_intent": "unknown",
            "secondary_intents": [],
            "urgency_level": "low",
            "confidence": 0.0,
            "device_summary": "",
        }

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
        # 置信度映射：high -> 1.0, medium -> 0.6, low -> 0.3
        confidence_map = {
            "high": 1.0,
            "medium": 0.6,
            "low": 0.3
        }

        intent_vector = [0.0] * NUM_INTENTS

        for intent_item in intents:
            intent_name = intent_item["name"]
            confidence_str = intent_item["confidence"]

            # 转换置信度字符串为数值
            confidence = confidence_map.get(confidence_str.lower(), 0.0)

            if intent_name in ALL_INTENTS:
                idx = ALL_INTENTS.index(intent_name)
                intent_vector[idx] = confidence

        return intent_vector

    def _convert_urgency_to_level(self, urgency_score: float) -> str:
        """将 urgency_score (0-10) 转换为 urgency_level (high/medium/low)。

        Args:
            urgency_score: 紧急度评分 (0-10)

        Returns:
            urgency_level: "high" (7-10), "medium" (4-6), "low" (0-3)
        """
        if urgency_score >= 7:
            return "high"
        elif urgency_score >= 4:
            return "medium"
        else:
            return "low"
