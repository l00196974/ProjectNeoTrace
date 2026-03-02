"""Log-to-Text 质量指标

定义语义完整性、可读性、准确性等质量指标。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
import re

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class LogToTextQualityMetrics:
    """Log-to-Text 质量指标"""

    def __init__(self):
        # 关键信息关键词
        self.key_info_keywords = {
            'app': ['使用', '访问', '打开', '浏览'],
            'duration': ['分钟', '小时', '秒', 'minute', 'hour', 'second'],
            'location': ['位置', '地点', '市场', '店', 'location'],
            'action': ['查看', '对比', '停留', '切换']
        }

    def evaluate_semantic_completeness(self, text: str, session: Dict) -> Dict:
        """评估语义完整性"""
        score = 0.0
        details = []

        # 检查是否包含应用信息
        if session.get('app_pkg_list'):
            has_app = any(keyword in text for keyword in self.key_info_keywords['app'])
            if has_app:
                score += 0.3
                details.append('包含应用信息')
            else:
                details.append('缺少应用信息')

        # 检查是否包含时长信息
        if session.get('session_duration', 0) > 0:
            has_duration = any(keyword in text for keyword in self.key_info_keywords['duration'])
            if has_duration:
                score += 0.3
                details.append('包含时长信息')
            else:
                details.append('缺少时长信息')

        # 检查是否包含地点信息
        if session.get('lbs_poi_list'):
            has_location = any(keyword in text for keyword in self.key_info_keywords['location'])
            if has_location:
                score += 0.2
                details.append('包含地点信息')
            else:
                details.append('缺少地点信息')

        # 检查是否包含行为信息
        has_action = any(keyword in text for keyword in self.key_info_keywords['action'])
        if has_action:
            score += 0.2
            details.append('包含行为信息')
        else:
            details.append('缺少行为信息')

        return {
            'score': score,
            'details': details
        }

    def evaluate_readability(self, text: str) -> Dict:
        """评估可读性"""
        score = 1.0
        details = []

        # 检查文本长度
        if len(text) < 10:
            score -= 0.3
            details.append('文本过短')
        elif len(text) > 500:
            score -= 0.2
            details.append('文本过长')

        # 检查句子结构
        sentences = re.split(r'[。！？]', text)
        if len(sentences) > 5:
            score -= 0.1
            details.append('句子过多')

        # 检查是否有重复词汇
        words = text.split()
        if len(words) != len(set(words)):
            duplicate_ratio = 1 - len(set(words)) / len(words)
            if duplicate_ratio > 0.3:
                score -= 0.2
                details.append(f'重复词汇过多 ({duplicate_ratio:.1%})')

        # 检查标点符号
        if '，' not in text and '。' not in text and len(text) > 20:
            score -= 0.1
            details.append('缺少标点符号')

        score = max(0.0, score)

        return {
            'score': score,
            'details': details if details else ['可读性良好']
        }

    def evaluate_accuracy(self, text: str, session: Dict) -> Dict:
        """评估准确性"""
        score = 1.0
        details = []

        # 检查应用映射准确性
        if session.get('app_pkg_list'):
            for app_pkg in session['app_pkg_list']:
                # 如果原始包名出现在文本中，说明未映射
                if app_pkg in text:
                    score -= 0.3
                    details.append(f'应用未映射: {app_pkg}')

        # 检查时长准确性
        if 'session_duration' in session:
            duration = session['session_duration']
            # 提取文本中的时长
            duration_match = re.search(r'(\d+)\s*(分钟|小时|秒)', text)
            if duration_match:
                value = int(duration_match.group(1))
                unit = duration_match.group(2)

                # 转换为秒
                if unit == '分钟':
                    text_duration = value * 60
                elif unit == '小时':
                    text_duration = value * 3600
                else:
                    text_duration = value

                # 检查误差
                error_ratio = abs(text_duration - duration) / duration
                if error_ratio > 0.2:  # 误差超过 20%
                    score -= 0.3
                    details.append(f'时长不准确: 实际 {duration}秒, 文本 {text_duration}秒')

        score = max(0.0, score)

        return {
            'score': score,
            'details': details if details else ['映射准确']
        }

    def evaluate_overall(self, text: str, session: Dict) -> Dict:
        """综合评估"""
        completeness = self.evaluate_semantic_completeness(text, session)
        readability = self.evaluate_readability(text)
        accuracy = self.evaluate_accuracy(text, session)

        # 加权平均
        overall_score = (
            completeness['score'] * 0.4 +
            readability['score'] * 0.3 +
            accuracy['score'] * 0.3
        )

        return {
            'overall_score': overall_score,
            'completeness': completeness,
            'readability': readability,
            'accuracy': accuracy,
            'grade': self._get_grade(overall_score)
        }

    def _get_grade(self, score: float) -> str:
        """获取评级"""
        if score >= 0.9:
            return 'A'
        elif score >= 0.8:
            return 'B'
        elif score >= 0.7:
            return 'C'
        elif score >= 0.6:
            return 'D'
        else:
            return 'F'


def main():
    """测试函数"""
    print("=" * 60)
    print("Log-to-Text 质量指标测试")
    print("=" * 60)

    # 创建质量评估器
    metrics = LogToTextQualityMetrics()

    # 测试用例 1: 高质量文本
    print("\n测试 1: 高质量文本")
    text1 = "用户在 5 分钟 内，使用了汽车之家，在配置页停留了 3 分钟，位置：汽车市场。"
    session1 = {
        'app_pkg_list': ['com.autohome'],
        'session_duration': 300,
        'lbs_poi_list': ['auto_market']
    }
    result1 = metrics.evaluate_overall(text1, session1)
    print(f"文本: {text1}")
    print(f"综合评分: {result1['overall_score']:.2f} ({result1['grade']})")
    print(f"  语义完整性: {result1['completeness']['score']:.2f} - {', '.join(result1['completeness']['details'])}")
    print(f"  可读性: {result1['readability']['score']:.2f} - {', '.join(result1['readability']['details'])}")
    print(f"  准确性: {result1['accuracy']['score']:.2f} - {', '.join(result1['accuracy']['details'])}")

    # 测试用例 2: 低质量文本（缺少信息）
    print("\n测试 2: 低质量文本（缺少信息）")
    text2 = "用户使用了应用。"
    session2 = {
        'app_pkg_list': ['com.autohome'],
        'session_duration': 300,
        'lbs_poi_list': ['auto_market']
    }
    result2 = metrics.evaluate_overall(text2, session2)
    print(f"文本: {text2}")
    print(f"综合评分: {result2['overall_score']:.2f} ({result2['grade']})")
    print(f"  语义完整性: {result2['completeness']['score']:.2f} - {', '.join(result2['completeness']['details'])}")
    print(f"  可读性: {result2['readability']['score']:.2f} - {', '.join(result2['readability']['details'])}")
    print(f"  准确性: {result2['accuracy']['score']:.2f} - {', '.join(result2['accuracy']['details'])}")

    # 测试用例 3: 未映射的应用
    print("\n测试 3: 未映射的应用")
    text3 = "用户在 5 分钟 内，使用了 com.autohome。"
    session3 = {
        'app_pkg_list': ['com.autohome'],
        'session_duration': 300
    }
    result3 = metrics.evaluate_overall(text3, session3)
    print(f"文本: {text3}")
    print(f"综合评分: {result3['overall_score']:.2f} ({result3['grade']})")
    print(f"  语义完整性: {result3['completeness']['score']:.2f} - {', '.join(result3['completeness']['details'])}")
    print(f"  可读性: {result3['readability']['score']:.2f} - {', '.join(result3['readability']['details'])}")
    print(f"  准确性: {result3['accuracy']['score']:.2f} - {', '.join(result3['accuracy']['details'])}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
