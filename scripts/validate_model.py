"""模型验证脚本

使用历史留资数据评估模型准确性。
"""

import sys
from pathlib import Path
import argparse
import json
import pandas as pd
import numpy as np
import torch
from typing import Dict, List

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.serving.inference import ProductionInference
from src.utils.metrics import precision_at_k, recall_at_k, compute_metrics


def load_test_data(test_data_path: str) -> pd.DataFrame:
    """加载测试数据"""
    print(f"加载测试数据: {test_data_path}")
    test_data = pd.read_csv(test_data_path)
    print(f"测试样本数: {len(test_data)}")
    return test_data


def batch_predict(
    inference: ProductionInference,
    test_data: pd.DataFrame
) -> List[Dict]:
    """批量预测"""
    print("\n开始批量预测...")
    predictions = []

    for idx, row in test_data.iterrows():
        if idx % 100 == 0:
            print(f"进度: {idx}/{len(test_data)}")

        try:
            # 解析 session_features
            if isinstance(row['session_features'], str):
                session_features = np.array(eval(row['session_features']))
            else:
                session_features = np.array(row['session_features'])

            # 预测
            result = inference.predict_lead_score(
                row['session_text'],
                session_features
            )

            predictions.append({
                'device_id': row['device_id'],
                'lead_score': result['lead_score'],
                'intent_probs': result['intent_probs'],
                'true_label': row['label']
            })
        except Exception as e:
            print(f"预测失败 (device_id={row['device_id']}): {e}")
            continue

    print(f"预测完成: {len(predictions)}/{len(test_data)}")
    return predictions


def calculate_metrics(predictions: List[Dict]) -> Dict:
    """计算评估指标"""
    print("\n计算评估指标...")

    # 提取数据
    y_true = np.array([p['true_label'] for p in predictions])
    y_pred = np.array([p['lead_score'] for p in predictions])

    # Precision@K 和 Recall@K
    metrics = {}
    for k in [10, 50, 100, 200]:
        precision = precision_at_k(y_true, y_pred, k=k, positive_label=3)
        recall = recall_at_k(y_true, y_pred, k=k, positive_label=3)
        metrics[f'precision@{k}'] = float(precision)
        metrics[f'recall@{k}'] = float(recall)
        print(f"Precision@{k}: {precision:.4f}")
        print(f"Recall@{k}: {recall:.4f}")

    # ROC AUC
    try:
        from sklearn.metrics import roc_auc_score
        y_true_binary = (y_true == 3).astype(int)
        auc = roc_auc_score(y_true_binary, y_pred)
        metrics['auc'] = float(auc)
        print(f"AUC: {auc:.4f}")
    except Exception as e:
        print(f"无法计算 AUC: {e}")
        metrics['auc'] = None

    # 高意向人群浓度
    high_intent_threshold = 0.8
    high_intent_mask = y_pred > high_intent_threshold
    if high_intent_mask.sum() > 0:
        high_intent_concentration = (y_true[high_intent_mask] == 3).mean()
        baseline_concentration = (y_true == 3).mean()
        concentration_lift = high_intent_concentration / baseline_concentration if baseline_concentration > 0 else 0

        metrics['high_intent_concentration'] = float(high_intent_concentration)
        metrics['baseline_concentration'] = float(baseline_concentration)
        metrics['concentration_lift'] = float(concentration_lift)

        print(f"\n高意向人群浓度: {high_intent_concentration:.2%}")
        print(f"基线浓度: {baseline_concentration:.2%}")
        print(f"浓度提升: {concentration_lift:.2f}x")
    else:
        print("\n警告: 没有高意向用户（lead_score > 0.8）")
        metrics['high_intent_concentration'] = 0.0
        metrics['baseline_concentration'] = float((y_true == 3).mean())
        metrics['concentration_lift'] = 0.0

    # 不同阈值下的性能
    threshold_results = []
    for threshold in [0.5, 0.6, 0.7, 0.8, 0.9]:
        y_pred_binary = (y_pred > threshold).astype(int)
        y_true_binary = (y_true == 3).astype(int)

        if y_pred_binary.sum() > 0:
            from sklearn.metrics import precision_score, recall_score, f1_score
            precision = precision_score(y_true_binary, y_pred_binary, zero_division=0)
            recall = recall_score(y_true_binary, y_pred_binary, zero_division=0)
            f1 = f1_score(y_true_binary, y_pred_binary, zero_division=0)
        else:
            precision = recall = f1 = 0.0

        threshold_results.append({
            'threshold': threshold,
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1)
        })

    metrics['threshold_analysis'] = threshold_results

    print("\n阈值分析:")
    for result in threshold_results:
        print(f"  阈值 {result['threshold']}: "
              f"Precision={result['precision']:.4f}, "
              f"Recall={result['recall']:.4f}, "
              f"F1={result['f1']:.4f}")

    return metrics


def generate_report(
    model_path: str,
    test_data_path: str,
    predictions: List[Dict],
    metrics: Dict,
    output_path: str
):
    """生成验证报告"""
    print(f"\n生成验证报告: {output_path}")

    report = {
        'model_path': model_path,
        'test_data': test_data_path,
        'test_samples': len(predictions),
        'metrics': metrics,
        'summary': {
            'precision@100': metrics.get('precision@100', 0),
            'recall@100': metrics.get('recall@100', 0),
            'auc': metrics.get('auc', 0),
            'concentration_lift': metrics.get('concentration_lift', 0)
        }
    }

    # 保存报告
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"验证报告已保存")

    # 保存预测结果
    pred_df = pd.DataFrame(predictions)
    pred_output_path = output_path.replace('.json', '_predictions.csv')
    pred_df.to_csv(pred_output_path, index=False)
    print(f"预测结果已保存: {pred_output_path}")


def main():
    parser = argparse.ArgumentParser(description='模型验证脚本')
    parser.add_argument(
        '--model',
        type=str,
        default='data/models/supcon_model.pth',
        help='SupCon 模型路径'
    )
    parser.add_argument(
        '--student_model',
        type=str,
        default='data/models/intent_student_model.pth',
        help='Student 模型路径'
    )
    parser.add_argument(
        '--test_data',
        type=str,
        required=True,
        help='测试数据路径 (CSV 格式)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/results/validation_report.json',
        help='输出报告路径'
    )
    parser.add_argument(
        '--use_mock_embedding',
        action='store_true',
        help='使用 Mock 向量化器'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("ProjectNeoTrace 模型验证")
    print("=" * 60)

    # 创建输出目录
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载测试数据
    test_data = load_test_data(args.test_data)

    # 初始化推理引擎
    print(f"\n加载模型...")
    print(f"  Student Model: {args.student_model}")
    print(f"  SupCon Model: {args.model}")

    inference = ProductionInference(
        student_model_path=args.student_model,
        supcon_model_path=args.model,
        use_mock_embedding=args.use_mock_embedding
    )

    # 批量预测
    predictions = batch_predict(inference, test_data)

    if len(predictions) == 0:
        print("\n错误: 没有成功的预测结果")
        return

    # 计算指标
    metrics = calculate_metrics(predictions)

    # 生成报告
    generate_report(
        args.model,
        args.test_data,
        predictions,
        metrics,
        args.output
    )

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)

    # 输出关键指标
    print("\n关键指标:")
    print(f"  Precision@100: {metrics.get('precision@100', 0):.4f}")
    print(f"  Recall@100: {metrics.get('recall@100', 0):.4f}")
    print(f"  AUC: {metrics.get('auc', 0):.4f}")
    print(f"  浓度提升: {metrics.get('concentration_lift', 0):.2f}x")

    # 判断是否达标
    print("\n达标情况:")
    checks = [
        ("Precision@100 > 0.50", metrics.get('precision@100', 0) > 0.50),
        ("Recall@100 > 0.30", metrics.get('recall@100', 0) > 0.30),
        ("AUC > 0.75", metrics.get('auc', 0) > 0.75),
        ("浓度提升 > 3x", metrics.get('concentration_lift', 0) > 3.0)
    ]

    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")


if __name__ == "__main__":
    main()
