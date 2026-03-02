# 模型使用指南

## 概述

本文档介绍如何使用训练好的 ProjectNeoTrace 模型进行汽车留资意向识别。

## 模型架构

ProjectNeoTrace 使用 Teacher-Student 架构和对比学习：

```
Session 数据
    ↓
[Student Model] → 意图向量 (128-dim)
    ↓
[文本向量 (128-dim)] + [意图向量 (128-dim)] = 融合向量 (256-dim)
    ↓
[SupCon Model] → 投影向量 (128-dim)
    ↓
与 Label 3 中心计算相似度 → lead_score (0-1)
```

## 训练后的模型文件

训练完成后，会生成以下模型文件：

```
data/models/
├── intent_student_model.pth      # Student Model 权重
├── supcon_model.pth               # SupCon Model 权重
└── label_3_center.npy             # Label 3 中心向量
```

## 加载训练好的模型

### 方法 1: 使用 ProductionInference 类

```python
from src.serving.inference import ProductionInference

# 初始化推理引擎
inference = ProductionInference(
    student_model_path="data/models/intent_student_model.pth",
    supcon_model_path="data/models/supcon_model.pth",
    use_mock_embedding=False  # 使用真实的 BGE-m3 向量化器
)

# 准备 Session 数据
session_text = "用户在 5 分钟 内，使用了汽车之家，在配置页停留了 3 分钟，位置：汽车市场。"
session_features = np.array([
    5.0,    # app_switch_freq
    3.0,    # config_page_dwell (分钟)
    1.0,    # finance_page_dwell (分钟)
    2.0,    # time_tension_bucket
    5.0,    # session_duration (小时)
    0.2,    # event_count (归一化)
] + [0.0] * 250)  # 填充到 256 维

# 预测
result = inference.predict_lead_score(session_text, session_features)

print(f"Lead Score: {result['lead_score']:.4f}")
print(f"意图概率: {result['intent_probs']}")
```

### 方法 2: 手动加载模型

```python
import torch
from src.model.intent_student_model import IntentStudentModel
from src.model.projection_head import ProjectionHead

# 加载 Student Model
student_model = IntentStudentModel(
    input_dim=256,
    hidden_dim=64,
    intent_dim=11,
    embedding_dim=128
)
student_model.load_state_dict(
    torch.load("data/models/intent_student_model.pth", map_location="cpu")
)
student_model.eval()

# 加载 SupCon Model
supcon_model = ProjectionHead(
    input_dim=256,
    hidden_dim=128,
    output_dim=128
)
supcon_model.load_state_dict(
    torch.load("data/models/supcon_model.pth", map_location="cpu")
)
supcon_model.eval()

# 加载 Label 3 中心向量
label_3_center = np.load("data/models/label_3_center.npy")
label_3_center = torch.tensor(label_3_center, dtype=torch.float32)
```

## 进行推理

### 单个 Session 推理

```python
import numpy as np
import torch

# 1. 准备输入数据
session_text = "用户在汽车之家浏览了 5 款 SUV，停留 10 分钟"
session_features = np.random.randn(256)  # 实际应该是真实特征

# 2. 生成文本向量
from src.agent.embedding import create_text_embedding
text_embedding = create_text_embedding(use_mock=False)
text_vector = text_embedding.encode(session_text, normalize=True)
text_vector_128 = text_embedding.reduce_dimension(text_vector, target_dim=128)

# 3. 生成意图向量
with torch.no_grad():
    x = torch.tensor(session_features, dtype=torch.float32).unsqueeze(0)
    intent_probs, intent_vector = student_model(x)
    intent_vector = intent_vector.squeeze(0).numpy()

# 4. 融合向量
combined_vector = np.concatenate([text_vector_128, intent_vector])

# 5. SupCon 推理
with torch.no_grad():
    x = torch.tensor(combined_vector, dtype=torch.float32).unsqueeze(0)
    projection = supcon_model(x).squeeze(0)

    # 计算与 Label 3 中心的相似度
    similarity = torch.cosine_similarity(
        projection.unsqueeze(0),
        label_3_center.unsqueeze(0)
    )
    lead_score = (similarity.item() + 1) / 2  # 归一化到 [0, 1]

print(f"Lead Score: {lead_score:.4f}")
print(f"意图概率: {intent_probs.squeeze(0).numpy()}")
```

### 批量推理

```python
# 准备批量数据
batch_texts = [
    "用户在汽车之家浏览了 5 款 SUV",
    "用户在易车网查看了金融方案",
    "用户在汽车市场停留了 30 分钟"
]
batch_features = np.random.randn(3, 256)

# 批量推理
results = []
for text, features in zip(batch_texts, batch_features):
    result = inference.predict_lead_score(text, features)
    results.append(result)

# 输出结果
for i, result in enumerate(results):
    print(f"Session {i+1}: Lead Score = {result['lead_score']:.4f}")
```

## 结果解释

### lead_score 含义

`lead_score` 是一个 0 到 1 之间的浮点数，表示用户的留资意向强度：

- **0.8 - 1.0**: 高意向用户，强烈推荐触达
- **0.6 - 0.8**: 中高意向用户，建议触达
- **0.4 - 0.6**: 中等意向用户，可选择性触达
- **0.0 - 0.4**: 低意向用户，不建议触达

**计算方法**:
```python
# 1. SupCon 模型将融合向量投影到 128 维空间
projection = supcon_model(combined_vector)

# 2. 计算投影向量与 Label 3 中心向量的余弦相似度
similarity = cosine_similarity(projection, label_3_center)  # [-1, 1]

# 3. 归一化到 [0, 1]
lead_score = (similarity + 1) / 2
```

### intent_probs 含义

`intent_probs` 是一个 11 维数组，表示用户在各个意图类别上的概率分布：

```python
intent_categories = [
    "购车意图",      # 索引 0
    "金融意图",      # 索引 1
    "外卖意图",      # 索引 2
    "出行意图",      # 索引 3
    "娱乐意图",      # 索引 4
    "社交意图",      # 索引 5
    "购物意图",      # 索引 6
    "新闻意图",      # 索引 7
    "工具意图",      # 索引 8
    "教育意图",      # 索引 9
    "其他意图"       # 索引 10
]

# 示例输出
intent_probs = [0.68, 0.12, 0.05, 0.03, 0.02, 0.01, 0.04, 0.02, 0.01, 0.01, 0.01]
# 解释: 购车意图 68%, 金融意图 12%, 外卖意图 5%, ...
```

**使用建议**:
- 关注购车意图（索引 0）和金融意图（索引 1）的概率
- 如果购车意图 > 0.5，说明用户有明确的购车需求
- 如果金融意图 > 0.3，说明用户关注购车金融方案

## 模型评估

### 离线评估

使用历史留资数据评估模型准确性：

```python
from src.utils.metrics import compute_metrics, compute_ranking_metrics

# 准备测试数据
test_data = pd.read_csv("data/processed/test_labeled.csv")

# 批量预测
predictions = []
for _, row in test_data.iterrows():
    result = inference.predict_lead_score(
        row['session_text'],
        row['session_features']
    )
    predictions.append(result['lead_score'])

# 计算指标
y_true = test_data['label'].values
y_pred = np.array(predictions)

# 分类指标（使用阈值 0.6）
metrics = compute_metrics(y_true, y_pred > 0.6)
print(f"Precision: {metrics['precision']:.4f}")
print(f"Recall: {metrics['recall']:.4f}")
print(f"F1 Score: {metrics['f1']:.4f}")

# 排序指标
ranking_metrics = compute_ranking_metrics(y_true, y_pred)
print(f"Precision@100: {ranking_metrics['precision@100']:.4f}")
print(f"Recall@100: {ranking_metrics['recall@100']:.4f}")
```

### 在线 A/B 测试

```python
# 1. 将用户随机分为对照组和实验组
import random

def assign_group(user_id):
    return "control" if hash(user_id) % 2 == 0 else "treatment"

# 2. 对照组：不使用模型
# 3. 实验组：使用模型筛选高意向用户

# 4. 统计转化率
control_conversion_rate = 0.05  # 对照组转化率
treatment_conversion_rate = 0.08  # 实验组转化率

# 5. 计算提升
lift = (treatment_conversion_rate - control_conversion_rate) / control_conversion_rate
print(f"转化率提升: {lift * 100:.2f}%")
```

### 业务指标

**关键指标**:
1. **高意向用户识别准确率**: 模型预测为高意向的用户中，实际留资的比例
2. **留资转化率提升**: 使用模型后，留资转化率相比基线的提升
3. **误报率**: 模型预测为高意向但实际未留资的比例

**计算方法**:
```python
# 1. 高意向用户识别准确率
high_intent_users = y_pred > 0.8
precision_at_high_intent = (y_true[high_intent_users] == 3).mean()
print(f"高意向用户识别准确率: {precision_at_high_intent:.2%}")

# 2. 留资转化率提升
baseline_conversion = 0.05  # 基线转化率
model_conversion = 0.08     # 使用模型后的转化率
lift = (model_conversion - baseline_conversion) / baseline_conversion
print(f"留资转化率提升: {lift:.2%}")

# 3. 误报率
false_positive_rate = ((y_pred > 0.8) & (y_true != 3)).mean()
print(f"误报率: {false_positive_rate:.2%}")
```

## 模型更新

### 何时更新模型

建议在以下情况下更新模型：

1. **数据分布变化**: 用户行为模式发生显著变化
2. **模型效果下降**: Precision@100 下降超过 5%
3. **新增意图类别**: 需要识别新的用户意图
4. **定期更新**: 每月或每季度定期重新训练

### 更新流程

```bash
# 1. 收集新的训练数据
python scripts/collect_training_data.py \
  --start_date 2026-02-01 \
  --end_date 2026-03-01 \
  --output data/raw/new_events.json

# 2. 重新训练模型
python scripts/offline_training_pipeline.py \
  --input data/raw/new_events.json \
  --output data/models/

# 3. 评估新模型
python scripts/validate_model.py \
  --model data/models/supcon_model.pth \
  --test_data data/processed/test_labeled.csv

# 4. 如果新模型效果更好，替换旧模型
mv data/models/supcon_model.pth data/models/supcon_model_v2.pth
mv data/models/intent_student_model.pth data/models/intent_student_model_v2.pth

# 5. 重启推理服务
pkill -f "python src/serving/api.py"
python src/serving/api.py
```

## 模型调优

### 调整阈值

根据业务需求调整 lead_score 阈值：

```python
# 高精度模式（减少误报）
high_precision_threshold = 0.8

# 高召回模式（减少漏报）
high_recall_threshold = 0.5

# 平衡模式
balanced_threshold = 0.6

# 使用阈值
high_intent_users = y_pred > high_precision_threshold
```

### 调整意图权重

如果某些意图更重要，可以调整权重：

```python
# 定义意图权重
intent_weights = np.array([
    2.0,  # 购车意图（权重加倍）
    1.5,  # 金融意图（权重增加 50%）
    0.5,  # 外卖意图（权重减半）
    1.0,  # 其他意图（保持不变）
    1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
])

# 加权意图概率
weighted_intent_probs = intent_probs * intent_weights
weighted_intent_probs /= weighted_intent_probs.sum()

# 重新计算 lead_score
# （需要重新训练模型以使用加权意图）
```

## 常见问题

### Q1: lead_score 总是很低怎么办？

**可能原因**:
1. Label 3 中心向量未正确加载
2. 训练数据中 Label 3 样本太少
3. 特征提取有问题

**解决方案**:
```python
# 检查 Label 3 中心向量
label_3_center = np.load("data/models/label_3_center.npy")
print(f"Label 3 中心向量范数: {np.linalg.norm(label_3_center)}")

# 如果范数接近 0，说明中心向量有问题
# 重新计算中心向量
from src.model.train_supcon import compute_label_centers
label_centers = compute_label_centers(train_loader, supcon_model)
np.save("data/models/label_3_center.npy", label_centers[3])
```

### Q2: 如何处理新的应用包名？

**解决方案**:
```python
# 在 src/agent/log_to_text.py 中添加新的映射
APP_NAME_MAP = {
    "com.autohome": "汽车之家",
    "com.yiche": "易车网",
    "com.new_app": "新应用名称",  # 添加新映射
}
```

### Q3: 如何提升模型效果？

**建议**:
1. **增加训练数据**: 收集更多 Label 3 样本
2. **改进特征工程**: 添加更多有区分度的特征
3. **调整模型参数**: 增加隐藏层维度或层数
4. **使用更好的 LLM**: 使用更强的 LLM 进行 Teacher 标注
5. **优化 Log-to-Text**: 改进语义转换质量

### Q4: 如何在生产环境部署？

参考 [部署指南](deployment.md) 中的 Docker 部署章节。

## 最佳实践

1. **定期评估**: 每周评估模型效果，监控 Precision@100
2. **A/B 测试**: 新模型上线前进行 A/B 测试
3. **数据质量**: 确保训练数据质量，定期清洗数据
4. **特征监控**: 监控特征分布，检测数据漂移
5. **模型版本管理**: 保留历史模型版本，支持快速回滚

## 参考资料

- [API 规范](api_spec.md)
- [架构设计](architecture.md)
- [部署指南](deployment.md)
- [验证方法论](validation_methodology.md)
