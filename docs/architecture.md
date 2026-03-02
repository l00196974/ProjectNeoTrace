# 架构设计文档

## 系统概述

ProjectNeoTrace 是一个基于 OS 级浅层数据的汽车线索留资识别系统，通过 Log-to-Text 降维和 Supervised Contrastive Learning (SupCon) 解决数据重叠与标签缺失问题。

## 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        原始行为数据采集                           │
│  (App 序列、LBS、传感器、息屏事件、页面停留等)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              模块 A: Session 切片引擎                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  规则引擎 (Rule Engine)                                   │   │
│  │  - 息屏 > 10min → 新 Session                             │   │
│  │  - LBS 地标跨越 → 新 Session                             │   │
│  │  - 应用类目跳变 → 新 Session                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│  输出: Session 切片 (device_id, session_id, events[])            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              模块 B: 语义特征工厂                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Log-to-Text 转换器                                       │   │
│  │  - 应用包名 → 语义化描述                                  │   │
│  │  - LBS POI → 地标名称                                     │   │
│  │  - 时长 → 自然语言表达                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Teacher Model (LLM)                                      │   │
│  │  - 离线批量标注 Session                                   │   │
│  │  - 多意图识别 (11 个类别)                                │   │
│  │  - 生成意图向量 (128-dim)                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Student Model (轻量级)                                   │   │
│  │  - 知识蒸馏，学习 Teacher 输出                            │   │
│  │  - 参数量 < 50K                                           │   │
│  │  - CPU 推理 < 1ms                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│  输出: 文本向量 (128-dim) + 意图向量 (128-dim) = 256-dim        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              模块 C: 弱监督标签挖掘                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  代理标签生成                                             │   │
│  │  - Label 3: 高意向用户 (留资/到店)                       │   │
│  │  - Label 2: 考虑购车                                     │   │
│  │  - Label 1: 汽车爱好者                                   │   │
│  │  - Label 0: 无效数据                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  输出: 带标签的训练数据 (device_id, vector, label)               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              模块 D: SupCon 对比学习                              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Projection Head (MLP)                                    │   │
│  │  - 256-dim → 128-dim 投影空间                            │   │
│  │  - 3 层 MLP                                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SupConLoss                                               │   │
│  │  - 同标签样本聚集                                         │   │
│  │  - 异标签样本推开                                         │   │
│  │  - Temperature = 0.07                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  输出: 优化后的向量空间，Label 3 中心向量                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              模块 E: 在线推理服务                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Flask API                                                │   │
│  │  - /health: 健康检查                                      │   │
│  │  - /predict: 单次预测                                     │   │
│  │  - /batch_predict: 批量预测                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  推理引擎                                                 │   │
│  │  - Student Model 生成意图向量                            │   │
│  │  - 融合文本向量 + 意图向量                               │   │
│  │  - SupCon 模型计算 lead_score                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│  输出: lead_score (0-1), intent_probs (11-dim)                   │
└─────────────────────────────────────────────────────────────────┘
```

## 数据流图

### 离线训练流程

```
原始行为序列
    │
    ├─ 可追溯性记录 (TraceabilityManager)
    │  └─ 记录原始事件 ID 和内容
    │
    ▼
Session 切片
    │
    ├─ 可追溯性记录
    │  └─ 记录 session_id → event_ids 映射
    │
    ▼
Log-to-Text 转换
    │
    ├─ 可追溯性记录
    │  └─ 记录 session_id → text 映射
    │
    ▼
LLM 意图标注 (Teacher)
    │
    ├─ 可追溯性记录
    │  └─ 记录 session_id → intent_json 映射
    │
    ▼
Student Model 训练
    │
    ├─ 知识蒸馏 (Teacher → Student)
    │  └─ 输入: Session 特征 (256-dim)
    │  └─ 输出: 意图概率 (11-dim) + 意图向量 (128-dim)
    │
    ▼
向量融合
    │
    ├─ 文本向量 (BGE-m3, 128-dim)
    ├─ 意图向量 (Student Model, 128-dim)
    └─ 融合向量 (256-dim)
    │
    ├─ 可追溯性记录
    │  └─ 记录 session_id → vector 映射
    │
    ▼
代理标签生成
    │
    ├─ Label 3: 留资用户
    ├─ Label 2: 考虑购车
    ├─ Label 1: 汽车爱好者
    └─ Label 0: 无效数据
    │
    ├─ 可追溯性记录
    │  └─ 记录 device_id → label 映射
    │
    ▼
SupCon 模型训练
    │
    ├─ 输入: 融合向量 (256-dim) + 标签
    ├─ Projection Head: 256-dim → 128-dim
    └─ SupConLoss: 同标签聚集，异标签推开
    │
    ▼
模型保存
    ├─ intent_student_model.pth
    ├─ supcon_model.pth
    └─ label_3_center.npy
```

### 在线推理流程

```
Session 数据
    │
    ▼
Log-to-Text 转换
    │
    ├─ 应用包名 → 语义化描述
    ├─ LBS POI → 地标名称
    └─ 时长 → 自然语言表达
    │
    ▼
特征提取
    │
    ├─ app_switch_freq
    ├─ config_page_dwell
    ├─ finance_page_dwell
    ├─ time_tension_bucket
    ├─ session_duration
    └─ event_count
    │
    ▼
向量生成
    │
    ├─ 文本向量: BGE-m3(session_text) → 128-dim
    ├─ 意图向量: Student Model(features) → 128-dim
    └─ 融合向量: Concat(text, intent) → 256-dim
    │
    ▼
SupCon 推理
    │
    ├─ Projection Head: 256-dim → 128-dim
    └─ 计算与 Label 3 中心的相似度
    │
    ▼
结果输出
    ├─ lead_score: 留资意向评分 (0-1)
    └─ intent_probs: 意图概率分布 (11-dim)
```

## 核心模块详解

### 模块 A: Session 切片引擎

**职责**: 将用户原始行为序列切割成有意义的 Session 片段。

**技术栈**: Python (本地/Spark), Java (Flink 实时)

**核心组件**:
- `SessionSlicer`: 主切片逻辑
- `RuleEngine`: 规则引擎，支持动态规则注册
- `SlicingRule`: 规则基类，支持自定义规则

**切片规则**:
1. **息屏规则**: 息屏 > 10min → 新 Session
2. **地标规则**: LBS 地标跨越 → 新 Session
3. **类目规则**: 应用一级类目跳变 → 新 Session

**输出格式**:
```python
{
    "device_id": "device_000001",
    "session_id": "session_000001",
    "start_time": 1709251200,
    "end_time": 1709251500,
    "events": [
        {
            "timestamp": 1709251200,
            "app_pkg": "com.autohome",
            "action": "app_foreground",
            "payload": {"dwell_time": 180}
        },
        ...
    ]
}
```

### 模块 B: 语义特征工厂

**职责**: 将 Session 切片转换为语义化文本和意图向量。

**技术栈**: Python, PyTorch, sentence-transformers

**核心组件**:

1. **Log-to-Text 转换器** (`LogToTextConverter`)
   - 应用包名映射: `com.autohome` → "汽车之家"
   - 地标映射: `auto_market` → "汽车市场"
   - 时长表达: `180` → "3 分钟"

2. **Teacher Model (LLM)**
   - 离线批量标注 Session
   - 支持多意图识别 (11 个类别)
   - 生成结构化 JSON 输出

3. **Student Model** (`IntentStudentModel`)
   - 知识蒸馏，学习 Teacher 的输出
   - 参数量 < 50K
   - CPU 推理 < 1ms

**输出格式**:
```python
{
    "session_id": "session_000001",
    "text": "用户在 5 分钟 内，使用了汽车之家，在配置页停留了 3 分钟，位置：汽车市场。",
    "text_vector": [0.1, 0.2, ...],  # 128-dim
    "intent_vector": [0.3, 0.4, ...],  # 128-dim
    "combined_vector": [0.1, 0.2, ..., 0.3, 0.4, ...]  # 256-dim
}
```

### 模块 C: 弱监督标签挖掘

**职责**: 基于用户行为特征生成代理标签。

**技术栈**: Python, Pandas

**标签定义**:
- **Label 3**: 高意向用户 (留资/到店)
- **Label 2**: 考虑购车 (多次访问汽车资讯)
- **Label 1**: 汽车爱好者 (偶尔浏览)
- **Label 0**: 无效数据 (数据质量差)

**标签生成逻辑**:
```python
def generate_label(device_sessions):
    # Label 3: 全渠道线索留资数据
    if has_lead_conversion(device_id):
        return 3

    # Label 2: 资讯活跃但非点击留资用户
    if is_active_in_auto_content(device_sessions):
        return 2

    # Label 1: 偶尔浏览汽车内容
    if has_auto_browsing(device_sessions):
        return 1

    # Label 0: 无效数据
    return 0
```

### 模块 D: SupCon 对比学习

**职责**: 使用 Supervised Contrastive Loss 优化向量空间。

**技术栈**: PyTorch (CPU)

**核心组件**:

1. **Projection Head** (`ProjectionHead`)
   - 3 层 MLP
   - 256-dim → 128-dim 投影空间
   - ReLU 激活 + Dropout

2. **SupConLoss**
   - Temperature = 0.07
   - 同标签样本聚集
   - 异标签样本推开

**训练流程**:
```python
# 1. 前向传播
projection = projection_head(combined_vector)  # [batch, 128]

# 2. 计算 SupCon Loss
loss = supcon_loss(projection, labels)

# 3. 反向传播
loss.backward()
optimizer.step()

# 4. 计算 Label 3 中心向量
label_3_center = projection[labels == 3].mean(dim=0)
```

### 模块 E: 在线推理服务

**职责**: 提供实时推理 API。

**技术栈**: Flask, PyTorch (CPU)

**核心组件**:

1. **ProductionInference**
   - 加载 Student Model 和 SupCon Model
   - 生成融合向量
   - 计算 lead_score

2. **Flask API**
   - `/health`: 健康检查
   - `/predict`: 单次预测
   - `/batch_predict`: 批量预测

**推理流程**:
```python
# 1. Log-to-Text 转换
session_text = log_to_text_converter.convert_session(session)

# 2. 生成融合向量
text_vector = bge_m3.encode(session_text)  # 128-dim
intent_vector = student_model(session_features)  # 128-dim
combined_vector = concat(text_vector, intent_vector)  # 256-dim

# 3. SupCon 推理
projection = supcon_model(combined_vector)  # 128-dim
lead_score = cosine_similarity(projection, label_3_center)

# 4. 返回结果
return {
    "lead_score": lead_score,
    "intent_probs": intent_probs
}
```

## 可追溯性系统

**职责**: 记录完整数据血缘，支持全链路追踪。

**核心组件**: `TraceabilityManager`

**追踪内容**:
1. 原始事件 → Session 切片
2. Session 切片 → Log-to-Text 文本
3. Log-to-Text 文本 → 意图标注
4. 意图标注 → 向量生成
5. 向量生成 → 标签分配

**使用示例**:
```python
# 记录原始事件
trace_manager.record_raw_event(event_id, event_data)

# 记录 Session 切片
trace_manager.record_session_slice(session_id, event_ids)

# 记录 Log-to-Text 转换
trace_manager.record_log_to_text(session_id, text)

# 查询完整血缘
lineage = trace_manager.get_full_lineage(session_id)
```

## 关键设计决策

### 1. Teacher-Student 架构

**问题**: LLM 推理成本高，无法在线使用。

**解决方案**:
- Teacher Model (LLM) 离线批量标注
- Student Model (轻量级) 在线推理
- 知识蒸馏，Student 学习 Teacher 的输出

**优势**:
- 降低在线推理成本
- 保持标注质量
- 支持 CPU 推理

### 2. 双路向量融合

**问题**: 单一文本向量无法捕捉用户意图。

**解决方案**:
- 路径 1: 文本向量 (BGE-m3, 128-dim)
- 路径 2: 意图向量 (Student Model, 128-dim)
- 融合: Concat(text, intent) → 256-dim

**优势**:
- 文本向量捕捉语义信息
- 意图向量捕捉行为模式
- 融合向量更全面

### 3. SupCon 对比学习

**问题**: 标签缺失，数据重叠。

**解决方案**:
- 使用代理标签 (Label 0-3)
- SupCon Loss 优化向量空间
- 同标签样本聚集，异标签样本推开

**优势**:
- 解决标签缺失问题
- 提升向量区分度
- 支持弱监督学习

### 4. CPU 优化

**问题**: GPU 成本高，不适合大规模部署。

**解决方案**:
- 所有模型支持 CPU 训练和推理
- Student Model 参数量 < 50K
- 推理延迟 < 1ms

**优势**:
- 降低部署成本
- 支持大规模部署
- 无需 GPU 资源

## 性能指标

### 训练性能 (CPU)
- Session 切片: 1000 设备 < 5 分钟
- LLM 标注: 1000 Session < 30 分钟
- Student Model 训练: 100 样本 < 1 小时
- SupCon 训练: 100 样本 < 1 小时

### 推理性能 (CPU)
- Student Model 推理: < 1ms
- API P50 延迟: < 5ms
- API P99 延迟: < 10ms
- 批量预测吞吐: 100 sessions/秒

### 模型效果
- Precision@100: > 50%
- LLM 解析成功率: > 95%
- Student-Teacher 一致性: > 80%

## 部署架构

### 本地模式 (Local)
```
用户 → Flask API → ProductionInference → 模型文件
```

### Spark 模式 (离线批处理)
```
历史数据 → Spark Job → Session 切片 → Log-to-Text → 向量生成 → 模型训练
```

### Flink 模式 (实时流处理)
```
实时数据流 → Flink Job → Session 切片 → Log-to-Text → 向量生成 → 推理服务
```

## 扩展性设计

### 规则引擎扩展
- 支持动态规则注册
- 支持规则优先级调整
- 支持规则启用/禁用

### 意图类别扩展
- 支持新增意图类别
- 支持意图权重调整
- 支持意图层级结构

### 模型扩展
- 支持多模型并行
- 支持 A/B 测试
- 支持模型热更新

## 安全性考虑

### 数据隐私
- 所有请求数据仅用于推理，不持久化存储
- 支持数据脱敏
- 支持数据加密传输

### 模型安全
- 模型文件权限控制
- 防止模型逆向工程
- 支持模型签名验证

## 监控和日志

### 监控指标
- API 请求量和延迟
- 模型推理时间
- 错误率和异常
- 资源使用情况

### 日志记录
- 请求日志
- 推理日志
- 错误日志
- 审计日志
