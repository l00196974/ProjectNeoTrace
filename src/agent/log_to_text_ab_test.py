"""Log-to-Text A/B 测试框架

支持多个 Log-to-Text 版本并行运行，收集质量指标，自动选择最优版本。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
import random
from datetime import datetime

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.log_to_text_quality import LogToTextQualityMetrics


class ABTestManager:
    """A/B 测试管理器"""

    def __init__(self, storage_path: str = "data/ab_tests"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.quality_metrics = LogToTextQualityMetrics()
        self.versions = {}  # version_name -> converter
        self.test_results = {}  # version_name -> results

    def register_version(self, version_name: str, converter):
        """注册一个 Log-to-Text 版本"""
        self.versions[version_name] = converter
        self.test_results[version_name] = {
            'samples': [],
            'quality_scores': [],
            'total_samples': 0
        }
        print(f"已注册版本: {version_name}")

    def assign_version(self, session_id: str) -> str:
        """为 Session 分配版本（随机分配）"""
        if not self.versions:
            raise ValueError("没有注册的版本")

        # 使用 session_id 的哈希确保稳定分配
        version_names = list(self.versions.keys())
        index = hash(session_id) % len(version_names)
        return version_names[index]

    def convert_and_evaluate(
        self,
        session_id: str,
        session: Dict,
        version_name: Optional[str] = None
    ) -> Dict:
        """转换并评估"""
        # 分配版本
        if version_name is None:
            version_name = self.assign_version(session_id)

        # 获取转换器
        converter = self.versions.get(version_name)
        if not converter:
            raise ValueError(f"版本不存在: {version_name}")

        # 转换
        text = converter.convert_session(session)

        # 评估质量
        quality_result = self.quality_metrics.evaluate_overall(text, session)

        # 记录结果
        result = {
            'session_id': session_id,
            'version': version_name,
            'text': text,
            'quality_score': quality_result['overall_score'],
            'quality_grade': quality_result['grade'],
            'timestamp': datetime.now().isoformat()
        }

        self.test_results[version_name]['samples'].append(result)
        self.test_results[version_name]['quality_scores'].append(
            quality_result['overall_score']
        )
        self.test_results[version_name]['total_samples'] += 1

        # 持久化
        self._save_result(result)

        return result

    def _save_result(self, result: Dict):
        """保存测试结果"""
        result_file = self.storage_path / f"{result['version']}_results.jsonl"
        with open(result_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        import numpy as np

        stats = {}

        for version_name, results in self.test_results.items():
            if results['quality_scores']:
                scores = np.array(results['quality_scores'])
                stats[version_name] = {
                    'total_samples': results['total_samples'],
                    'mean_score': float(np.mean(scores)),
                    'median_score': float(np.median(scores)),
                    'std_score': float(np.std(scores)),
                    'min_score': float(np.min(scores)),
                    'max_score': float(np.max(scores))
                }

        return stats

    def compare_versions(self) -> Dict:
        """对比版本"""
        stats = self.get_statistics()

        if len(stats) < 2:
            return {'error': '至少需要 2 个版本才能对比'}

        # 找出最优版本
        best_version = max(stats.items(), key=lambda x: x[1]['mean_score'])

        comparison = {
            'best_version': best_version[0],
            'best_score': best_version[1]['mean_score'],
            'version_comparison': []
        }

        # 对比所有版本
        for version_name, version_stats in stats.items():
            comparison['version_comparison'].append({
                'version': version_name,
                'mean_score': version_stats['mean_score'],
                'total_samples': version_stats['total_samples'],
                'vs_best': version_stats['mean_score'] - best_version[1]['mean_score']
            })

        # 按平均分数排序
        comparison['version_comparison'].sort(
            key=lambda x: x['mean_score'],
            reverse=True
        )

        return comparison

    def select_winner(self, min_samples: int = 100) -> Optional[str]:
        """选择获胜版本"""
        stats = self.get_statistics()

        # 检查样本量
        for version_name, version_stats in stats.items():
            if version_stats['total_samples'] < min_samples:
                print(f"警告: {version_name} 样本量不足 ({version_stats['total_samples']} < {min_samples})")
                return None

        # 选择平均分数最高的版本
        comparison = self.compare_versions()
        winner = comparison['best_version']

        print(f"获胜版本: {winner} (平均分数: {comparison['best_score']:.4f})")
        return winner

    def export_report(self, output_path: str):
        """导出测试报告"""
        stats = self.get_statistics()
        comparison = self.compare_versions()

        report = {
            'statistics': stats,
            'comparison': comparison,
            'timestamp': datetime.now().isoformat()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"测试报告已导出: {output_path}")


def main():
    """测试函数"""
    print("=" * 60)
    print("Log-to-Text A/B 测试框架测试")
    print("=" * 60)

    # 创建 A/B 测试管理器
    ab_test = ABTestManager()

    # 模拟两个版本的转换器
    class ConverterV1:
        def convert_session(self, session):
            return f"用户使用了应用，停留了一段时间。"

    class ConverterV2:
        def convert_session(self, session):
            app_list = session.get('app_pkg_list', [])
            duration = session.get('session_duration', 0)
            location = session.get('lbs_poi_list', [])

            parts = []
            if duration > 0:
                parts.append(f"用户在 {duration // 60} 分钟 内")
            if app_list:
                parts.append(f"使用了汽车之家")
            if location:
                parts.append(f"位置：{location[0]}")

            return "，".join(parts) + "。"

    # 注册版本
    ab_test.register_version('v1_baseline', ConverterV1())
    ab_test.register_version('v2_improved', ConverterV2())

    # 模拟测试
    print("\n运行 A/B 测试...")
    for i in range(100):
        session = {
            'session_id': f'session_{i:03d}',
            'app_pkg_list': ['com.autohome'],
            'session_duration': 300 + i * 10,
            'lbs_poi_list': ['auto_market']
        }

        result = ab_test.convert_and_evaluate(
            session_id=session['session_id'],
            session=session
        )

        if i % 20 == 0:
            print(f"  进度: {i}/100")

    # 获取统计信息
    print("\n统计信息:")
    stats = ab_test.get_statistics()
    for version_name, version_stats in stats.items():
        print(f"\n{version_name}:")
        print(f"  样本数: {version_stats['total_samples']}")
        print(f"  平均分数: {version_stats['mean_score']:.4f}")
        print(f"  中位数: {version_stats['median_score']:.4f}")
        print(f"  标准差: {version_stats['std_score']:.4f}")

    # 对比版本
    print("\n版本对比:")
    comparison = ab_test.compare_versions()
    print(f"最优版本: {comparison['best_version']} (分数: {comparison['best_score']:.4f})")

    for version_comp in comparison['version_comparison']:
        print(f"\n{version_comp['version']}:")
        print(f"  平均分数: {version_comp['mean_score']:.4f}")
        print(f"  vs 最优: {version_comp['vs_best']:+.4f}")

    # 选择获胜版本
    print("\n选择获胜版本...")
    winner = ab_test.select_winner(min_samples=50)

    # 导出报告
    output_path = "data/ab_tests/ab_test_report.json"
    ab_test.export_report(output_path)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
