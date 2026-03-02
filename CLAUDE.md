# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ProjectNeoTrace - 实现基于 OS 级浅层数据（App 序列、LBS、传感器）识别"汽车线索留资（Lead Generation）"高意向用户的闭环系统。利用 Log-to-Text 降维和 Supervised Contrastive Learning (SupCon) 解决数据重叠与标签缺失问题。

**系统特点**：
- Teacher-Student 架构：LLM Teacher 标注 + 轻量级 Student 模型推理
- CPU 优化：无需 GPU，适合边缘设备和大规模部署
- 多意图识别：支持购车意图的多阶段细粒度识别
- 端到端追踪：全链路 trace_id 记录，支持数据血缘分析
- 质量门禁：5 个阶段的自动化验证和异常检测

## Development Commands

### Building
```bash
# No build step required (Python project)
# Install dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_ingestion/test_session_slicer.py

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run tests in verbose mode
pytest -v

# Run specific test categories
pytest tests/test_ingestion/  # Session slicing tests
pytest tests/test_features/   # Feature extraction tests
pytest tests/test_training/   # Model training tests
```

### Linting
```bash
# Run linter (flake8)
flake8 src/ tests/

# Run code formatter (black)
black src/ tests/

# Check formatting without making changes
black --check src/ tests/
```

### Running the Application
```bash
# Development mode - Generate mock data and run training
python scripts/generate_mock_data.py
python scripts/offline_training_pipeline.py

# Log-to-Text conversion (standalone)
python scripts/convert_sessions_to_text.py \
  --input data/processed/sessions.csv \
  --output data/processed/session_texts.csv

# Use custom rule configuration
python scripts/convert_sessions_to_text.py \
  --input data/processed/sessions.csv \
  --output data/processed/session_texts.csv \
  --config config/log_to_text_rules.yaml

# Start inference API server
python src/serving/api.py

# Production mode - Run with environment variables
FLASK_HOST=0.0.0.0 FLASK_PORT=5000 FLASK_DEBUG=False python src/serving/api.py
```

### Validation and Quality Checks
```bash
# Model validation
python scripts/validate_model.py --model data/models/supcon_model.pth --test_data data/processed/test_labeled.csv

# A/B test analysis
python scripts/analyze_ab_test.py --experiment_data data/experiments/ab_test_log.jsonl

# Data quality validation (full pipeline)
python -c "from src.pipeline.validation_gates import validate_pipeline; print(validate_pipeline('data/raw/events.json'))"

# Log-to-Text quality check
python -c "from src.features.log_to_text_quality import LogToTextQualityChecker; checker = LogToTextQualityChecker(); print(checker.check_quality('session_data'))"
```

### Monitoring and Debugging
```bash
# View rule monitoring statistics
python -c "from src.ingestion.rule_engine.monitor import RuleMonitor; monitor = RuleMonitor(); print(monitor.get_statistics())"

# Generate monitoring dashboard
python -c "from src.monitoring.slicing_dashboard import SlicingDashboard; from src.ingestion.rule_engine.monitor import RuleMonitor; dashboard = SlicingDashboard(RuleMonitor()); dashboard.generate_html_report('dashboard.html')"

# View data lineage for a specific trace
python -c "from src.pipeline.e2e_tracing import E2ETracer; tracer = E2ETracer(); print(tracer.get_full_lineage('trace_id_here'))"

# Check anomaly detection status
python -c "from src.pipeline.anomaly_detection import AnomalyDetector; detector = AnomalyDetector(); print(detector.get_recent_anomalies())"
```

## Architecture

### High-Level Structure (Optimized)

**优化后的系统采用七阶段流水线架构**：

1. **数据采集与切片**：基于用户全量行为序列进行清洗，完成 session 切片
2. **Log-to-Text 转换**：使用规则引擎将 session 转换为文本描述
3. **Proxy Label 挖掘**：基于业务规则生成 lead/non-lead 二分类标签（全量数据）
4. **Teacher 标注**：LLM 对 10-20% 子集进行意图标注（分层采样）
5. **Student 训练**：轻量级模型通过知识蒸馏学习 Teacher 的意图识别能力
6. **SupCon 训练**：使用二分类 lead/non-lead 标签进行对比学习（全量数据）
7. **模型推理**：输出意图特征（概率 + 向量）和 lead 评分

**关键优化点**：
- **成本优化**：Teacher 只标注 15% 子集，降低 85% LLM 成本
- **架构简化**：Teacher 不再生成向量，只输出意图标签
- **目标对齐**：SupCon 直接优化 lead/non-lead 分离，而非意图分类
- **质量保持**：Student 通过知识蒸馏保留 Teacher 的识别能力

**可追溯性保障**：
- 每个环节都有 trace_id 记录
- 记录用户原始行为序列 → session 切片的映射关系
- 记录 session 切片 → 语义化内容、意图标签的映射
- 记录用户原始行为向量 → 样本标签的映射
- 支持全链路数据血缘查询

### Architecture Comparison

**优化前**：
```
Session Slicing → Log-to-Text → Teacher (全量, 生成向量) → Student → SupCon (意图标签) → 推理
```

**优化后**：
```
Session Slicing → Log-to-Text → Proxy Labels (全量) → Teacher (15% 子集, 只标注) → Student → SupCon (二分类标签, 全量) → 推理
```

**主要变化**：
1. Teacher 标注从全量改为 15% 子集（分层采样）
2. Teacher 输出从 4 个字段简化为 3 个字段（移除 intent_embedding）
3. SupCon 标签从 11 类意图改为 2 类 lead/non-lead
4. 推理输出强调意图特征（intent_features），lead_score 为辅助输出

### Key Components

#### 模块 A：数据采集与切片引擎 (Data Ingestion & Slicing)

基于用户原始行为序列和行为事件完成 session 切片，根据位置、时间、应用等上下文，将用户的原始序列切割成一段段的 session 切片。

**技术栈**：Flink (Java) / Spark (Java) / Python (Local)

**核心文件**：
- `src/ingestion/session_slicer.py` - Session 切片主逻辑
- `src/ingestion/state_machine.py` - 基于 did 的状态机
- `src/ingestion/feature_aggregator.py` - Session 特征聚合

**规则引擎**（6 个文件）：
- `src/ingestion/rule_engine/base.py` - 规则基类定义
- `src/ingestion/rule_engine/engine.py` - 规则引擎核心
- `src/ingestion/rule_engine/rules.py` - 内置切片规则（息屏、LBS、应用类目）
- `src/ingestion/rule_engine/registry.py` - 规则注册管理
- `src/ingestion/rule_engine/config.py` - 规则配置加载
- `src/ingestion/rule_engine/monitor.py` - 规则命中统计和监控
- `src/ingestion/rule_engine/optimizer.py` - 规则性能优化建议

**任务**：
1. 实现基于 did 的状态机，识别 Sub-session 边界
2. 切断规则：息屏 > 10min、LBS 地标跨越、应用一级类目跳变
3. 特征聚合：统计 App 切换频率、特定页面停留时长、时间张力（对数分桶）

**监控能力**：
- 规则命中统计（命中次数、命中率、平均处理时间）
- Session 质量分析（长度分布、特征完整性）
- 动态优化建议（规则顺序调整、阈值优化）

**使用示例**：
```python
from src.ingestion.session_slicer import SessionSlicer
from src.ingestion.rule_engine.engine import RuleEngine

# 初始化切片器
slicer = SessionSlicer(rule_engine=RuleEngine())

# 处理用户行为序列
sessions = slicer.slice_events(user_events)

# 查看监控统计
from src.ingestion.rule_engine.monitor import RuleMonitor
monitor = RuleMonitor()
print(monitor.get_statistics())
```

#### 模块 B：语义特征工厂 (Feature Factory & Agent)

将一个个 session 切片完成 log-to-Text 转化，提取语义特征。

**技术栈**：PySpark / Python

**核心文件**：

**Log-to-Text 转换引擎**（基于规则引擎和模板引擎）：
- `src/features/log_to_text_engine/base.py` - 基础类定义
- `src/features/log_to_text_engine/registry.py` - 规则注册表
- `src/features/log_to_text_engine/template_engine.py` - Jinja2 模板引擎
- `src/features/log_to_text_engine/rules.py` - 具体规则实现
- `src/features/log_to_text_engine/engine.py` - 执行引擎
- `src/features/log_to_text_engine/config.py` - 配置管理
- `src/features/log_to_text_engine/monitor.py` - 监控系统
- `scripts/convert_sessions_to_text.py` - 独立转换脚本

**传统 Log-to-Text 转换**（保留用于兼容）：
- `src/features/log_to_text.py` - 主转换逻辑
- `src/features/log_to_text_quality.py` - 质量指标计算
- `src/features/log_to_text_ab_test.py` - A/B 测试框架
- `src/features/log_to_text_feedback.py` - 反馈循环机制

**LLM 集成（优化后）**：
- `src/agent/llm_client.py` - LLM API 客户端
- `src/agent/teacher_labeling.py` - Teacher 模型标注（简化版）
- `src/agent/knowledge_enhanced_labeling.py` - 知识增强标注
- `src/agent/prompt_templates.py` - Prompt 模板管理

**向量生成**：
- `src/agent/embedding.py` - BGE-m3 向量生成（用于 Student 模型）
- `src/agent/intent_taxonomy.py` - 意图分类体系

**任务（优化后）**：
1. **Log-to-Text 转换引擎**：基于规则引擎和模板引擎的灵活转换系统
   - 规则引擎：支持优先级、匹配条件、自定义规则
   - 模板引擎：Jinja2 语法，支持自定义过滤器和函数
   - 兜底机制：FallbackRule 确保全量覆盖
   - 独立输出：生成 `session_texts.csv` 中间文件

2. **Teacher 意图标注（简化版）**：
   - **输入**：Session 文本（从 log-to-text 转换）
   - **输出**：
     - `intent_probs`: 11 维意图概率向量
     - `primary_intent`: 主要意图名称
     - `urgency_level`: 紧急度等级（high/medium/low）
     - `confidence`: LLM 置信度（0.0-1.0）
   - **关键变化**：
     - ❌ 不再生成 `intent_embedding`（Teacher 不生成向量）
     - ❌ 不再输出 `urgency_score`（改为 urgency_level）
     - ✅ 只标注 10-20% 子集（分层采样）
     - ✅ 成本降低 80-90%

3. **Student 向量生成**：
   - Student 模型从 Teacher 标注的子集学习
   - Student 自行生成 intent_embedding（128-dim）
   - 通过分类任务训练，不依赖 Teacher 的向量

**质量保障**：
- 规则命中统计：了解哪些规则最常用
- 转换质量监控：文本长度、成功率等指标
- A/B 测试：支持多版本转换策略对比
- 反馈循环：根据实际效果持续优化转换规则

**使用示例（优化后）**：
```python
# 使用新的规则引擎（推荐）
from src.features.log_to_text_engine import LogToTextEngine, ConversionRuleRegistry
from src.features.log_to_text_engine.rules import TemplateRule, AutomotiveRule, FallbackRule
from src.features.log_to_text_engine.config import load_config

# 注册规则类型
ConversionRuleRegistry.register("template", TemplateRule)
ConversionRuleRegistry.register("automotive", AutomotiveRule)
ConversionRuleRegistry.register("fallback", FallbackRule)

# 加载配置并创建引擎
config = load_config("config/log_to_text_rules.yaml")
rules = [ConversionRuleRegistry.create_rule(rule_config) for rule_config in config["rules"]]
engine = LogToTextEngine(rules=rules, mode=config["execution"]["mode"])

# 转换 session
result = engine.convert(session)
print(result.text)

# Teacher 标注（简化版）
from src.agent.teacher_labeling import TeacherLabeler
from src.agent.llm_client import create_llm_client

llm_client = create_llm_client(provider="openai")
teacher = TeacherLabeler(llm_client)

# 标注单个 session
label = teacher.label_session(session)
print(label["intent_probs"])      # 11-dim 概率向量
print(label["primary_intent"])    # 主要意图
print(label["urgency_level"])     # high/medium/low
print(label["confidence"])        # 0.0-1.0

# 标注设备级别（批量）
device_label = teacher.label_device(device_id, sessions)

# Student 模型推理（生成向量）
from src.model.intent_student_model import IntentStudentModel
student = IntentStudentModel(input_dim=256, hidden_dim=64, intent_dim=11, embedding_dim=128)
intent_probs, intent_embedding = student(session_features)
```

#### 模块 C：弱监督标签挖掘 (Proxy Label Miner)

基于业务规则和历史数据挖掘弱监督标签。

**技术栈**：SQL / Spark / Python

**核心文件**：
- `src/labeling/proxy_label_miner.py` - 标签挖掘主逻辑

**知识库**：
- `src/knowledge/automotive_ontology.py` - 汽车领域本体知识库
  - 汽车品牌层级（豪华/合资/自主）
  - 车型价格区间
  - 购车路径阶段

**任务（优化后）**：
1. **4 级 Proxy Label 生成**：
   - Label 0 (Noise): 无效数据
   - Label 1 (Fans): 汽车爱好者，无购车意向
   - Label 2 (Consider): 考虑购车，未采取行动
   - Label 3 (Leads): 高意向用户，已留资或到店

2. **二分类标签转换**：
   - `is_lead = 1`: Label 3（正样本）
   - `is_lead = 0`: Label 0/1/2（负样本）
   - 用于 SupCon 训练的二分类对比学习

3. **标签分布统计**：
   - 同时输出 4 级和二分类标签分布
   - 确保标签平衡性

**使用示例（优化后）**：
```python
from src.labeling.proxy_label_miner import ProxyLabelMiner

miner = ProxyLabelMiner()

# 挖掘标签（自动生成 proxy_label 和 is_lead）
labels = miner.mine_labels(sessions)

# 获取标签分布
distribution = miner.get_label_distribution(labels)
print(distribution["proxy_label"])  # 4 级分布
print(distribution["is_lead"])      # 二分类分布

# 单独转换标签
is_lead = ProxyLabelMiner.convert_to_binary_label(proxy_label=3)  # 返回 1
is_lead = ProxyLabelMiner.convert_to_binary_label(proxy_label=1)  # 返回 0
```

#### 模块 D：对比学习训练算子 (Contrastive Learning Core)

基于 Supervised Contrastive Learning 训练向量表示。

**技术栈**：PyTorch (CPU)

**核心文件**：
- `src/model/supcon_loss.py` - SupConLoss 实现
- `src/model/projection_head.py` - 3 层 MLP Projection Head
- `src/model/trainer.py` - 训练主流程（优化版）

**Student Model**（轻量级推理）：
- `src/model/intent_student_model.py` - Student 模型定义
- `src/model/train_student_model.py` - Student 训练脚本（优化版）
- `src/model/distillation_loss.py` - 知识蒸馏损失函数（简化版）

**任务（优化后）**：
1. **Student 模型训练**：
   - 从 Teacher 标注的 10-20% 子集学习
   - 只使用分类损失（移除 embedding 损失）
   - 输出：intent_probs (11-dim) + intent_embedding (128-dim)
   - Student 的 embedding 通过分类任务自行学习

2. **SupCon 训练**：
   - 使用二分类 lead/non-lead 标签（不再使用 11 类意图标签）
   - 温度参数 0.07
   - 平衡采样：确保每个 batch 中 lead/non-lead 比例均衡
   - 目标：lead 用户聚集，non-lead 用户聚集，两类分离

3. **Projection Head**：
   - 3 层 MLP：256 维 → 128 维
   - L2 归一化输出

**使用示例（优化后）**：
```python
# Student 模型训练（简化版）
from src.model.train_student_model import train_student_model_cpu, stratified_sample_for_teacher_labeling

# 分层采样（15% 子集）
sampled_df = stratified_sample_for_teacher_labeling(
    sessions_df,
    sample_ratio=0.15,
    stratify_column='proxy_label'
)

# 训练 Student（只使用分类损失）
train_student_model_cpu(
    train_data_path="teacher_labeled_subset.csv",
    model_save_path="student_model.pth",
    epochs=30,
    batch_size=32,
    learning_rate=0.001
)

# SupCon 训练（二分类标签）
from src.model.trainer import train_supcon_model_cpu

train_supcon_model_cpu(
    train_data_path="labeled_sessions.csv",  # 全量数据，包含 is_lead 列
    model_save_path="supcon_model.pth",
    epochs=30,
    batch_size=16,
    learning_rate=0.001,
    temperature=0.07,
    use_balanced_sampling=True  # 平衡采样
)

# 推理
from src.model.intent_student_model import IntentStudentModel
student = IntentStudentModel(input_dim=256, hidden_dim=64, intent_dim=11, embedding_dim=128)
intent_probs, intent_embedding = student(session_features)
```

#### 模块 E：在线推理服务 (Serving)

提供 RESTful API 接口进行实时推理。

**技术栈**：Flask

**核心文件**：
- `src/serving/api.py` - Flask API 服务（v2 API）
- `src/serving/inference.py` - 推理逻辑（优化版）

**API 端点（v2）**：
- `GET /health` - 健康检查
- `POST /predict` - 单样本预测（返回意图特征 + lead 评分）
- `POST /batch_predict` - 批量预测

**API 响应格式（v2）**：
```json
{
  "device_id": "device_000001",
  "intent_features": {
    "intent_probs": [0.8, 0.1, ...],      // 11-dim 概率向量
    "intent_embedding": [...],             // 128-dim 向量
    "primary_intent": "automotive_purchase",
    "urgency_level": "high"                // high/medium/low
  },
  "lead_score": 0.85,                      // 从对比空间计算
  "timestamp": 1234567890,
  "api_version": "v2"
}
```

**关键变化**：
- ✅ 强调 `intent_features` 输出（概率 + 向量 + 主要意图 + 紧急度）
- ✅ `lead_score` 作为辅助输出
- ✅ 添加 `api_version: "v2"` 标识
- ✅ 自动从概率提取 `primary_intent` 和 `urgency_level`

**使用示例（优化后）**：
```bash
# 启动服务
python src/serving/api.py

# 单样本预测（v2 API）
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "session": {
      "device_id": "device_001",
      "app_switch_freq": 5,
      "config_page_dwell": 180,
      "finance_page_dwell": 60,
      "session_duration": 300
    }
  }'

# 响应示例
{
  "device_id": "device_001",
  "intent_features": {
    "intent_probs": [0.8, 0.1, 0.0, ...],
    "intent_embedding": [0.23, -0.45, ...],
    "primary_intent": "automotive_purchase",
    "urgency_level": "high"
  },
  "lead_score": 0.85,
  "timestamp": 1234567890,
  "api_version": "v2"
}
```

### Support Systems

#### 数据管道可靠性系统

**核心文件**：
- `src/pipeline/validation_gates.py` - 5 个阶段的质量门禁
  - Stage 1: 原始事件验证
  - Stage 2: Session 切片验证
  - Stage 3: Log-to-Text 验证
  - Stage 4: 意图标注验证
  - Stage 5: 向量生成验证
- `src/pipeline/e2e_tracing.py` - 端到端追踪，trace_id 全链路记录
- `src/pipeline/anomaly_detection.py` - 异常检测、自动告警、模型回滚

**使用示例**：
```python
from src.pipeline.validation_gates import validate_pipeline
from src.pipeline.e2e_tracing import E2ETracer

# 全流程验证
result = validate_pipeline('data/raw/events.json')

# 查询数据血缘
tracer = E2ETracer()
lineage = tracer.get_full_lineage('trace_id_123')
```

#### 监控系统

**核心文件**：
- `src/monitoring/monitor.py` - 规则命中统计、Session 质量指标
- `src/monitoring/slicing_dashboard.py` - HTML 可视化仪表板
- `src/monitoring/optimizer.py` - 规则性能分析和优化建议

**使用示例**：
```python
from src.monitoring.slicing_dashboard import SlicingDashboard
from src.ingestion.rule_engine.monitor import RuleMonitor

# 生成监控仪表板
monitor = RuleMonitor()
dashboard = SlicingDashboard(monitor)
dashboard.generate_html_report('dashboard.html')
```

#### 知识增强系统

**核心文件**：
- `src/knowledge/automotive_ontology.py` - 汽车领域本体知识库
- `src/features/knowledge_enhanced_labeling.py` - 知识增强的 LLM 标注
- 反馈循环：根据实际结果持续更新知识库

**使用示例**：
```python
from src.knowledge.automotive_ontology import AutomotiveOntology
from src.features.knowledge_enhanced_labeling import KnowledgeEnhancedLabeling

# 加载知识库
ontology = AutomotiveOntology()

# 知识增强标注
labeler = KnowledgeEnhancedLabeling(ontology)
intent = labeler.label_with_knowledge(session)
```

### Data Flow

#### 离线训练链路（优化后）

```
1. Session 切片
   用户历史行为数据 → Session 切片器 → sessions.csv

2. Log-to-Text 转换
   sessions.csv → 规则引擎 → session_texts.csv

3. Proxy Label 挖掘（全量）
   sessions.csv → 业务规则 → labeled_sessions.csv (含 is_lead)

4. Teacher 标注（15% 子集）
   labeled_sessions.csv → 分层采样 → 15% 子集
   15% 子集 + session_texts → LLM → teacher_labeled.csv
   输出：intent_probs, primary_intent, urgency_level, confidence

5. Student 训练（知识蒸馏）
   teacher_labeled.csv → Student 模型 → student_model.pth
   损失：只使用分类损失（BCE）
   输出：intent_probs (11-dim) + intent_embedding (128-dim)

6. SupCon 训练（二分类标签，全量）
   labeled_sessions.csv (含 is_lead) → SupCon 模型 → supcon_model.pth
   标签：二分类 lead/non-lead
   采样：平衡采样确保 batch 中 lead/non-lead 比例均衡

7. 模型验证
   验证 Student 和 SupCon 模型性能
```

**关键优化点**：
- ✅ Teacher 只标注 15% 子集（成本降低 85%）
- ✅ SupCon 使用全量数据和二分类标签（更好的聚类效果）
- ✅ Student 从子集学习，泛化到全量数据
- ✅ 清晰的数据流：Proxy Labels → Teacher Subset → Student → SupCon

#### 实时推理链路（生产方案）

```
用户行为数据上报
  ↓
Session 切片（Flink/实时）
  ↓
Log-to-Text 转换（规则引擎）
  ↓
Student 模型推理
  输出：intent_probs (11-dim) + intent_embedding (128-dim)
  ↓
SupCon 模型推理
  输入：session_features (256-dim)
  输出：projection (128-dim 对比空间向量)
  ↓
计算 lead_score（与 lead 中心的相似度）
  ↓
返回结果：
  - intent_features (probs + embedding + primary_intent + urgency_level)
  - lead_score
  ↓
传递给推荐引擎/业务系统
```

**推理性能**：
- CPU 推理：<1ms
- 无需 GPU
- 适合边缘设备和大规模部署

**可追溯性**：每个环节都有 trace_id 记录
**质量门禁**：每个环节都有验证检查
**异常处理**：自动检测和告警机制
  ↓
原始向量通过新的损失函数进行纠偏，让正负样本分别聚集生成纠偏后意图向量
  ↓
引擎模型训练引入该向量，评估向量效果
```

### Important Patterns

#### 用户原始行为数据格式

不同的 action 对应不同的 payload 属性：

```json
{
  "oaid": "string",
  "timestamp": "int64",
  "app_pkg": "string",
  "action": "touch_scroll|app_foreground|.....",
  "payload": {"dwell_time": 450, "lbs_poi": "auto_market"}
}
```

#### Trace ID 格式

全链路追踪使用统一的 trace_id 格式：

```python
trace_id = f"{oaid}_{timestamp}_{session_id}"
```

## Configuration

系统提供三种部署模式：

### 1. Local 模式（本地数据功能验证）

**用途**：功能验证、开发测试

**运行方式**：
```bash
# 生成模拟数据
python scripts/generate_mock_data.py

# 运行训练流程
python scripts/offline_training_pipeline.py

# 启动推理服务
python src/serving/api.py
```

**数据来源**：使用 `generate_mock_data.py` 生成模拟数据

**特点**：
- 快速验证功能
- 无需外部依赖
- 适合开发调试

### 2. Spark 模式（历史数据批处理）

**用途**：历史数据批处理、模型训练验证

**核心逻辑**：与 Local 模式相同，运行环境不同

**注意事项**：
- 需要 Spark 环境配置（Spark 3.3+）
- 代码逻辑与 Local 模式保持一致
- 适合大规模历史数据处理

**运行方式**：
```bash
# 提交 Spark 任务
spark-submit --master yarn \
  --deploy-mode cluster \
  scripts/spark_training_pipeline.py
```

### 3. Flink 模式（生产环境实时计算）

**用途**：生产环境实时计算

**技术栈**：Java

**优先级**：低（可先不实现）

**特点**：
- 实时流处理
- 低延迟
- 高吞吐量

## Dependencies

### 核心依赖

```
Python 3.9+
torch>=1.13.0 (CPU)
sentence-transformers>=2.2.0 (BGE-m3)
flask>=2.3.0
pandas>=1.5.0
numpy>=1.23.0
scikit-learn>=1.2.0
```

### 开发依赖

```
pytest>=7.2.0
pytest-cov>=4.0.0
black>=23.0.0
flake8>=6.0.0
```

### 可选依赖

```
# Spark 模式
pyspark>=3.3.0

# Flink 模式
Apache Flink 1.15+ (Java)
```

### 安装方式

```bash
# 安装核心依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

## Common Development Tasks

### 数据生成和处理

```bash
# 生成模拟数据
python scripts/generate_mock_data.py --num_users 1000 --num_events 10000

# 运行完整训练流程
python scripts/offline_training_pipeline.py
```

### Log-to-Text 转换

```bash
# 使用默认配置转换
python scripts/convert_sessions_to_text.py \
  --input data/processed/sessions.csv \
  --output data/processed/session_texts.csv

# 使用自定义配置
python scripts/convert_sessions_to_text.py \
  --input data/processed/sessions.csv \
  --output data/processed/session_texts.csv \
  --config config/log_to_text_rules.yaml

# 不显示进度条
python scripts/convert_sessions_to_text.py \
  --input data/processed/sessions.csv \
  --output data/processed/session_texts.csv \
  --no-progress

# 生成示例配置文件
python -c "from src.features.log_to_text_engine.config import create_example_config; create_example_config('config/my_rules.yaml')"

# 测试规则引擎
python -c "
from src.features.log_to_text_engine import LogToTextEngine, ConversionRuleRegistry
from src.features.log_to_text_engine.rules import TemplateRule, AutomotiveRule, FallbackRule
from src.features.log_to_text_engine.config import load_config

# 注册规则
ConversionRuleRegistry.register('template', TemplateRule)
ConversionRuleRegistry.register('automotive', AutomotiveRule)
ConversionRuleRegistry.register('fallback', FallbackRule)

# 加载配置
config = load_config()
rules = [ConversionRuleRegistry.create_rule(r) for r in config['rules']]
engine = LogToTextEngine(rules=rules)

# 打印规则摘要
import json
print(json.dumps(engine.get_rule_summary(), indent=2))
"
```

### 模型训练和验证

```bash
# 训练 SupCon 模型
python src/training/trainer.py --data data/processed/train_labeled.csv

# 训练 Student 模型
python src/training/train_student_model.py --teacher_model data/models/supcon_model.pth

# 模型验证
python scripts/validate_model.py \
  --model data/models/supcon_model.pth \
  --test_data data/processed/test_labeled.csv
```

### A/B 测试

```bash
# 运行 A/B 测试
python scripts/run_ab_test.py \
  --variant_a baseline \
  --variant_b new_model

# 分析 A/B 测试结果
python scripts/analyze_ab_test.py \
  --experiment_data data/experiments/ab_test_log.jsonl
```

### 质量检查

```bash
# 数据质量验证（全流程）
python -c "from src.pipeline.validation_gates import validate_pipeline; print(validate_pipeline('data/raw/events.json'))"

# Log-to-Text 质量检查
python -c "from src.features.log_to_text_quality import LogToTextQualityChecker; checker = LogToTextQualityChecker(); print(checker.check_quality('session_data'))"

# Session 切片质量分析
python -c "from src.ingestion.rule_engine.monitor import RuleMonitor; monitor = RuleMonitor(); print(monitor.get_session_quality_report())"
```

### 监控和调试

```bash
# 查看规则监控统计
python -c "from src.ingestion.rule_engine.monitor import RuleMonitor; monitor = RuleMonitor(); print(monitor.get_statistics())"

# 生成监控仪表板
python -c "from src.monitoring.slicing_dashboard import SlicingDashboard; from src.ingestion.rule_engine.monitor import RuleMonitor; dashboard = SlicingDashboard(RuleMonitor()); dashboard.generate_html_report('dashboard.html')"

# 查看完整数据血缘
python -c "from src.pipeline.e2e_tracing import E2ETracer; tracer = E2ETracer(); print(tracer.get_full_lineage('trace_id_here'))"

# 检查异常检测状态
python -c "from src.pipeline.anomaly_detection import AnomalyDetector; detector = AnomalyDetector(); print(detector.get_recent_anomalies())"

# 获取规则优化建议
python -c "from src.ingestion.rule_engine.optimizer import RuleOptimizer; optimizer = RuleOptimizer(); print(optimizer.get_optimization_suggestions())"
```

### 推理服务

```bash
# 启动推理服务
python src/serving/api.py

# 健康检查
curl http://localhost:5000/health

# 单样本预测
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"session": {...}}'

# 批量预测
curl -X POST http://localhost:5000/batch_predict \
  -H "Content-Type: application/json" \
  -d '{"sessions": [...]}'
```

## Documentation

完整的文档体系位于 `docs/` 目录：

### 核心文档

- [架构设计](docs/architecture.md) - 系统整体架构和数据流
- [API 规范](docs/api_spec.md) - RESTful API 接口文档
- [部署指南](docs/deployment.md) - Local/Spark/Flink 部署方法
- [模型使用指南](docs/model_usage.md) - 模型训练和推理使用
- [验证方法论](docs/validation_methodology.md) - 离线/在线验证方法

### 快速导航

- **新手入门**：阅读 [部署指南](docs/deployment.md) 了解如何快速启动系统
- **API 集成**：参考 [API 规范](docs/api_spec.md) 了解接口调用方式
- **模型训练**：查看 [模型使用指南](docs/model_usage.md) 了解训练流程
- **系统架构**：阅读 [架构设计](docs/architecture.md) 了解整体设计
- **质量保障**：参考 [验证方法论](docs/validation_methodology.md) 了解验证策略

## Project Structure

```
ProjectNeoTrace/
├── src/
│   ├── ingestion/          # 数据采集与切片
│   │   ├── session_slicer.py
│   │   ├── state_machine.py
│   │   ├── feature_aggregator.py
│   │   └── rule_engine/    # 规则引擎
│   ├── features/           # 语义特征工厂
│   │   ├── log_to_text.py
│   │   ├── teacher_labeling.py
│   │   ├── embedding.py
│   │   └── ...
│   ├── training/           # 对比学习训练
│   │   ├── supcon_loss.py
│   │   ├── projection_head.py
│   │   ├── trainer.py
│   │   └── ...
│   ├── serving/            # 在线推理服务
│   │   ├── api.py
│   │   └── inference.py
│   ├── pipeline/           # 数据管道可靠性
│   │   ├── validation_gates.py
│   │   ├── e2e_tracing.py
│   │   └── anomaly_detection.py
│   ├── monitoring/         # 监控系统
│   │   ├── monitor.py
│   │   ├── slicing_dashboard.py
│   │   └── optimizer.py
│   └── knowledge/          # 知识库
│       └── automotive_ontology.py
├── scripts/                # 脚本工具
│   ├── generate_mock_data.py
│   ├── offline_training_pipeline.py
│   ├── validate_model.py
│   └── analyze_ab_test.py
├── tests/                  # 测试用例
├── docs/                   # 文档
├── data/                   # 数据目录
│   ├── raw/               # 原始数据
│   ├── processed/         # 处理后数据
│   ├── models/            # 模型文件
│   └── experiments/       # 实验数据
├── requirements.txt        # 依赖列表
└── CLAUDE.md              # 本文件
```

## Best Practices

### 代码规范

- 遵循 PEP 8 代码风格
- 使用 black 进行代码格式化
- 使用 flake8 进行代码检查
- 编写单元测试覆盖核心逻辑

### 数据处理

- 始终使用 trace_id 进行全链路追踪
- 在每个处理阶段添加质量验证
- 记录详细的处理日志便于调试
- 使用异常检测机制保障数据质量

### 模型训练

- 使用验证集进行超参数调优
- 定期保存模型检查点
- 记录训练指标和损失曲线
- 使用 A/B 测试验证模型效果

### 部署运维

- 使用健康检查端点监控服务状态
- 配置日志记录和告警机制
- 定期备份模型和关键数据
- 使用监控仪表板跟踪系统性能
