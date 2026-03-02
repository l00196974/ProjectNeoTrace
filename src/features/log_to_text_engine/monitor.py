"""转换监控系统

统计规则命中率和转换质量
"""

import time
import numpy as np
from typing import Dict, List
from collections import defaultdict
from .base import ConversionResult


class ConversionMonitor:
    """转换监控器

    记录和统计转换过程的各项指标
    """

    def __init__(self):
        self.stats = {
            "rule_hits": defaultdict(int),
            "conversion_times": [],
            "text_lengths": [],
            "failures": [],
            "total_conversions": 0
        }

    def record_conversion(self, result: ConversionResult, duration_ms: float):
        """记录转换结果

        Args:
            result: 转换结果
            duration_ms: 转换耗时（毫秒）
        """
        self.stats["total_conversions"] += 1

        # 规则命中统计
        rule_id = result.rule_id
        self.stats["rule_hits"][rule_id] += 1

        # 转换时间
        self.stats["conversion_times"].append(duration_ms)

        # 文本长度
        if result.success:
            self.stats["text_lengths"].append(len(result.text))
        else:
            error_msg = result.metadata.get("error", "Unknown")
            self.stats["failures"].append({
                "rule_id": rule_id,
                "error": error_msg
            })

    def get_statistics(self) -> Dict:
        """获取统计信息

        Returns:
            统计信息字典
        """
        total_conversions = self.stats["total_conversions"]

        if total_conversions == 0:
            return {
                "total_conversions": 0,
                "rule_hits": {},
                "rule_hit_rates": {},
                "avg_conversion_time_ms": 0,
                "avg_text_length": 0,
                "failure_count": 0,
                "failure_rate": 0
            }

        return {
            "total_conversions": total_conversions,
            "rule_hits": dict(self.stats["rule_hits"]),
            "rule_hit_rates": {
                rule_id: count / total_conversions
                for rule_id, count in self.stats["rule_hits"].items()
            },
            "avg_conversion_time_ms": np.mean(self.stats["conversion_times"]) if self.stats["conversion_times"] else 0,
            "p95_conversion_time_ms": np.percentile(self.stats["conversion_times"], 95) if self.stats["conversion_times"] else 0,
            "p99_conversion_time_ms": np.percentile(self.stats["conversion_times"], 99) if self.stats["conversion_times"] else 0,
            "avg_text_length": np.mean(self.stats["text_lengths"]) if self.stats["text_lengths"] else 0,
            "min_text_length": min(self.stats["text_lengths"]) if self.stats["text_lengths"] else 0,
            "max_text_length": max(self.stats["text_lengths"]) if self.stats["text_lengths"] else 0,
            "failure_count": len(self.stats["failures"]),
            "failure_rate": len(self.stats["failures"]) / total_conversions if total_conversions > 0 else 0
        }

    def get_rule_performance(self) -> List[Dict]:
        """获取规则性能排名

        Returns:
            规则性能列表，按命中次数降序排列
        """
        total_conversions = self.stats["total_conversions"]

        if total_conversions == 0:
            return []

        performance = []
        for rule_id, count in self.stats["rule_hits"].items():
            performance.append({
                "rule_id": rule_id,
                "hit_count": count,
                "hit_rate": count / total_conversions,
                "percentage": f"{count / total_conversions * 100:.2f}%"
            })

        # 按命中次数降序排列
        performance.sort(key=lambda x: x["hit_count"], reverse=True)

        return performance

    def get_failure_summary(self) -> Dict:
        """获取失败摘要

        Returns:
            失败摘要信息
        """
        if not self.stats["failures"]:
            return {
                "total_failures": 0,
                "failure_by_rule": {},
                "failure_by_error": {}
            }

        failure_by_rule = defaultdict(int)
        failure_by_error = defaultdict(int)

        for failure in self.stats["failures"]:
            failure_by_rule[failure["rule_id"]] += 1
            failure_by_error[failure["error"]] += 1

        return {
            "total_failures": len(self.stats["failures"]),
            "failure_by_rule": dict(failure_by_rule),
            "failure_by_error": dict(failure_by_error)
        }

    def reset(self):
        """重置统计信息"""
        self.stats = {
            "rule_hits": defaultdict(int),
            "conversion_times": [],
            "text_lengths": [],
            "failures": [],
            "total_conversions": 0
        }

    def print_summary(self):
        """打印统计摘要"""
        stats = self.get_statistics()
        performance = self.get_rule_performance()

        print("\n=== 转换统计摘要 ===")
        print(f"总转换次数: {stats['total_conversions']}")
        print(f"平均转换时间: {stats['avg_conversion_time_ms']:.2f} ms")
        print(f"P95 转换时间: {stats['p95_conversion_time_ms']:.2f} ms")
        print(f"平均文本长度: {stats['avg_text_length']:.1f} 字符")
        print(f"失败次数: {stats['failure_count']} ({stats['failure_rate']:.2%})")

        print("\n=== 规则命中排名 ===")
        for i, perf in enumerate(performance, 1):
            print(f"{i}. {perf['rule_id']}: {perf['hit_count']} 次 ({perf['percentage']})")

        if stats['failure_count'] > 0:
            failure_summary = self.get_failure_summary()
            print("\n=== 失败统计 ===")
            for rule_id, count in failure_summary['failure_by_rule'].items():
                print(f"  {rule_id}: {count} 次")
