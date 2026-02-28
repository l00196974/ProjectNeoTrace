"""
性能测试工具集

提供 CPU 推理性能、内存使用、API 延迟的测试工具。
"""

import time
import psutil
import torch
import numpy as np
from typing import Callable, Dict, List, Tuple
from dataclasses import dataclass
import statistics


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    mean: float
    median: float
    p50: float
    p95: float
    p99: float
    min: float
    max: float
    std: float


class InferencePerformanceTester:
    """推理性能测试器"""

    def __init__(self, model: torch.nn.Module, device: str = "cpu"):
        """
        初始化推理性能测试器

        Args:
            model: PyTorch 模型
            device: 设备类型（cpu/cuda）
        """
        self.model = model
        self.device = device
        self.model.to(device)
        self.model.eval()

    def benchmark_inference(
        self,
        input_data: torch.Tensor,
        num_iterations: int = 100,
        warmup_iterations: int = 10
    ) -> PerformanceMetrics:
        """
        基准测试推理性能

        Args:
            input_data: 输入数据
            num_iterations: 测试迭代次数
            warmup_iterations: 预热迭代次数

        Returns:
            性能指标
        """
        input_data = input_data.to(self.device)
        latencies = []

        # 预热
        with torch.no_grad():
            for _ in range(warmup_iterations):
                _ = self.model(input_data)

        # 正式测试
        with torch.no_grad():
            for _ in range(num_iterations):
                start_time = time.perf_counter()
                _ = self.model(input_data)
                end_time = time.perf_counter()
                latencies.append((end_time - start_time) * 1000)  # 转换为毫秒

        return self._calculate_metrics(latencies)

    def benchmark_batch_inference(
        self,
        input_data: torch.Tensor,
        batch_sizes: List[int] = [1, 8, 16, 32, 64],
        num_iterations: int = 100
    ) -> Dict[int, PerformanceMetrics]:
        """
        测试不同批次大小的推理性能

        Args:
            input_data: 输入数据（单样本）
            batch_sizes: 批次大小列表
            num_iterations: 每个批次的测试次数

        Returns:
            批次大小到性能指标的映射
        """
        results = {}

        for batch_size in batch_sizes:
            # 创建批次数据
            batch_data = input_data.repeat(batch_size, 1)
            metrics = self.benchmark_inference(batch_data, num_iterations)
            results[batch_size] = metrics

            print(f"Batch size {batch_size}: {metrics.mean:.3f}ms (P99: {metrics.p99:.3f}ms)")

        return results

    @staticmethod
    def _calculate_metrics(latencies: List[float]) -> PerformanceMetrics:
        """计算性能指标"""
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)

        return PerformanceMetrics(
            mean=statistics.mean(latencies),
            median=statistics.median(latencies),
            p50=sorted_latencies[int(n * 0.50)],
            p95=sorted_latencies[int(n * 0.95)],
            p99=sorted_latencies[int(n * 0.99)],
            min=min(latencies),
            max=max(latencies),
            std=statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        )


class MemoryProfiler:
    """内存使用分析器"""

    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = None

    def start(self):
        """开始内存监控"""
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        print(f"Baseline memory: {self.baseline_memory:.2f} MB")

    def snapshot(self, label: str = ""):
        """记录内存快照"""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        delta = current_memory - self.baseline_memory if self.baseline_memory else 0
        print(f"[{label}] Memory: {current_memory:.2f} MB (Δ {delta:+.2f} MB)")
        return current_memory

    def check_memory_leak(
        self,
        func: Callable,
        num_iterations: int = 100,
        threshold_mb: float = 10.0
    ) -> Tuple[bool, float]:
        """
        检查内存泄漏

        Args:
            func: 要测试的函数
            num_iterations: 迭代次数
            threshold_mb: 内存增长阈值（MB）

        Returns:
            (是否有内存泄漏, 内存增长量)
        """
        self.start()
        initial_memory = self.snapshot("Initial")

        for i in range(num_iterations):
            func()
            if (i + 1) % 10 == 0:
                self.snapshot(f"Iteration {i + 1}")

        final_memory = self.snapshot("Final")
        memory_growth = final_memory - initial_memory

        has_leak = memory_growth > threshold_mb
        return has_leak, memory_growth


class APILatencyTester:
    """API 延迟测试器"""

    def __init__(self, api_func: Callable):
        """
        初始化 API 延迟测试器

        Args:
            api_func: API 函数
        """
        self.api_func = api_func

    def benchmark_latency(
        self,
        request_data: any,
        num_requests: int = 1000
    ) -> PerformanceMetrics:
        """
        测试 API 延迟

        Args:
            request_data: 请求数据
            num_requests: 请求次数

        Returns:
            性能指标
        """
        latencies = []

        for _ in range(num_requests):
            start_time = time.perf_counter()
            _ = self.api_func(request_data)
            end_time = time.perf_counter()
            latencies.append((end_time - start_time) * 1000)  # 转换为毫秒

        return InferencePerformanceTester._calculate_metrics(latencies)

    def benchmark_concurrent(
        self,
        request_data: any,
        num_requests: int = 1000,
        concurrency: int = 10
    ) -> PerformanceMetrics:
        """
        测试并发 API 延迟

        Args:
            request_data: 请求数据
            num_requests: 总请求次数
            concurrency: 并发数

        Returns:
            性能指标
        """
        # 注意：这里需要使用多线程或异步来实现真正的并发
        # 简化版本，仅作为示例
        import concurrent.futures

        latencies = []

        def single_request():
            start_time = time.perf_counter()
            _ = self.api_func(request_data)
            end_time = time.perf_counter()
            return (end_time - start_time) * 1000

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(single_request) for _ in range(num_requests)]
            for future in concurrent.futures.as_completed(futures):
                latencies.append(future.result())

        return InferencePerformanceTester._calculate_metrics(latencies)


def print_performance_report(metrics: PerformanceMetrics, target_ms: float = None):
    """
    打印性能报告

    Args:
        metrics: 性能指标
        target_ms: 目标延迟（毫秒）
    """
    print("\n" + "=" * 50)
    print("Performance Report")
    print("=" * 50)
    print(f"Mean:   {metrics.mean:.3f} ms")
    print(f"Median: {metrics.median:.3f} ms")
    print(f"P50:    {metrics.p50:.3f} ms")
    print(f"P95:    {metrics.p95:.3f} ms")
    print(f"P99:    {metrics.p99:.3f} ms")
    print(f"Min:    {metrics.min:.3f} ms")
    print(f"Max:    {metrics.max:.3f} ms")
    print(f"Std:    {metrics.std:.3f} ms")

    if target_ms:
        status = "✓ PASS" if metrics.p99 < target_ms else "✗ FAIL"
        print(f"\nTarget: {target_ms:.3f} ms - {status}")

    print("=" * 50 + "\n")


if __name__ == "__main__":
    # 示例：测试一个简单的模型
    class DummyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = torch.nn.Linear(256, 128)

        def forward(self, x):
            return self.fc(x)

    # 推理性能测试
    model = DummyModel()
    tester = InferencePerformanceTester(model, device="cpu")
    input_data = torch.randn(1, 256)

    print("Testing inference performance...")
    metrics = tester.benchmark_inference(input_data, num_iterations=100)
    print_performance_report(metrics, target_ms=1.0)

    # 批处理性能测试
    print("\nTesting batch inference performance...")
    batch_results = tester.benchmark_batch_inference(input_data, batch_sizes=[1, 8, 16, 32])

    # 内存测试
    print("\nTesting memory usage...")
    profiler = MemoryProfiler()

    def dummy_inference():
        with torch.no_grad():
            _ = model(input_data)

    has_leak, growth = profiler.check_memory_leak(dummy_inference, num_iterations=100)
    print(f"\nMemory leak detected: {has_leak}")
    print(f"Memory growth: {growth:.2f} MB")
