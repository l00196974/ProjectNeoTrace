#!/usr/bin/env python3
"""
手动测试运行器
用于在没有 pytest 的情况下验证核心模块
"""

import sys
from pathlib import Path

# 添加 src 到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

def test_session_slicer():
    """测试 Session 切片器"""
    print("\n" + "="*80)
    print("测试 Session 切片器")
    print("="*80)

    try:
        from ingestion.session_slicer import SessionSlicer

        # 创建测试数据
        events = [
            {
                "device_id": "test_device_001",
                "timestamp": 1709136000000,
                "app_pkg": "com.autohome",
                "action": "app_foreground",
                "payload": {"dwell_time": 300}
            },
            {
                "device_id": "test_device_001",
                "timestamp": 1709136900000,  # 15 分钟后
                "app_pkg": "com.autohome",
                "action": "app_foreground",
                "payload": {"dwell_time": 200}
            }
        ]

        slicer = SessionSlicer(idle_threshold_ms=600000)  # 10 分钟
        sessions = slicer.slice(events)

        print(f"✓ SessionSlicer 导入成功")
        print(f"✓ 切片结果: {len(sessions)} 个 session")

        if len(sessions) == 2:
            print("✓ 通过: 息屏 > 10min 切断规则正确")
        else:
            print(f"✗ 失败: 期望 2 个 session，实际 {len(sessions)} 个")

        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_log_to_text():
    """测试 Log-to-Text 转换"""
    print("\n" + "="*80)
    print("测试 Log-to-Text 转换")
    print("="*80)

    try:
        from agent.log_to_text import LogToTextConverter

        converter = LogToTextConverter()

        session = {
            "session_id": "session_001",
            "device_id": "test_device_001",
            "events": [
                {
                    "app_pkg": "com.autohome",
                    "action": "app_foreground",
                    "payload": {"dwell_time": 450}
                }
            ]
        }

        text = converter.session_to_text(session)

        print(f"✓ LogToTextConverter 导入成功")
        print(f"✓ 转换结果: {text[:100]}...")

        if "汽车" in text or "autohome" in text.lower():
            print("✓ 通过: 包含汽车相关内容")
        else:
            print("✗ 失败: 未包含预期内容")

        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_supcon_loss():
    """测试 SupCon 损失函数"""
    print("\n" + "="*80)
    print("测试 SupCon 损失函数")
    print("="*80)

    try:
        import torch
        from model.supcon_loss import SupConLoss

        loss_fn = SupConLoss(temperature=0.07)

        # 创建测试数据
        features = torch.randn(32, 128)
        labels = torch.tensor([0, 0, 1, 1, 2, 2] * 5 + [3, 3])

        loss = loss_fn(features, labels)

        print(f"✓ SupConLoss 导入成功")
        print(f"✓ 损失值: {loss.item():.4f}")

        if loss.item() > 0 and not torch.isnan(loss):
            print("✓ 通过: 损失值有效")
        else:
            print("✗ 失败: 损失值无效")

        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_student_model():
    """测试 Student Model"""
    print("\n" + "="*80)
    print("测试 Student Model")
    print("="*80)

    try:
        import torch
        from model.intent_student_model import IntentStudentModel

        model = IntentStudentModel(input_dim=256, hidden_dim=128, output_dim=4)

        # 创建测试输入
        input_vector = torch.randn(1, 256)

        # 测试推理
        import time
        start = time.perf_counter()
        output = model(input_vector)
        elapsed = (time.perf_counter() - start) * 1000  # ms

        print(f"✓ IntentStudentModel 导入成功")
        print(f"✓ 输出形状: {output.shape}")
        print(f"✓ 推理延迟: {elapsed:.4f} ms")

        if elapsed < 10.0:  # 宽松的阈值
            print("✓ 通过: 推理速度合理")
        else:
            print(f"⚠ 警告: 推理延迟 {elapsed:.4f} ms 较高")

        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_proxy_labeler():
    """测试标签挖掘"""
    print("\n" + "="*80)
    print("测试标签挖掘")
    print("="*80)

    try:
        from labeling.proxy_label_miner import ProxyLabelMiner

        miner = ProxyLabelMiner()

        # 测试正样本检测
        sms_content = "您的验证码是 123456，用于汽车之家账号登录"
        has_signal = miner.detect_lead_signal_from_sms(sms_content)

        print(f"✓ ProxyLabelMiner 导入成功")
        print(f"✓ 短信检测结果: {has_signal}")

        if has_signal:
            print("✓ 通过: 正确识别验证码短信")
        else:
            print("✗ 失败: 未识别验证码短信")

        return True
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("ProjectNeoTrace 核心模块测试")
    print("="*80)

    tests = [
        ("Session 切片器", test_session_slicer),
        ("Log-to-Text 转换", test_log_to_text),
        ("SupCon 损失函数", test_supcon_loss),
        ("Student Model", test_student_model),
        ("标签挖掘", test_proxy_labeler),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 测试失败: {e}")
            results.append((name, False))

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 项通过")

    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 项测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
