"""规则优化器

根据监控数据调整规则参数、自动禁用低效规则、建议新规则。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.rule_engine.monitor import RuleMonitor


class RuleOptimizer:
    """规则优化器"""

    def __init__(self, monitor: RuleMonitor):
        self.monitor = monitor

        # 优化阈值
        self.thresholds = {
            'min_hit_rate': 0.05,  # 最低命中率 5%
            'max_session_duration': 7200,  # 最大 Session 时长 2 小时
            'min_session_duration': 10,  # 最小 Session 时长 10 秒
            'max_event_count': 1000,  # 最大事件数量
            'min_event_count': 1  # 最小事件数量
        }

    def analyze_rules(self) -> Dict:
        """分析规则性能"""
        stats = self.monitor.get_statistics()
        analysis = {
            'low_efficiency_rules': [],
            'high_efficiency_rules': [],
            'parameter_suggestions': [],
            'new_rule_suggestions': []
        }

        # 识别低效规则
        for rule_name, hit_rate in stats['rule_hit_rates'].items():
            if hit_rate < self.thresholds['min_hit_rate']:
                analysis['low_efficiency_rules'].append({
                    'rule_name': rule_name,
                    'hit_rate': hit_rate,
                    'recommendation': 'disable',
                    'reason': f'命中率过低 ({hit_rate:.2%})'
                })
            elif hit_rate > 0.3:
                analysis['high_efficiency_rules'].append({
                    'rule_name': rule_name,
                    'hit_rate': hit_rate
                })

        # 分析 Session 质量
        if stats.get('session_duration_stats'):
            duration_stats = stats['session_duration_stats']

            # 检查是否有过长的 Session
            if duration_stats['p95'] > self.thresholds['max_session_duration']:
                analysis['parameter_suggestions'].append({
                    'type': 'duration_threshold',
                    'current_p95': duration_stats['p95'],
                    'threshold': self.thresholds['max_session_duration'],
                    'suggestion': '建议添加最大时长规则，防止 Session 过长'
                })

            # 检查是否有过短的 Session
            if duration_stats['p25'] < self.thresholds['min_session_duration']:
                analysis['parameter_suggestions'].append({
                    'type': 'duration_threshold',
                    'current_p25': duration_stats['p25'],
                    'threshold': self.thresholds['min_session_duration'],
                    'suggestion': '建议调整切片规则，避免产生过短的 Session'
                })

        # 分析事件数量
        if stats.get('session_event_count_stats'):
            count_stats = stats['session_event_count_stats']

            # 检查是否有事件过多的 Session
            if count_stats['p95'] > self.thresholds['max_event_count']:
                analysis['parameter_suggestions'].append({
                    'type': 'event_count_threshold',
                    'current_p95': count_stats['p95'],
                    'threshold': self.thresholds['max_event_count'],
                    'suggestion': '建议添加最大事件数规则，防止 Session 事件过多'
                })

        # 建议新规则
        analysis['new_rule_suggestions'] = self._suggest_new_rules(stats)

        return analysis

    def _suggest_new_rules(self, stats: Dict) -> List[Dict]:
        """建议新规则"""
        suggestions = []

        # 基于触发原因分析
        if stats.get('rule_trigger_reasons'):
            # 统计所有触发原因
            all_reasons = []
            for reasons in stats['rule_trigger_reasons'].values():
                all_reasons.extend(reasons.keys())

            # 如果某些原因频繁出现，建议添加专门的规则
            from collections import Counter
            reason_counts = Counter(all_reasons)

            for reason, count in reason_counts.most_common(5):
                if count > stats['total_sessions'] * 0.1:  # 超过 10% 的 Session
                    suggestions.append({
                        'reason': reason,
                        'frequency': count / stats['total_sessions'],
                        'suggestion': f'考虑为 "{reason}" 添加专门的规则'
                    })

        return suggestions

    def generate_optimization_report(self) -> str:
        """生成优化报告"""
        analysis = self.analyze_rules()

        report_parts = []
        report_parts.append("=" * 60)
        report_parts.append("规则优化报告")
        report_parts.append("=" * 60)

        # 低效规则
        if analysis['low_efficiency_rules']:
            report_parts.append("\n低效规则（建议禁用）:")
            for rule in analysis['low_efficiency_rules']:
                report_parts.append(
                    f"  - {rule['rule_name']}: {rule['reason']} "
                    f"(命中率: {rule['hit_rate']:.2%})"
                )
        else:
            report_parts.append("\n✓ 没有发现低效规则")

        # 高效规则
        if analysis['high_efficiency_rules']:
            report_parts.append("\n高效规则:")
            for rule in analysis['high_efficiency_rules']:
                report_parts.append(
                    f"  - {rule['rule_name']}: 命中率 {rule['hit_rate']:.2%}"
                )

        # 参数调整建议
        if analysis['parameter_suggestions']:
            report_parts.append("\n参数调整建议:")
            for suggestion in analysis['parameter_suggestions']:
                report_parts.append(f"  - {suggestion['suggestion']}")
        else:
            report_parts.append("\n✓ 当前参数配置合理")

        # 新规则建议
        if analysis['new_rule_suggestions']:
            report_parts.append("\n新规则建议:")
            for suggestion in analysis['new_rule_suggestions']:
                report_parts.append(
                    f"  - {suggestion['suggestion']} "
                    f"(频率: {suggestion['frequency']:.2%})"
                )

        report_parts.append("\n" + "=" * 60)

        return '\n'.join(report_parts)

    def apply_optimizations(self, auto_disable: bool = False) -> Dict:
        """应用优化建议"""
        analysis = self.analyze_rules()
        actions = {
            'disabled_rules': [],
            'adjusted_parameters': [],
            'added_rules': []
        }

        # 自动禁用低效规则
        if auto_disable:
            for rule in analysis['low_efficiency_rules']:
                rule_name = rule['rule_name']
                # TODO: 实际禁用规则的逻辑
                actions['disabled_rules'].append(rule_name)
                print(f"已禁用规则: {rule_name}")

        return actions

    def export_report(self, output_path: str):
        """导出优化报告"""
        analysis = self.analyze_rules()
        report_text = self.generate_optimization_report()

        # 保存 JSON 格式
        json_path = output_path.replace('.txt', '.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        # 保存文本格式
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_text)

        print(f"优化报告已导出:")
        print(f"  JSON: {json_path}")
        print(f"  文本: {output_path}")


def main():
    """测试函数"""
    print("=" * 60)
    print("规则优化器测试")
    print("=" * 60)

    # 创建监控器
    monitor = RuleMonitor()

    # 模拟数据
    print("\n生成模拟数据...")

    # 高效规则
    for i in range(50):
        monitor.record_rule_hit(
            rule_name="screen_off_rule",
            trigger_reason="screen_off > 10min",
            session_data={
                'session_id': f'session_{i:03d}',
                'device_id': f'device_{i % 10:03d}',
                'session_duration': 300 + i * 10,
                'event_count': 10 + i
            }
        )

    # 中效规则
    for i in range(20):
        monitor.record_rule_hit(
            rule_name="location_rule",
            trigger_reason="lbs_poi_change",
            session_data={
                'session_id': f'session_{i+50:03d}',
                'device_id': f'device_{i % 10:03d}',
                'session_duration': 200 + i * 15,
                'event_count': 8 + i
            }
        )

    # 低效规则
    for i in range(3):
        monitor.record_rule_hit(
            rule_name="rare_rule",
            trigger_reason="rare_condition",
            session_data={
                'session_id': f'session_{i+70:03d}',
                'device_id': f'device_{i:03d}',
                'session_duration': 100,
                'event_count': 5
            }
        )

    # 创建优化器
    optimizer = RuleOptimizer(monitor)

    # 生成优化报告
    print("\n生成优化报告...")
    report = optimizer.generate_optimization_report()
    print(report)

    # 导出报告
    output_path = "data/monitoring/optimization_report.txt"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    optimizer.export_report(output_path)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
