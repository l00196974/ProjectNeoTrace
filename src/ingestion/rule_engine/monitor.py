"""规则引擎监控器

统计每个规则的命中次数、Session 质量指标等。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
from collections import defaultdict, Counter

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class RuleMonitor:
    """规则监控器"""

    def __init__(self, storage_path: str = "data/monitoring/rule_stats"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # 统计数据
        self.rule_hits = Counter()  # 规则命中次数
        self.rule_trigger_reasons = defaultdict(list)  # 规则触发原因
        self.session_durations = []  # Session 时长分布
        self.session_event_counts = []  # Session 事件数量分布
        self.total_sessions = 0

    def record_rule_hit(self, rule_name: str, trigger_reason: str, session_data: Dict):
        """记录规则命中"""
        # 更新统计
        self.rule_hits[rule_name] += 1
        self.rule_trigger_reasons[rule_name].append(trigger_reason)
        self.total_sessions += 1

        # 记录 Session 质量指标
        if 'session_duration' in session_data:
            self.session_durations.append(session_data['session_duration'])

        if 'event_count' in session_data:
            self.session_event_counts.append(session_data['event_count'])

        # 持久化记录
        self._save_hit_record(rule_name, trigger_reason, session_data)

    def _save_hit_record(self, rule_name: str, trigger_reason: str, session_data: Dict):
        """保存命中记录"""
        record = {
            'rule_name': rule_name,
            'trigger_reason': trigger_reason,
            'session_id': session_data.get('session_id'),
            'device_id': session_data.get('device_id'),
            'session_duration': session_data.get('session_duration'),
            'event_count': session_data.get('event_count'),
            'timestamp': datetime.now().isoformat()
        }

        # 按日期分文件
        date_str = datetime.now().strftime("%Y%m%d")
        record_file = self.storage_path / f"hits_{date_str}.jsonl"

        with open(record_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        import numpy as np

        stats = {
            'total_sessions': self.total_sessions,
            'rule_hits': dict(self.rule_hits),
            'rule_hit_rates': {},
            'session_duration_stats': {},
            'session_event_count_stats': {},
            'rule_trigger_reasons': {}
        }

        # 计算规则命中率
        if self.total_sessions > 0:
            for rule_name, hits in self.rule_hits.items():
                stats['rule_hit_rates'][rule_name] = hits / self.total_sessions

        # Session 时长统计
        if self.session_durations:
            durations = np.array(self.session_durations)
            stats['session_duration_stats'] = {
                'mean': float(np.mean(durations)),
                'median': float(np.median(durations)),
                'std': float(np.std(durations)),
                'min': float(np.min(durations)),
                'max': float(np.max(durations)),
                'p25': float(np.percentile(durations, 25)),
                'p75': float(np.percentile(durations, 75)),
                'p95': float(np.percentile(durations, 95))
            }

        # Session 事件数量统计
        if self.session_event_counts:
            counts = np.array(self.session_event_counts)
            stats['session_event_count_stats'] = {
                'mean': float(np.mean(counts)),
                'median': float(np.median(counts)),
                'std': float(np.std(counts)),
                'min': float(np.min(counts)),
                'max': float(np.max(counts)),
                'p25': float(np.percentile(counts, 25)),
                'p75': float(np.percentile(counts, 75)),
                'p95': float(np.percentile(counts, 95))
            }

        # 规则触发原因统计
        for rule_name, reasons in self.rule_trigger_reasons.items():
            reason_counts = Counter(reasons)
            stats['rule_trigger_reasons'][rule_name] = dict(reason_counts)

        return stats

    def export_statistics(self, output_path: str):
        """导出统计信息"""
        stats = self.get_statistics()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        print(f"统计信息已导出: {output_path}")

    def load_historical_data(self, start_date: str, end_date: str):
        """加载历史数据"""
        from datetime import datetime, timedelta

        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")

        current = start
        while current <= end:
            date_str = current.strftime("%Y%m%d")
            record_file = self.storage_path / f"hits_{date_str}.jsonl"

            if record_file.exists():
                with open(record_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        record = json.loads(line)
                        self.rule_hits[record['rule_name']] += 1
                        self.rule_trigger_reasons[record['rule_name']].append(
                            record['trigger_reason']
                        )
                        self.total_sessions += 1

                        if record.get('session_duration'):
                            self.session_durations.append(record['session_duration'])
                        if record.get('event_count'):
                            self.session_event_counts.append(record['event_count'])

            current += timedelta(days=1)

        print(f"已加载 {start_date} 到 {end_date} 的历史数据")


def main():
    """测试函数"""
    print("=" * 60)
    print("规则引擎监控器测试")
    print("=" * 60)

    # 创建监控器
    monitor = RuleMonitor()

    # 模拟规则命中
    print("\n模拟规则命中...")

    # 息屏规则
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

    # 地标规则
    for i in range(30):
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

    # 类目规则
    for i in range(20):
        monitor.record_rule_hit(
            rule_name="category_rule",
            trigger_reason="app_category_change",
            session_data={
                'session_id': f'session_{i+80:03d}',
                'device_id': f'device_{i % 10:03d}',
                'session_duration': 150 + i * 20,
                'event_count': 5 + i
            }
        )

    # 获取统计信息
    print("\n统计信息:")
    stats = monitor.get_statistics()

    print(f"\n总 Session 数: {stats['total_sessions']}")

    print("\n规则命中次数:")
    for rule_name, hits in stats['rule_hits'].items():
        hit_rate = stats['rule_hit_rates'][rule_name]
        print(f"  {rule_name}: {hits} 次 ({hit_rate:.2%})")

    print("\nSession 时长统计:")
    duration_stats = stats['session_duration_stats']
    print(f"  均值: {duration_stats['mean']:.2f} 秒")
    print(f"  中位数: {duration_stats['median']:.2f} 秒")
    print(f"  P95: {duration_stats['p95']:.2f} 秒")

    print("\nSession 事件数量统计:")
    count_stats = stats['session_event_count_stats']
    print(f"  均值: {count_stats['mean']:.2f}")
    print(f"  中位数: {count_stats['median']:.2f}")
    print(f"  P95: {count_stats['p95']:.2f}")

    print("\n规则触发原因:")
    for rule_name, reasons in stats['rule_trigger_reasons'].items():
        print(f"  {rule_name}:")
        for reason, count in reasons.items():
            print(f"    {reason}: {count} 次")

    # 导出统计信息
    output_path = "data/monitoring/rule_stats_summary.json"
    monitor.export_statistics(output_path)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
