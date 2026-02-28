# ProjectNeoTrace

基于 OS 级浅层数据的汽车线索留资识别系统

## 项目概述

ProjectNeoTrace 是一个利用用户行为序列数据识别汽车购买高意向用户的系统。通过 Log-to-Text 降维和 Supervised Contrastive Learning (SupCon) 解决数据重叠与标签缺失问题。

### 核心特性

- **多意图识别**：支持同时识别多个用户意图（购车、金融、外卖等）
- **Teacher-Student 架构**：LLM 作为 Teacher 离线标注，轻量级 Student Model 在线推理
- **CPU 优化**：无需 GPU，CPU 训练和推理
- **对比学习**：使用 SupCon Loss 优化向量空间，让正负样本分别聚集

## 系统架构

```
原始日志 → Session 切片 → LLM 标注（Teacher）→ Student Model 训练
                                                    ↓
                                            意图向量生成
                                                    ↓
                                    文本向量 + 意图向量融合（256-dim）
                                                    ↓
                                            SupCon 模型训练
                                                    ↓
                                            在线推理服务
```

## 快速开始

### 环境要求

- Python 3.9+
- CPU（无需 GPU）
- 8GB+ RAM

### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入 LLM API Key
# OPENAI_API_KEY=your_key_here
```

### 运行完整流程

```bash
# 1. 生成模拟数据
python scripts/generate_mock_data.py

# 2. 运行完整训练流程
python scripts/offline_training_pipeline.py

# 3. 启动推理服务
python src/serving/api.py
```

### 测试 API

```bash
curl -X POST http://localhost:5000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "session_text": "用户在汽车之家浏览了 5 款 SUV",
    "session_features": [0.1, 0.2, 0.3, ...]
  }'
```

## 项目结构

```
ProjectNeoTrace/
├── src/
│   ├── ingestion/          # 模块 A：Session 切片引擎
│   ├── agent/              # 模块 B：语义特征工厂
│   ├── labeling/           # 模块 C：弱监督标签挖掘
│   ├── model/              # 模块 D：对比学习训练
│   ├── serving/            # 模块 E：在线推理服务
│   └── utils/              # 通用工具
├── scripts/                # 脚本工具
├── tests/                  # 测试代码
├── data/                   # 数据目录
├── docs/                   # 文档
└── requirements.txt        # 依赖列表
```

## 核心模块

### 模块 A：Session 切片引擎

将用户原始行为序列切割成有意义的 Session 片段。

**切片规则**：
- 息屏 > 10min → 新 Session
- LBS 地标跨越 → 新 Session
- 应用类目跳变 → 新 Session

### 模块 B：语义特征工厂

**Teacher Model（LLM）**：
- 离线批量标注 Session
- 支持多意图识别（11 个意图类别）
- 生成意图向量（128-dim）

**Student Model（轻量级）**：
- 知识蒸馏，学习 Teacher 的输出
- 参数量 < 50K
- CPU 推理 < 1ms

### 模块 C：弱监督标签挖掘

基于用户行为特征生成代理标签：
- Label 3：高意向用户（留资/到店）
- Label 2：考虑购车
- Label 1：汽车爱好者
- Label 0：无效数据

### 模块 D：SupCon 对比学习

使用 Supervised Contrastive Loss 优化向量空间：
- 同标签样本聚集
- 异标签样本推开
- CPU 训练（30 epochs，约 1-2 小时）

### 模块 E：在线推理服务

Flask API 提供实时推理：
- Student Model 生成意图向量
- 融合文本向量 + 意图向量
- SupCon 模型计算 lead_score

## 性能指标

### MVP 目标

- ✅ Student Model 推理 < 1ms（CPU）
- ✅ API P99 延迟 < 10ms
- ✅ Precision@100 > 50%
- ✅ LLM 解析成功率 > 95%
- ✅ Student-Teacher 一致性 > 80%

### 训练时间（CPU）

- Session 切片：1000 设备 < 5 分钟
- LLM 标注：1000 Session < 30 分钟
- Student Model 训练：100 样本 < 1 小时
- SupCon 训练：100 样本 < 1 小时

## 开发指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_ingestion/test_session_slicer.py

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

### 代码格式化

```bash
# 使用 black 格式化代码
black src/ tests/

# 使用 flake8 检查代码
flake8 src/ tests/
```

## Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动推理服务
docker-compose up neotrace-api

# 运行训练流程
docker-compose --profile training up neotrace-training
```

## 技术栈

- **深度学习**：PyTorch (CPU)
- **向量化**：sentence-transformers (BGE-m3)
- **数据处理**：Pandas, NumPy
- **Web 服务**：Flask
- **LLM API**：OpenAI / Anthropic

## 文档

- [架构设计](docs/architecture.md)
- [API 规范](docs/api_spec.md)
- [部署指南](docs/deployment.md)

## 许可证

MIT License

## 联系方式

ProjectNeoTrace Team
