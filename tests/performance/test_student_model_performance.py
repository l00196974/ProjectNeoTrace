"""
Student Model 推理性能测试

测试目标：
- 单样本推理时间 < 1ms
- 批处理推理时间 < 10ms (batch_size=32)
- 内存使用 < 2GB
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import torch
import numpy as np
from tests.performance.performance_utils import (
    InferencePerformanceTester,
    MemoryProfiler,
    print_performance_report
)


def test_student_model_inference():
    """测试 Student Model 推理性能"""
    print("=" * 60)
    print("Student Model Inference Performance Test")
    print("=" * 60)

    # TODO: 替换为实际的 Student Model
    # from src.feature_factory.student_model import StudentModel
    # model = StudentModel()

    # 临时使用简单模型进行测试
    class DummyStudentModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.Linear(256, 128)
            self.fc2 = torch.nn.Linear(128, 64)
            self.fc3 = torch.nn.Linear(64, 32)

        def forward(self, x):
            x = torch.relu(self.fc1(x))
            x = torch.relu(self.fc2(x))
            return self.fc3(x)

    model = DummyStudentModel()
    tester = InferencePerformanceTester(model, device="cpu")

    # 测试单样本推理
    print("\n[Test 1] Single Sample Inference")
    print("-" * 60)
    input_data = torch.randn(1, 256)
    metrics = tester.benchmark_inference(input_data, num_iterations=1000)
    print_performance_report(metrics, target_ms=1.0)

    # 测试批处理推理
    print("\n[Test 2] Batch Inference")
    print("-" * 60)
    batch_results = tester.benchmark_batch_inference(
        input_data,
        batch_sizes=[1, 8, 16, 32, 64],
        num_iterations=100
    )

    # 检查批处理性能
    batch_32_metrics = batch_results[32]
    avg_per_sample = batch_32_metrics.mean / 32
    print(f"\nBatch 32 average per sample: {avg_per_sample:.3f} ms")
    print(f"Target: < 0.31 ms (10ms / 32)")
    print(f"Status: {'✓ PASS' if avg_per_sample < 0.31 else '✗ FAIL'}")

    # 内存测试
    print("\n[Test 3] Memory Usage")
    print("-" * 60)
    profiler = MemoryProfiler()

    def inference_func():
        with torch.no_grad():
            _ = model(input_data)

    has_leak, growth = profiler.check_memory_leak(inference_func, num_iterations=1000)

    print(f"\nMemory leak detected: {has_leak}")
    print(f"Memory growth: {growth:.2f} MB")
    print(f"Target: < 10 MB")
    print(f"Status: {'✓ PASS' if not has_leak else '✗ FAIL'}")

    # 总结
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    single_pass = metrics.p99 < 1.0
    batch_pass = avg_per_sample < 0.31
    memory_pass = not has_leak

    print(f"Single Sample Inference: {'✓ PASS' if single_pass else '✗ FAIL'}")
    print(f"Batch Inference:         {'✓ PASS' if batch_pass else '✗ FAIL'}")
    print(f"Memory Usage:            {'✓ PASS' if memory_pass else '✗ FAIL'}")

    all_pass = single_pass and batch_pass and memory_pass
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if all_pass else '✗ SOME TESTS FAILED'}")
    print("=" * 60)

    return all_pass


if __name__ == "__main__":
    success = test_student_model_inference()
    sys.exit(0 if success else 1)
