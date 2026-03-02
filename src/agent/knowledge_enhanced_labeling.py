"""知识增强的 LLM 标注系统

在调用 LLM 前查询领域知识库，提供用户后续行为参考，提升标注准确性。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.knowledge.automotive_ontology import KnowledgeBase
from src.agent.llm_client import LLMClient


class KnowledgeEnhancedLabeler:
    """知识增强的标注器"""

    def __init__(self, llm_client: LLMClient, knowledge_base: KnowledgeBase):
        self.llm_client = llm_client
        self.knowledge_base = knowledge_base

    def label_device(self, device_id: str, sessions: List[Dict]) -> Dict:
        """
        对设备进行意图标注（设备级别）

        Args:
            device_id: 设备 ID
            sessions: 设备的所有 Session 列表

        Returns:
            设备级别的意图标注结果
        """
        # 1. 提取所有行为
        all_behaviors = []
        all_texts = []

        for session in sessions:
            session_text = session.get('text', '')
            all_texts.append(session_text)

            # 从 Session 中提取行为
            behaviors = self._extract_behaviors_from_session(session)
            all_behaviors.extend(behaviors)

        # 2. 查询领域知识库
        domain_context = self.knowledge_base.get_domain_context(
            '\n'.join(all_texts),
            all_behaviors
        )

        # 3. 查询相似用户模式
        similar_patterns = self.knowledge_base.query_similar_users(
            device_id,
            all_behaviors
        )

        # 4. 构建增强 Prompt
        enhanced_prompt = self._build_enhanced_prompt(
            device_id=device_id,
            sessions=sessions,
            domain_context=domain_context,
            similar_patterns=similar_patterns
        )

        # 5. 调用 LLM 标注
        llm_response = self.llm_client.label_intent(enhanced_prompt)

        # 6. 解析 LLM 响应
        intent_data = self._parse_llm_response(llm_response)

        # 7. 记录标注结果（用于后续知识库更新）
        self._record_labeling_result(device_id, all_behaviors, intent_data)

        return intent_data

    def _extract_behaviors_from_session(self, session: Dict) -> List[str]:
        """从 Session 中提取行为"""
        behaviors = []

        # 从 Session 文本中提取
        text = session.get('text', '')
        if '配置页' in text:
            behaviors.append('查看配置')
        if '金融' in text or '贷款' in text:
            behaviors.append('查看金融方案')
        if '对比' in text:
            behaviors.append('对比车型')
        if '汽车市场' in text or '4S店' in text:
            behaviors.append('访问汽车市场')

        # 从 Session 元数据中提取
        if session.get('config_page_dwell', 0) > 60:
            behaviors.append('长时间停留在配置页')
        if session.get('finance_page_dwell', 0) > 30:
            behaviors.append('查看金融方案')

        # 从应用列表中提取
        app_pkg_list = session.get('app_pkg_list', [])
        if 'com.autohome' in app_pkg_list:
            behaviors.append('访问汽车之家')
        if 'com.yiche' in app_pkg_list:
            behaviors.append('访问易车网')

        return behaviors

    def _build_enhanced_prompt(
        self,
        device_id: str,
        sessions: List[Dict],
        domain_context: str,
        similar_patterns: List[Dict]
    ) -> str:
        """构建增强 Prompt"""
        prompt_parts = []

        # 1. 任务说明
        prompt_parts.append("""你是一个汽车行业的用户意图识别专家。请根据用户的行为序列，识别用户的购车意图。

请输出结构化的 JSON 格式，包含以下字段：
- intents: 意图列表（从以下 11 个类别中选择）
  - 购车意图、金融意图、外卖意图、出行意图、娱乐意图、社交意图、购物意图、新闻意图、工具意图、教育意图、其他意图
- confidence: 置信度（0-1 之间的浮点数）
- reasoning: 推理过程（简要说明为什么做出这个判断）
""")

        # 2. 领域知识上下文
        if domain_context:
            prompt_parts.append(f"\n## 领域知识\n{domain_context}")

        # 3. 相似用户模式
        if similar_patterns:
            prompt_parts.append("\n## 相似用户的典型行为模式")
            for pattern in similar_patterns[:2]:  # 只显示前 2 个
                prompt_parts.append(f"\n阶段: {pattern['stage']}")
                prompt_parts.append(f"典型行为: {', '.join(pattern['typical_behaviors'])}")
                prompt_parts.append(f"转化概率: {pattern['probability']:.0%}")

        # 4. 用户行为序列
        prompt_parts.append(f"\n## 用户行为序列（设备 ID: {device_id}）")
        for idx, session in enumerate(sessions, 1):
            prompt_parts.append(f"\nSession {idx}:")
            prompt_parts.append(f"  文本: {session.get('text', '')}")
            if 'session_duration' in session:
                prompt_parts.append(f"  时长: {session['session_duration']} 秒")
            if 'app_pkg_list' in session:
                prompt_parts.append(f"  应用: {', '.join(session['app_pkg_list'])}")

        # 5. 输出格式要求
        prompt_parts.append("""

请输出 JSON 格式的结果：
```json
{
  "intents": ["购车意图"],
  "confidence": 0.85,
  "reasoning": "用户多次访问汽车平台，查看配置和金融方案，表现出明确的购车意图"
}
```
""")

        return '\n'.join(prompt_parts)

    def _parse_llm_response(self, llm_response: str) -> Dict:
        """解析 LLM 响应"""
        try:
            # 提取 JSON 部分
            if '```json' in llm_response:
                json_start = llm_response.find('```json') + 7
                json_end = llm_response.find('```', json_start)
                json_str = llm_response[json_start:json_end].strip()
            elif '```' in llm_response:
                json_start = llm_response.find('```') + 3
                json_end = llm_response.find('```', json_start)
                json_str = llm_response[json_start:json_end].strip()
            else:
                json_str = llm_response.strip()

            # 解析 JSON
            intent_data = json.loads(json_str)

            # 验证必填字段
            if 'intents' not in intent_data or 'confidence' not in intent_data:
                raise ValueError("缺少必填字段: intents 或 confidence")

            return intent_data

        except Exception as e:
            print(f"解析 LLM 响应失败: {e}")
            print(f"原始响应: {llm_response}")

            # 返回默认值
            return {
                'intents': ['其他意图'],
                'confidence': 0.0,
                'reasoning': f'解析失败: {str(e)}'
            }

    def _record_labeling_result(
        self,
        device_id: str,
        behaviors: List[str],
        intent_data: Dict
    ):
        """记录标注结果（用于后续知识库更新）"""
        # 这里可以记录到数据库或文件，用于后续分析和知识库更新
        result = {
            'device_id': device_id,
            'behaviors': behaviors,
            'intents': intent_data.get('intents', []),
            'confidence': intent_data.get('confidence', 0.0),
            'timestamp': Path(__file__).stat().st_mtime
        }

        # 保存到文件（简化实现）
        result_file = Path("data/knowledge/labeling_results.jsonl")
        result_file.parent.mkdir(parents=True, exist_ok=True)

        with open(result_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    def update_knowledge_base(self, device_id: str, actual_outcome: str):
        """
        根据实际结果更新知识库

        Args:
            device_id: 设备 ID
            actual_outcome: 实际结果（如 'converted', 'not_converted'）
        """
        # 加载标注结果
        result_file = Path("data/knowledge/labeling_results.jsonl")
        if not result_file.exists():
            return

        # 查找该设备的标注结果
        device_result = None
        with open(result_file, 'r', encoding='utf-8') as f:
            for line in f:
                result = json.loads(line)
                if result['device_id'] == device_id:
                    device_result = result
                    break

        if not device_result:
            return

        # 更新知识库
        self.knowledge_base.update_user_pattern(
            device_id=device_id,
            behaviors=device_result['behaviors'],
            outcome=actual_outcome
        )

        print(f"知识库已更新: {device_id} -> {actual_outcome}")


class FeedbackLoop:
    """反馈循环：根据标注结果持续改进"""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.knowledge_base = knowledge_base

    def collect_feedback(self, device_id: str, predicted_intent: str, actual_outcome: str):
        """收集反馈"""
        feedback = {
            'device_id': device_id,
            'predicted_intent': predicted_intent,
            'actual_outcome': actual_outcome,
            'timestamp': Path(__file__).stat().st_mtime
        }

        # 保存反馈
        feedback_file = Path("data/knowledge/feedback.jsonl")
        feedback_file.parent.mkdir(parents=True, exist_ok=True)

        with open(feedback_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(feedback, ensure_ascii=False) + '\n')

    def analyze_feedback(self) -> Dict:
        """分析反馈，识别标注质量问题"""
        feedback_file = Path("data/knowledge/feedback.jsonl")
        if not feedback_file.exists():
            return {}

        # 加载所有反馈
        feedbacks = []
        with open(feedback_file, 'r', encoding='utf-8') as f:
            for line in f:
                feedbacks.append(json.loads(line))

        # 统计准确率
        total = len(feedbacks)
        correct = sum(1 for f in feedbacks if f['predicted_intent'] == f['actual_outcome'])
        accuracy = correct / total if total > 0 else 0

        # 识别常见错误模式
        error_patterns = {}
        for feedback in feedbacks:
            if feedback['predicted_intent'] != feedback['actual_outcome']:
                key = f"{feedback['predicted_intent']} -> {feedback['actual_outcome']}"
                error_patterns[key] = error_patterns.get(key, 0) + 1

        return {
            'total_samples': total,
            'accuracy': accuracy,
            'error_patterns': error_patterns
        }

    def refresh_knowledge_base(self):
        """刷新知识库（根据反馈更新）"""
        analysis = self.analyze_feedback()

        print("反馈分析结果:")
        print(f"  总样本数: {analysis.get('total_samples', 0)}")
        print(f"  准确率: {analysis.get('accuracy', 0):.2%}")

        if analysis.get('error_patterns'):
            print("  常见错误模式:")
            for pattern, count in sorted(
                analysis['error_patterns'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]:
                print(f"    {pattern}: {count} 次")

        # TODO: 根据错误模式更新知识库
        # 例如：调整购车阶段的判断规则、更新高意向行为特征等


def main():
    """测试函数"""
    print("=" * 60)
    print("知识增强的 LLM 标注系统测试")
    print("=" * 60)

    # 创建组件
    from src.agent.llm_client import MockLLMClient
    llm_client = MockLLMClient()
    knowledge_base = KnowledgeBase()
    labeler = KnowledgeEnhancedLabeler(llm_client, knowledge_base)

    # 模拟 Session 数据
    sessions = [
        {
            'text': '用户在汽车之家浏览了宝马 5 系，停留 5 分钟',
            'session_duration': 300,
            'app_pkg_list': ['com.autohome'],
            'config_page_dwell': 180
        },
        {
            'text': '用户查看了金融方案和贷款计算器',
            'session_duration': 120,
            'app_pkg_list': ['com.autohome'],
            'finance_page_dwell': 60
        },
        {
            'text': '用户访问了汽车市场，停留 30 分钟',
            'session_duration': 1800,
            'lbs_poi_list': ['auto_market']
        }
    ]

    # 标注
    print("\n标注设备意图...")
    result = labeler.label_device('device_001', sessions)

    print(f"\n标注结果:")
    print(f"  意图: {result.get('intents', [])}")
    print(f"  置信度: {result.get('confidence', 0):.2f}")
    print(f"  推理: {result.get('reasoning', '')}")

    # 模拟反馈循环
    print("\n测试反馈循环...")
    feedback_loop = FeedbackLoop(knowledge_base)

    # 收集反馈
    feedback_loop.collect_feedback('device_001', '购车意图', 'converted')
    feedback_loop.collect_feedback('device_002', '购车意图', 'not_converted')
    feedback_loop.collect_feedback('device_003', '其他意图', 'not_converted')

    # 分析反馈
    feedback_loop.refresh_knowledge_base()

    # 更新知识库
    print("\n更新知识库...")
    labeler.update_knowledge_base('device_001', 'converted')

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
