# 验证方法论

## 概述

本文档描述如何验证 ProjectNeoTrace 模型的准确性和效果，包括离线验证、在线验证和业务指标评估。

## 验证目标

验证模型是否能够准确识别汽车留资高意向用户，具体目标：

1. **准确性**: 模型预测为高意向的用户中，实际留资的比例
2. **召回率**: 实际留资用户中，被模型识别出的比例
3. **转化率提升**: 使用模型后，留资转化率相比基线的提升
4. **误报率控制**: 模型预测为高意向但实际未留资的比例

## 离线验证

### 1. 数据准备

使用历史留资数据进行离线验证：

```python
import pandas as pd
from src.serving.inference import ProductionInference

# 加载测试数据
test_data = pd.read_csv("data/processed/test_labeled.csv")

# 数据格式
# device_id, session_text, session_features, label
# - label 3: 高意向用户（留资/到店）
# - label 2: 考虑购车
# - label 1: 汽车爱好者
# - label 0: 无效数据
```

### 2. 批量预测

```python
# 初始化推理引擎
inference = ProductionInference(
    student_model_path="data/models/intent_student_model.pth",
    supcon_model_path="data/models/supcon_model.pth",
    use_mock_embedding=False
)

# 批量预测
predictions = []
for _, row in test_data.iterrows():
    result = inference.predict_lead_score(
        row['session_text'],
        eval(row['session_features'])  # 字符串转数组
    )
    predictions.append({
        'device_id': row['device_id'],
        'lead_score': result['lead_score'],
        'intent_probs': result['intent_probs'],
        'true_label': row['label']
    })

# 保存预测结果
pred_df = pd.DataFrame(predictions)
pred_df.to_csv("data/results/predictions.csv", index=False)
```

### 3. 计算评估指标

#### 3.1 Precision@K 和 Recall@K

```python
from src.utils.metrics import precision_at_k, recall_at_k

# 提取真实标签和预测分数
y_true = pred_df['true_label'].values
y_pred = pred_df['lead_score'].values

# 计算 Precision@K
for k in [10, 50, 100, 200]:
    precision = precision_at_k(y_true, y_pred, k=k, positive_label=3)
    print(f"Precision@{k}: {precision:.4f}")

# 计算 Recall@K
for k in [10, 50, 100, 200]:
    recall = recall_at_k(y_true, y_pred, k=k, positive_label=3)
    print(f"Recall@{k}: {recall:.4f}")
```

**解释**:
- **Precision@100**: 预测分数最高的 100 个用户中，实际留资用户的比例
- **Recall@100**: 实际留资用户中，被排在前 100 名的比例

**目标**:
- Precision@100 > 50%（前 100 名中至少 50 个是真实留资用户）
- Recall@100 > 30%（至少捕获 30% 的留资用户）

#### 3.2 ROC 曲线和 AUC

```python
from sklearn.metrics import roc_curve, auc
import matplotlib.pyplot as plt

# 计算 ROC 曲线
fpr, tpr, thresholds = roc_curve(
    y_true == 3,  # 二分类：Label 3 vs 其他
    y_pred
)
roc_auc = auc(fpr, tpr)

# 绘制 ROC 曲线
plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, label=f'ROC curve (AUC = {roc_auc:.2f})')
plt.plot([0, 1], [0, 1], 'k--', label='Random')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve')
plt.legend()
plt.savefig("data/results/roc_curve.png")
print(f"AUC: {roc_auc:.4f}")
```

**目标**: AUC > 0.75

#### 3.3 意图人群浓度分析

分析高意向人群中实际留资用户的浓度：

```python
# 定义高意向阈值
high_intent_threshold = 0.8

# 筛选高意向用户
high_intent_users = pred_df[pred_df['lead_score'] > high_intent_threshold]

# 计算浓度
concentration = (high_intent_users['true_label'] == 3).mean()
print(f"高意向人群浓度: {concentration:.2%}")

# 对比基线浓度
baseline_concentration = (pred_df['true_label'] == 3).mean()
print(f"基线浓度: {baseline_concentration:.2%}")
print(f"浓度提升: {concentration / baseline_concentration:.2f}x")
```

**目标**: 高意向人群浓度 > 基线浓度 3 倍

#### 3.4 不同阈值下的性能

```python
from sklearn.metrics import precision_score, recall_score, f1_score

# 测试不同阈值
thresholds = [0.5, 0.6, 0.7, 0.8, 0.9]
results = []

for threshold in thresholds:
    y_pred_binary = (y_pred > threshold).astype(int)
    y_true_binary = (y_true == 3).astype(int)

    precision = precision_score(y_true_binary, y_pred_binary)
    recall = recall_score(y_true_binary, y_pred_binary)
    f1 = f1_score(y_true_binary, y_pred_binary)

    results.append({
        'threshold': threshold,
        'precision': precision,
        'recall': recall,
        'f1': f1
    })

# 输出结果
results_df = pd.DataFrame(results)
print(results_df)
results_df.to_csv("data/results/threshold_analysis.csv", index=False)
```

### 4. 生成验证报告

```python
# 生成完整验证报告
report = {
    'model_path': 'data/models/supcon_model.pth',
    'test_data': 'data/processed/test_labeled.csv',
    'test_samples': len(test_data),
    'metrics': {
        'precision@100': precision_at_k(y_true, y_pred, k=100, positive_label=3),
        'recall@100': recall_at_k(y_true, y_pred, k=100, positive_label=3),
        'auc': roc_auc,
        'high_intent_concentration': concentration,
        'baseline_concentration': baseline_concentration,
        'concentration_lift': concentration / baseline_concentration
    },
    'threshold_analysis': results_df.to_dict('records')
}

# 保存报告
import json
with open("data/results/validation_report.json", "w") as f:
    json.dump(report, f, indent=2)

print("验证报告已保存到 data/results/validation_report.json")
```

## 在线验证

### 1. A/B 测试框架

#### 1.1 用户分组

```python
import hashlib

def assign_group(user_id: str) -> str:
    """
    将用户分配到对照组或实验组

    Args:
        user_id: 用户唯一标识

    Returns:
        "control" 或 "treatment"
    """
    # 使用哈希确保稳定分组
    hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return "control" if hash_value % 2 == 0 else "treatment"

# 测试分组
print(assign_group("device_000001"))  # control
print(assign_group("device_000002"))  # treatment
```

#### 1.2 实验设计

**对照组 (Control)**:
- 不使用模型
- 随机触达用户或使用现有规则

**实验组 (Treatment)**:
- 使用模型筛选高意向用户
- 仅触达 lead_score > 0.8 的用户

#### 1.3 数据收集

```python
# 记录实验数据
experiment_log = {
    'user_id': 'device_000001',
    'group': 'treatment',
    'lead_score': 0.85,
    'contacted': True,
    'converted': False,
    'timestamp': '2026-03-01T10:00:00Z'
}

# 保存到数据库或日志文件
with open("data/experiments/ab_test_log.jsonl", "a") as f:
    f.write(json.dumps(experiment_log) + "\n")
```

### 2. 转化率分析

```python
import pandas as pd

# 加载实验数据
experiment_data = pd.read_json("data/experiments/ab_test_log.jsonl", lines=True)

# 计算各组转化率
control_data = experiment_data[experiment_data['group'] == 'control']
treatment_data = experiment_data[experiment_data['group'] == 'treatment']

control_conversion = control_data['converted'].mean()
treatment_conversion = treatment_data['converted'].mean()

print(f"对照组转化率: {control_conversion:.2%}")
print(f"实验组转化率: {treatment_conversion:.2%}")

# 计算提升
lift = (treatment_conversion - control_conversion) / control_conversion
print(f"转化率提升: {lift:.2%}")
```

### 3. 统计显著性检验

```python
from scipy.stats import chi2_contingency

# 构建列联表
contingency_table = pd.crosstab(
    experiment_data['group'],
    experiment_data['converted']
)

# 卡方检验
chi2, p_value, dof, expected = chi2_contingency(contingency_table)

print(f"卡方统计量: {chi2:.4f}")
print(f"P 值: {p_value:.4f}")

if p_value < 0.05:
    print("结果具有统计显著性（p < 0.05）")
else:
    print("结果不具有统计显著性（p >= 0.05）")
```

### 4. 样本量计算

```python
from statsmodels.stats.power import zt_ind_solve_power

# 计算所需样本量
# 假设基线转化率 5%，期望提升到 8%
baseline_rate = 0.05
treatment_rate = 0.08
effect_size = (treatment_rate - baseline_rate) / baseline_rate

required_sample_size = zt_ind_solve_power(
    effect_size=effect_size,
    alpha=0.05,  # 显著性水平
    power=0.8,   # 统计功效
    ratio=1.0    # 对照组和实验组比例
)

print(f"每组所需样本量: {int(required_sample_size)}")
print(f"总样本量: {int(required_sample_size * 2)}")
```

## 业务指标

### 1. 高意向用户识别准确率

```python
# 定义高意向用户
high_intent_users = pred_df[pred_df['lead_score'] > 0.8]

# 计算准确率
accuracy = (high_intent_users['true_label'] == 3).mean()
print(f"高意向用户识别准确率: {accuracy:.2%}")
```

**目标**: > 60%

### 2. 留资转化率提升

```python
# 对比使用模型前后的转化率
baseline_conversion = 0.05  # 基线转化率
model_conversion = treatment_conversion  # 使用模型后的转化率

lift = (model_conversion - baseline_conversion) / baseline_conversion
print(f"留资转化率提升: {lift:.2%}")
```

**目标**: > 50%

### 3. 误报率控制

```python
# 计算误报率
false_positives = pred_df[
    (pred_df['lead_score'] > 0.8) & (pred_df['true_label'] != 3)
]
false_positive_rate = len(false_positives) / len(pred_df[pred_df['lead_score'] > 0.8])

print(f"误报率: {false_positive_rate:.2%}")
```

**目标**: < 40%

### 4. 成本效益分析

```python
# 假设触达成本和转化价值
contact_cost = 1.0  # 每次触达成本（元）
conversion_value = 100.0  # 每次转化价值（元）

# 对照组成本效益
control_contacts = len(control_data[control_data['contacted']])
control_conversions = len(control_data[control_data['converted']])
control_cost = control_contacts * contact_cost
control_revenue = control_conversions * conversion_value
control_roi = (control_revenue - control_cost) / control_cost

# 实验组成本效益
treatment_contacts = len(treatment_data[treatment_data['contacted']])
treatment_conversions = len(treatment_data[treatment_data['converted']])
treatment_cost = treatment_contacts * contact_cost
treatment_revenue = treatment_conversions * conversion_value
treatment_roi = (treatment_revenue - treatment_cost) / treatment_cost

print(f"对照组 ROI: {control_roi:.2%}")
print(f"实验组 ROI: {treatment_roi:.2%}")
print(f"ROI 提升: {(treatment_roi - control_roi) / control_roi:.2%}")
```

## 持续监控

### 1. 模型性能监控

```python
# 定期计算模型性能指标
def monitor_model_performance(start_date, end_date):
    # 加载时间范围内的数据
    data = load_data(start_date, end_date)

    # 计算指标
    metrics = {
        'date_range': f"{start_date} to {end_date}",
        'precision@100': calculate_precision_at_k(data, k=100),
        'recall@100': calculate_recall_at_k(data, k=100),
        'auc': calculate_auc(data),
        'conversion_rate': calculate_conversion_rate(data)
    }

    # 保存监控结果
    with open(f"data/monitoring/{start_date}_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics

# 每周监控
weekly_metrics = monitor_model_performance("2026-02-24", "2026-03-01")
print(weekly_metrics)
```

### 2. 数据漂移检测

```python
from scipy.stats import ks_2samp

# 比较训练数据和生产数据的分布
train_scores = train_data['lead_score'].values
prod_scores = prod_data['lead_score'].values

# KS 检验
statistic, p_value = ks_2samp(train_scores, prod_scores)

print(f"KS 统计量: {statistic:.4f}")
print(f"P 值: {p_value:.4f}")

if p_value < 0.05:
    print("警告：数据分布发生显著变化，建议重新训练模型")
else:
    print("数据分布稳定")
```

### 3. 告警机制

```python
# 设置告警阈值
ALERT_THRESHOLDS = {
    'precision@100': 0.45,  # 低于 45% 告警
    'auc': 0.70,            # 低于 0.70 告警
    'conversion_rate': 0.04 # 低于 4% 告警
}

def check_alerts(metrics):
    alerts = []

    for metric, threshold in ALERT_THRESHOLDS.items():
        if metrics[metric] < threshold:
            alerts.append(f"{metric} 低于阈值: {metrics[metric]:.4f} < {threshold}")

    if alerts:
        print("⚠️ 告警:")
        for alert in alerts:
            print(f"  - {alert}")
        # 发送告警通知（邮件、Slack 等）
        send_alert_notification(alerts)
    else:
        print("✅ 所有指标正常")

# 检查告警
check_alerts(weekly_metrics)
```

## 验证脚本

完整的验证脚本位于 `scripts/validate_model.py`：

```bash
# 运行离线验证
python scripts/validate_model.py \
  --model data/models/supcon_model.pth \
  --test_data data/processed/test_labeled.csv \
  --output data/results/validation_report.json

# 运行在线验证分析
python scripts/analyze_ab_test.py \
  --experiment_data data/experiments/ab_test_log.jsonl \
  --output data/results/ab_test_report.json
```

## 最佳实践

1. **定期验证**: 每周运行离线验证，监控模型性能
2. **A/B 测试**: 新模型上线前进行 A/B 测试，确保效果提升
3. **多维度评估**: 不仅看准确率，还要看转化率、ROI 等业务指标
4. **数据质量**: 确保测试数据质量，定期清洗数据
5. **告警机制**: 设置告警阈值，及时发现模型性能下降
6. **版本管理**: 保留历史验证结果，支持模型版本对比

## 参考资料

- [模型使用指南](model_usage.md)
- [API 规范](api_spec.md)
- [架构设计](architecture.md)
