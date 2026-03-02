"""切片监控仪表板

可视化规则命中率、Session 质量指标、异常检测。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.rule_engine.monitor import RuleMonitor


class SlicingDashboard:
    """切片监控仪表板"""

    def __init__(self, monitor: RuleMonitor):
        self.monitor = monitor

    def generate_html_report(self, output_path: str):
        """生成 HTML 报告"""
        stats = self.monitor.get_statistics()

        html = self._build_html(stats)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"HTML 报告已生成: {output_path}")

    def _build_html(self, stats: Dict) -> str:
        """构建 HTML"""
        html_parts = []

        # HTML 头部
        html_parts.append("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Session 切片监控仪表板</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 30px;
        }
        .metric-card {
            display: inline-block;
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin: 10px;
            min-width: 200px;
        }
        .metric-title {
            font-size: 14px;
            color: #666;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background-color: #4CAF50;
            transition: width 0.3s ease;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Session 切片监控仪表板</h1>
        <p>生成时间: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
""")

        # 总览指标
        html_parts.append("""
        <h2>总览</h2>
        <div class="metric-card">
            <div class="metric-title">总 Session 数</div>
            <div class="metric-value">""" + str(stats['total_sessions']) + """</div>
        </div>
""")

        # 规则命中统计
        html_parts.append("""
        <h2>规则命中统计</h2>
        <table>
            <tr>
                <th>规则名称</th>
                <th>命中次数</th>
                <th>命中率</th>
                <th>命中率可视化</th>
            </tr>
""")

        for rule_name, hits in stats['rule_hits'].items():
            hit_rate = stats['rule_hit_rates'].get(rule_name, 0)
            html_parts.append(f"""
            <tr>
                <td>{rule_name}</td>
                <td>{hits}</td>
                <td>{hit_rate:.2%}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {hit_rate * 100}%"></div>
                    </div>
                </td>
            </tr>
""")

        html_parts.append("</table>")

        # Session 时长统计
        if stats.get('session_duration_stats'):
            duration_stats = stats['session_duration_stats']
            html_parts.append("""
        <h2>Session 时长统计（秒）</h2>
        <div class="metric-card">
            <div class="metric-title">均值</div>
            <div class="metric-value">""" + f"{duration_stats['mean']:.2f}" + """</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">中位数</div>
            <div class="metric-value">""" + f"{duration_stats['median']:.2f}" + """</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">P95</div>
            <div class="metric-value">""" + f"{duration_stats['p95']:.2f}" + """</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">最大值</div>
            <div class="metric-value">""" + f"{duration_stats['max']:.2f}" + """</div>
        </div>
""")

        # Session 事件数量统计
        if stats.get('session_event_count_stats'):
            count_stats = stats['session_event_count_stats']
            html_parts.append("""
        <h2>Session 事件数量统计</h2>
        <div class="metric-card">
            <div class="metric-title">均值</div>
            <div class="metric-value">""" + f"{count_stats['mean']:.2f}" + """</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">中位数</div>
            <div class="metric-value">""" + f"{count_stats['median']:.2f}" + """</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">P95</div>
            <div class="metric-value">""" + f"{count_stats['p95']:.2f}" + """</div>
        </div>
        <div class="metric-card">
            <div class="metric-title">最大值</div>
            <div class="metric-value">""" + f"{count_stats['max']:.2f}" + """</div>
        </div>
""")

        # 规则触发原因
        if stats.get('rule_trigger_reasons'):
            html_parts.append("""
        <h2>规则触发原因</h2>
""")
            for rule_name, reasons in stats['rule_trigger_reasons'].items():
                html_parts.append(f"""
        <h3>{rule_name}</h3>
        <table>
            <tr>
                <th>触发原因</th>
                <th>次数</th>
            </tr>
""")
                for reason, count in reasons.items():
                    html_parts.append(f"""
            <tr>
                <td>{reason}</td>
                <td>{count}</td>
            </tr>
""")
                html_parts.append("</table>")

        # HTML 尾部
        html_parts.append("""
    </div>
</body>
</html>
""")

        return ''.join(html_parts)

    def print_summary(self):
        """打印摘要"""
        stats = self.monitor.get_statistics()

        print("=" * 60)
        print("Session 切片监控摘要")
        print("=" * 60)

        print(f"\n总 Session 数: {stats['total_sessions']}")

        print("\n规则命中率:")
        for rule_name, hits in stats['rule_hits'].items():
            hit_rate = stats['rule_hit_rates'].get(rule_name, 0)
            print(f"  {rule_name}: {hits} 次 ({hit_rate:.2%})")

        if stats.get('session_duration_stats'):
            duration_stats = stats['session_duration_stats']
            print("\nSession 时长统计:")
            print(f"  均值: {duration_stats['mean']:.2f} 秒")
            print(f"  中位数: {duration_stats['median']:.2f} 秒")
            print(f"  P95: {duration_stats['p95']:.2f} 秒")

        if stats.get('session_event_count_stats'):
            count_stats = stats['session_event_count_stats']
            print("\nSession 事件数量统计:")
            print(f"  均值: {count_stats['mean']:.2f}")
            print(f"  中位数: {count_stats['median']:.2f}")
            print(f"  P95: {count_stats['p95']:.2f}")


def main():
    """测试函数"""
    print("=" * 60)
    print("切片监控仪表板测试")
    print("=" * 60)

    # 创建监控器
    monitor = RuleMonitor()

    # 模拟数据
    print("\n生成模拟数据...")
    for i in range(100):
        rule_name = ["screen_off_rule", "location_rule", "category_rule"][i % 3]
        trigger_reason = {
            "screen_off_rule": "screen_off > 10min",
            "location_rule": "lbs_poi_change",
            "category_rule": "app_category_change"
        }[rule_name]

        monitor.record_rule_hit(
            rule_name=rule_name,
            trigger_reason=trigger_reason,
            session_data={
                'session_id': f'session_{i:03d}',
                'device_id': f'device_{i % 20:03d}',
                'session_duration': 200 + i * 5,
                'event_count': 10 + i % 30
            }
        )

    # 创建仪表板
    dashboard = SlicingDashboard(monitor)

    # 打印摘要
    dashboard.print_summary()

    # 生成 HTML 报告
    output_path = "data/monitoring/slicing_dashboard.html"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    dashboard.generate_html_report(output_path)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
