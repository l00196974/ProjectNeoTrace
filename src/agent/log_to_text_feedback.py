"""Log-to-Text 反馈循环

收集下游任务反馈，识别质量问题，自动更新知识库映射。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
from collections import Counter, defaultdict

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.log_to_text_quality import LogToTextQualityMetrics


class FeedbackCollector:
    """反馈收集器"""

    def __init__(self, storage_path: str = "data/feedback"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def collect_downstream_feedback(
        self,
        session_id: str,
        session_text: str,
        downstream_task: str,
        feedback_data: Dict
    ):
        """收集下游任务反馈"""
        feedback = {
            'session_id': session_id,
            'session_text': session_text,
            'downstream_task': downstream_task,
            'feedback_data': feedback_data,
            'timestamp': datetime.now().isoformat()
        }

        # 保存反馈
        feedback_file = self.storage_path / f"{downstream_task}_feedback.jsonl"
        with open(feedback_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(feedback, ensure_ascii=False) + '\n')

    def collect_quality_issue(
        self,
        session_id: str,
        session_text: str,
        issue_type: str,
        issue_description: str
    ):
        """收集质量问题"""
        issue = {
            'session_id': session_id,
            'session_text': session_text,
            'issue_type': issue_type,
            'issue_description': issue_description,
            'timestamp': datetime.now().isoformat()
        }

        # 保存问题
        issue_file = self.storage_path / "quality_issues.jsonl"
        with open(issue_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(issue, ensure_ascii=False) + '\n')


class FeedbackAnalyzer:
    """反馈分析器"""

    def __init__(self, feedback_collector: FeedbackCollector):
        self.feedback_collector = feedback_collector
        self.quality_metrics = LogToTextQualityMetrics()

    def analyze_quality_issues(self) -> Dict:
        """分析质量问题"""
        issue_file = self.feedback_collector.storage_path / "quality_issues.jsonl"

        if not issue_file.exists():
            return {'total_issues': 0, 'issue_types': {}}

        # 加载所有问题
        issues = []
        with open(issue_file, 'r', encoding='utf-8') as f:
            for line in f:
                issues.append(json.loads(line))

        # 统计问题类型
        issue_types = Counter([issue['issue_type'] for issue in issues])

        # 识别常见问题模式
        patterns = self._identify_patterns(issues)

        return {
            'total_issues': len(issues),
            'issue_types': dict(issue_types),
            'patterns': patterns
        }

    def _identify_patterns(self, issues: List[Dict]) -> List[Dict]:
        """识别常见问题模式"""
        patterns = []

        # 按问题类型分组
        issues_by_type = defaultdict(list)
        for issue in issues:
            issues_by_type[issue['issue_type']].append(issue)

        # 分析每种类型的问题
        for issue_type, type_issues in issues_by_type.items():
            if len(type_issues) >= 5:  # 至少 5 个相同类型的问题
                # 提取共同特征
                common_words = self._extract_common_words(
                    [issue['session_text'] for issue in type_issues]
                )

                patterns.append({
                    'issue_type': issue_type,
                    'frequency': len(type_issues),
                    'common_words': common_words[:5],  # 前 5 个常见词
                    'example': type_issues[0]['issue_description']
                })

        return patterns

    def _extract_common_words(self, texts: List[str]) -> List[str]:
        """提取常见词汇"""
        all_words = []
        for text in texts:
            words = text.split()
            all_words.extend(words)

        word_counts = Counter(all_words)
        # 过滤停用词
        stopwords = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个'}
        filtered_counts = {
            word: count for word, count in word_counts.items()
            if word not in stopwords and len(word) > 1
        }

        return [word for word, _ in Counter(filtered_counts).most_common(10)]

    def generate_improvement_suggestions(self) -> List[Dict]:
        """生成改进建议"""
        analysis = self.analyze_quality_issues()
        suggestions = []

        # 基于问题模式生成建议
        for pattern in analysis.get('patterns', []):
            if pattern['issue_type'] == 'missing_app_info':
                suggestions.append({
                    'type': 'mapping_update',
                    'priority': 'high',
                    'suggestion': f"更新应用映射，常见词汇: {', '.join(pattern['common_words'])}",
                    'affected_count': pattern['frequency']
                })
            elif pattern['issue_type'] == 'incorrect_duration':
                suggestions.append({
                    'type': 'duration_format',
                    'priority': 'medium',
                    'suggestion': '改进时长格式化逻辑',
                    'affected_count': pattern['frequency']
                })
            elif pattern['issue_type'] == 'poor_readability':
                suggestions.append({
                    'type': 'text_template',
                    'priority': 'medium',
                    'suggestion': '优化文本模板，提升可读性',
                    'affected_count': pattern['frequency']
                })

        return suggestions


class KnowledgeBaseUpdater:
    """知识库更新器"""

    def __init__(self, knowledge_base_path: str = "src/agent/log_to_text.py"):
        self.knowledge_base_path = Path(knowledge_base_path)

    def suggest_mapping_updates(self, analysis: Dict) -> List[Dict]:
        """建议映射更新"""
        suggestions = []

        # 基于质量问题分析建议新的映射
        for pattern in analysis.get('patterns', []):
            if pattern['issue_type'] == 'missing_app_info':
                for word in pattern['common_words']:
                    if 'com.' in word:  # 可能是包名
                        suggestions.append({
                            'type': 'app_mapping',
                            'package_name': word,
                            'suggested_name': '待确认',
                            'frequency': pattern['frequency']
                        })

        return suggestions

    def apply_updates(self, updates: List[Dict]):
        """应用更新（需要人工审核）"""
        # 生成更新建议文件
        update_file = Path("data/feedback/mapping_updates.json")
        update_file.parent.mkdir(parents=True, exist_ok=True)

        with open(update_file, 'w', encoding='utf-8') as f:
            json.dump(updates, f, indent=2, ensure_ascii=False)

        print(f"映射更新建议已保存: {update_file}")
        print("请人工审核后应用更新")


def main():
    """测试函数"""
    print("=" * 60)
    print("Log-to-Text 反馈循环测试")
    print("=" * 60)

    # 创建组件
    feedback_collector = FeedbackCollector()
    feedback_analyzer = FeedbackAnalyzer(feedback_collector)
    kb_updater = KnowledgeBaseUpdater()

    # 模拟收集反馈
    print("\n收集反馈...")

    # 收集质量问题
    for i in range(10):
        feedback_collector.collect_quality_issue(
            session_id=f'session_{i:03d}',
            session_text=f'用户使用了 com.newapp{i % 3}',
            issue_type='missing_app_info',
            issue_description='应用名称未映射'
        )

    for i in range(5):
        feedback_collector.collect_quality_issue(
            session_id=f'session_{i+10:03d}',
            session_text='用户停留了很长时间',
            issue_type='incorrect_duration',
            issue_description='时长信息不准确'
        )

    # 分析质量问题
    print("\n分析质量问题...")
    analysis = feedback_analyzer.analyze_quality_issues()

    print(f"\n总问题数: {analysis['total_issues']}")
    print("\n问题类型分布:")
    for issue_type, count in analysis['issue_types'].items():
        print(f"  {issue_type}: {count}")

    print("\n识别的问题模式:")
    for pattern in analysis['patterns']:
        print(f"\n  类型: {pattern['issue_type']}")
        print(f"  频率: {pattern['frequency']}")
        print(f"  常见词汇: {', '.join(pattern['common_words'])}")
        print(f"  示例: {pattern['example']}")

    # 生成改进建议
    print("\n生成改进建议...")
    suggestions = feedback_analyzer.generate_improvement_suggestions()

    for suggestion in suggestions:
        print(f"\n  [{suggestion['priority'].upper()}] {suggestion['type']}")
        print(f"  建议: {suggestion['suggestion']}")
        print(f"  影响样本数: {suggestion['affected_count']}")

    # 建议映射更新
    print("\n建议映射更新...")
    mapping_updates = kb_updater.suggest_mapping_updates(analysis)

    for update in mapping_updates:
        print(f"\n  类型: {update['type']}")
        print(f"  包名: {update['package_name']}")
        print(f"  建议名称: {update['suggested_name']}")
        print(f"  频率: {update['frequency']}")

    # 应用更新
    if mapping_updates:
        kb_updater.apply_updates(mapping_updates)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
