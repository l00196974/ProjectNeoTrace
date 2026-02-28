#!/usr/bin/env python3
"""
测试运行脚本
支持运行所有测试或特定模块测试
"""
import sys
import subprocess
from pathlib import Path


def run_tests(test_path=None, coverage=True, verbose=True):
    """运行测试"""
    cmd = ["pytest"]

    if test_path:
        cmd.append(test_path)

    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing", "--cov-report=html"])

    if verbose:
        cmd.append("-v")

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    """主函数"""
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
        print(f"Running tests in: {test_path}")
        return run_tests(test_path)
    else:
        print("Running all tests...")
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())
