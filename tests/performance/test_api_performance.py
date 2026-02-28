"""
API 延迟性能测试

测试目标：
- API P50 延迟 < 5ms
- API P99 延迟 < 10ms
- QPS > 1000
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import time
from tests.performance.performance_utils import (
    APILatencyTester,
    print_performance_report
)


def test_api_latency():
    """测试 API 延迟性能"""
    print("=" * 60)
    print("API Latency Performance Test")
    print("=" * 60)

    # TODO: 替换为实际的 API 函数
    # from src.serving.api import predict
    # api_func = predict

    # 临时使用模拟 API 函数
    def mock_api_func(request_data):
        """模拟 API 函数"""
        # 模拟一些计算
        time.sleep(0.001)  # 1ms
        return {"prediction": 0.85, "label": 3}

    tester = APILatencyTester(mock_api_func)

    # 测试单线程延迟
    print("\n[Test 1] Single Thread Latency")
    print("-" * 60)
    request_data = {"device_id": "test_device", "vector": [0.1] * 256}
    metrics = tester.benchmark_latency(request_data, num_requests=1000)
    print_performance_report(metrics, target_ms=10.0)

    # 检查 P50 和 P99
    p50_pass = metrics.p50 < 5.0
    p99_pass = metrics.p99 < 10.0

    print(f"P50 < 5ms:  {'✓ PASS' if p50_pass else '✗ FAIL'}")
    print(f"P99 < 10ms: {'✓ PASS' if p99_pass else '✗ FAIL'}")

    # 测试并发延迟
    print("\n[Test 2] Concurrent Latency")
    print("-" * 60)
    concurrent_metrics = tester.benchmark_concurrent(
        request_data,
        num_requests=1000,
        concurrency=10
    )
    print_performance_report(concurrent_metrics, target_ms=10.0)

    # 计算 QPS
    total_time = concurrent_metrics.mean * 1000 / 1000  # 总时间（秒）
    qps = 1000 / total_time if total_time > 0 else 0
    print(f"Estimated QPS: {qps:.0f}")
    print(f"Target: > 1000 QPS")
    qps_pass = qps > 1000

    # 总结
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"P50 Latency:  {'✓ PASS' if p50_pass else '✗ FAIL'}")
    print(f"P99 Latency:  {'✓ PASS' if p99_pass else '✗ FAIL'}")
    print(f"QPS:          {'✓ PASS' if qps_pass else '✗ FAIL'}")

    all_pass = p50_pass and p99_pass and qps_pass
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_pass else '✗ SOME TESTS FAILED'}")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    success = test_api_latency()
    sys.exit(0 if success else 1)
