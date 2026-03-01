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

### High-Level Structure

系统采用四阶段流水线架构：

1. **数据采集与切片**：基于用户全量行为序列进行清洗，完成 session 切片
2. **语义特征提取**：对各 session 进行 log-to-text 语义化和意图打标，生成向量
3. **弱监督标签挖掘**：按照车型价格区间分布构建正负样本标签
4. **对比学习训练**：通过损失函数优化向量，让正样本聚集、负样本分离

**可追溯性保障**：
- 每个环节都有 trace_id 记录
- 记录用户原始行为序列 → session 切片的映射关系
- 记录 session 切片 → 语义化内容、意图标签的映射
- 记录用户原始行为向量 → 样本标签的映射
- 支持全链路数据血缘查询

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

**Log-to-Text 转换**：
- `src/features/log_to_text.py` - 主转换逻辑
- `src/features/log_to_text_quality.py` - 质量指标计算
- `src/features/log_to_text_ab_test.py` - A/B 测试框架
- `src/features/log_to_text_feedback.py` - 反馈循环机制

**LLM 集成**：
- `src/features/llm_client.py` - LLM API 客户端
- `src/features/teacher_labeling.py` - Teacher 模型标注
- `src/features/knowledge_enhanced_labeling.py` - 知识增强标注
- `src/features/prompt_templates.py` - Prompt 模板管理

**向量生成**：
- `src/features/embedding.py` - BGE-m3 向量生成
- `src/features/intent_taxonomy.py` - 意图分类体系

**任务**：
1. **Log-to-Text 转换器**：将 pkg_name 等内部标识通过汽车本体知识库映射到语义表达
   - 示例：`com.autohome` 长时间使用 → "汽车垂直门户-深度对比"
2. **LLM 意图打标**：封装调用接口，Prompt 强制输出包含 `urgency_score` 和 `stage` 的结构化 JSON
3. **双路向量融合**：
   - 路径 1：原始 Text → BGE-m3 Embedding (V_text)
   - 路径 2：LLM Intent JSON → Embedding (V_intent)
   - 操作：Output = Concat(V_text, V_intent)

**质量保障**：
- 质量指标：语义完整性、信息密度、可读性评分
- A/B 测试：支持多版本转换策略对比
- 反馈循环：根据实际效果持续优化转换规则

**使用示例**：
```python
from src.features.log_to_text import LogToTextConverter
from src.features.teacher_labeling import TeacherLabeling
from src.features.embedding import EmbeddingGenerator

# Log-to-Text 转换
converter = LogToTextConverter()
text = converter.convert(session)

# Teacher 标注
teacher = TeacherLabeling()
intent = teacher.label(text)

# 向量生成
embedder = EmbeddingGenerator()
vector = embedder.generate(text, intent)
```

#### 模块 C：弱监督标签挖掘 (Proxy Label Miner)

基于业务规则和历史数据挖掘弱监督标签。

**技术栈**：SQL / Spark / Python

**核心文件**：
- `src/training/proxy_label_miner.py` - 标签挖掘主逻辑

**知识库**：
- `src/knowledge/automotive_ontology.py` - 汽车领域本体知识库
  - 汽车品牌层级（豪华/合资/自主）
  - 车型价格区间
  - 购车路径阶段

**任务**：
1. **Label 3 (正样本) 逻辑**：全渠道线索留资数据
2. **Label 1/2 (负样本/中性) 逻辑**：资讯活跃但非点击、留资用户

**使用示例**：
```python
from src.training.proxy_label_miner import ProxyLabelMiner

miner = ProxyLabelMiner()
labels = miner.mine_labels(sessions, lead_data)
```

#### 模块 D：对比学习训练算子 (Contrastive Learning Core)

基于 Supervised Contrastive Learning 训练向量表示。

**技术栈**：PyTorch (CPU)

**核心文件**：
- `src/training/supcon_loss.py` - SupConLoss 实现
- `src/training/projection_head.py` - 3 层 MLP Projection Head
- `src/training/trainer.py` - 训练主流程

**Student Model**（轻量级推理）：
- `src/training/intent_student_model.py` - Student 模型定义
- `src/training/train_student_model.py` - Student 训练脚本
- `src/training/distillation_loss.py` - 知识蒸馏损失函数

**任务**：
1. 实现 SupConLoss 类（温度参数 0.07）
2. 构建 Projection Head：3 层 MLP，256 维 → 128 维
3. 拉扯逻辑：同 Label 样本聚类，异类样本推开

**使用示例**：
```python
from src.training.supcon_loss import SupConLoss
from src.training.projection_head import ProjectionHead
from src.training.trainer import Trainer

# 初始化模型
projection_head = ProjectionHead(input_dim=256, output_dim=128)
loss_fn = SupConLoss(temperature=0.07)

# 训练
trainer = Trainer(projection_head, loss_fn)
trainer.train(train_data, labels)
```

#### 模块 E：在线推理服务 (Serving)

提供 RESTful API 接口进行实时推理。

**技术栈**：Flask

**核心文件**：
- `src/serving/api.py` - Flask API 服务
- `src/serving/inference.py` - 推理逻辑

**API 端点**：
- `GET /health` - 健康检查
- `POST /predict` - 单样本预测
- `POST /batch_predict` - 批量预测

**使用示例**：
```bash
# 启动服务
python src/serving/api.py

# 调用 API
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"session": {...}}'
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

#### 实时链路（生产方案）

```
端侧用户行为数据上报
  ↓
Flink 数据清洗完成 session 切片
  ↓
Flink 完成 log_to_text 以及原始向量生成
  ↓
原始向量通过新的损失函数进行纠偏，让正负样本分别聚集
  ↓
传递用户意图特征向量给推荐引擎
```

**可追溯性**：每个环节都有 trace_id 记录
**质量门禁**：每个环节都有验证检查
**异常处理**：自动检测和告警机制

#### 离线链路（验证方案）

```
现有已采集的用户历史行为数据
  ↓
Spark 数据清洗完成 session 切片
  ↓
Spark 完成 log_to_text 以及原始向量生成
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
