"""A/B 测试分析脚本

分析在线 A/B 测试结果，评估模型效果提升。
"""

import sys
from pathlib import Path
import argparse
import json
import pandas as pd
import numpy as np
from typing import Dict

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_experiment_data(data_path: str) -> pd.DataFrame:
    """加载实验数据"""
    print(f"加载实验数据: {data_path}")

    # 支持 JSON Lines 格式
    if data_path.endswith('.jsonl'):
        data = pd.read_json(data_path, lines=True)
    else:
        data = pd.read_csv(data_path)

    print(f"实验样本数: {len(data)}")
    print(f"对照组样本数: {len(data[data['group'] == 'control'])}")
    print(f"实验组样本数: {len(data[data['group'] == 'treatment'])}")

    return data


def calculate_conversion_rates(data: pd.DataFrame) -> Dict:
    """计算转化率"""
    print("\n计算转化率...")

    # 分组统计
    control_data = data[data['group'] == 'control']
    treatment_data = data[data['group'] == 'treatment']

    # 转化率
    control_conversion = control_data['converted'].mean()
    treatment_conversion = treatment_data['converted'].mean()

    # 提升
    lift = (treatment_conversion - control_conversion) / control_conversion if control_conversion > 0 else 0

    results = {
        'control': {
            'total': len(control_data),
            'contacted': control_data['contacted'].sum(),
            'converted': control_data['converted'].sum(),
            'conversion_rate': float(control_conversion)
        },
        'treatment': {
            'total': len(treatment_data),
            'contacted': treatment_data['contacted'].sum(),
            'converted': treatment_data['converted'].sum(),
            'conversion_rate': float(treatment_conversion)
        },
        'lift': float(lift)
    }

    print(f"对照组转化率: {control_conversion:.2%}")
    print(f"实验组转化率: {treatment_conversion:.2%}")
    print(f"转化率提升: {lift:.2%}")

    return results


def statistical_significance_test(data: pd.DataFrame) -> Dict:
    """统计显著性检验"""
    print("\n统计显著性检验...")

    try:
        from scipy.stats import chi2_contingency

        # 构建列联表
        contingency_table = pd.crosstab(
            data['group'],
            data['converted']
        )

        # 卡方检验
        chi2, p_value, dof, expected = chi2_contingency(contingency_table)

        is_significant = p_value < 0.05

        results = {
            'chi2': float(chi2),
            'p_value': float(p_value),
            'dof': int(dof),
            'is_significant': is_significant
        }

        print(f"卡方统计量: {chi2:.4f}")
        print(f"P 值: {p_value:.4f}")
        print(f"自由度: {dof}")

        if is_significant:
            print("✓ 结果具有统计显著性（p < 0.05）")
        else:
            print("✗ 结果不具有统计显著性（p >= 0.05）")

        return results

    except ImportError:
        print("警告: scipy 未安装，跳过统计检验")
        return {}


def calculate_roi(data: pd.DataFrame, contact_cost: float = 1.0, conversion_value: float = 100.0) -> Dict:
    """计算成本效益"""
    print("\n计算成本效益...")

    control_data = data[data['group'] == 'control']
    treatment_data = data[data['group'] == 'treatment']

    # 对照组
    control_contacts = control_data['contacted'].sum()
    control_conversions = control_data['converted'].sum()
    control_cost = control_contacts * contact_cost
    control_revenue = control_conversions * conversion_value
    control_roi = (control_revenue - control_cost) / control_cost if control_cost > 0 else 0

    # 实验组
    treatment_contacts = treatment_data['contacted'].sum()
    treatment_conversions = treatment_data['converted'].sum()
    treatment_cost = treatment_contacts * contact_cost
    treatment_revenue = treatment_conversions * conversion_value
    treatment_roi = (treatment_revenue - treatment_cost) / treatment_cost if treatment_cost > 0 else 0

    # ROI 提升
    roi_lift = (treatment_roi - control_roi) / control_roi if control_roi > 0 else 0

    results = {
        'control': {
            'contacts': int(control_contacts),
            'conversions': int(control_conversions),
            'cost': float(control_cost),
            'revenue': float(control_revenue),
            'roi': float(control_roi)
        },
        'treatment': {
            'contacts': int(treatment_contacts),
            'conversions': int(treatment_conversions),
            'cost': float(treatment_cost),
            'revenue': float(treatment_revenue),
            'roi': float(treatment_roi)
        },
        'roi_lift': float(roi_lift)
    }

    print(f"对照组 ROI: {control_roi:.2%}")
    print(f"实验组 ROI: {treatment_roi:.2%}")
    print(f"ROI 提升: {roi_lift:.2%}")

    return results


def analyze_by_lead_score(data: pd.DataFrame) -> Dict:
    """按 lead_score 分析"""
    print("\n按 lead_score 分析...")

    # 仅分析实验组（有 lead_score）
    treatment_data = data[data['group'] == 'treatment'].copy()

    if 'lead_score' not in treatment_data.columns:
        print("警告: 数据中没有 lead_score 字段")
        return {}

    # 按分数段统计
    bins = [0, 0.5, 0.6, 0.7, 0.8, 1.0]
    labels = ['0.0-0.5', '0.5-0.6', '0.6-0.7', '0.7-0.8', '0.8-1.0']
    treatment_data['score_bin'] = pd.cut(treatment_data['lead_score'], bins=bins, labels=labels)

    results = []
    for label in labels:
        bin_data = treatment_data[treatment_data['score_bin'] == label]
        if len(bin_data) > 0:
            conversion_rate = bin_data['converted'].mean()
            results.append({
                'score_range': label,
                'count': len(bin_data),
                'conversions': int(bin_data['converted'].sum()),
                'conversion_rate': float(conversion_rate)
            })
            print(f"  {label}: {len(bin_data)} 样本, 转化率 {conversion_rate:.2%}")

    return {'score_analysis': results}


def generate_report(
    experiment_data_path: str,
    conversion_results: Dict,
    significance_results: Dict,
    roi_results: Dict,
    score_analysis: Dict,
    output_path: str
):
    """生成分析报告"""
    print(f"\n生成分析报告: {output_path}")

    report = {
        'experiment_data': experiment_data_path,
        'conversion_rates': conversion_results,
        'statistical_test': significance_results,
        'roi_analysis': roi_results,
        'score_analysis': score_analysis,
        'summary': {
            'conversion_lift': conversion_results['lift'],
            'is_significant': significance_results.get('is_significant', False),
            'roi_lift': roi_results.get('roi_lift', 0)
        }
    }

    # 保存报告
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"分析报告已保存")


def main():
    parser = argparse.ArgumentParser(description='A/B 测试分析脚本')
    parser.add_argument(
        '--experiment_data',
        type=str,
        required=True,
        help='实验数据路径 (CSV 或 JSONL 格式)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/results/ab_test_report.json',
        help='输出报告路径'
    )
    parser.add_argument(
        '--contact_cost',
        type=float,
        default=1.0,
        help='每次触达成本（元）'
    )
    parser.add_argument(
        '--conversion_value',
        type=float,
        default=100.0,
        help='每次转化价值（元）'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("ProjectNeoTrace A/B 测试分析")
    print("=" * 60)

    # 创建输出目录
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载实验数据
    data = load_experiment_data(args.experiment_data)

    # 计算转化率
    conversion_results = calculate_conversion_rates(data)

    # 统计显著性检验
    significance_results = statistical_significance_test(data)

    # 计算 ROI
    roi_results = calculate_roi(data, args.contact_cost, args.conversion_value)

    # 按 lead_score 分析
    score_analysis = analyze_by_lead_score(data)

    # 生成报告
    generate_report(
        args.experiment_data,
        conversion_results,
        significance_results,
        roi_results,
        score_analysis,
        args.output
    )

    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)

    # 输出关键结论
    print("\n关键结论:")
    print(f"  转化率提升: {conversion_results['lift']:.2%}")
    print(f"  统计显著性: {'是' if significance_results.get('is_significant', False) else '否'}")
    print(f"  ROI 提升: {roi_results.get('roi_lift', 0):.2%}")

    # 判断实验是否成功
    print("\n实验评估:")
    checks = [
        ("转化率提升 > 20%", conversion_results['lift'] > 0.20),
        ("统计显著性 (p < 0.05)", significance_results.get('is_significant', False)),
        ("ROI 提升 > 30%", roi_results.get('roi_lift', 0) > 0.30)
    ]

    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {check_name}")


if __name__ == "__main__":
    main()
