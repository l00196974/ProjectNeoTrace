# ProjectNeoTrace 测试文档

## 测试概览

本项目包含完整的单元测试套件，覆盖所有核心模块。目标覆盖率 > 80%。

## 测试结构

```
tests/
├── conftest.py                          # Pytest 全局配置和 fixtures
├── test_ingestion/                      # 模块 A：Session 切片测试
│   ├── __init__.py
│   └── test_session_slicer.py
├── test_agent/                          # 模块 B：LLM 标注和 Student Model 测试
│   ├── __init__.py
│   └── test_feature_factory.py
├── test_labeling/                       # 模块 C：标签挖掘测试
│   ├── __init__.py
│   └── test_proxy_labeler.py
├── test_model/                          # 模块 D：SupCon 训练测试
│   ├── __init__.py
│   └── test_supcon_training.py
└── test_serving/                        # 模块 E：API 接口测试
    ├── __init__.py
    └── test_inference_api.py
```

## 运行测试

### 运行所有测试
```bash
pytest
```

### 运行特定模块测试
```bash
# Session 切片测试
pytest tests/test_ingestion/

# LLM 标注测试
pytest tests/test_agent/

# 标签挖掘测试
pytest tests/test_labeling/

# SupCon 训练测试
pytest tests/test_model/

# API 接口测试
pytest tests/test_serving/
```

### 运行单个测试文件
```bash
pytest tests/test_ingestion/test_session_slicer.py
```

### 运行单个测试用例
```bash
pytest tests/test_ingestion/test_session_slicer.py::TestSessionSlicer::test_session_boundary_by_screen_off
```

### 生成覆盖率报告
```bash
# 终端输出
pytest --cov=src --cov-report=term-missing

# HTML 报告
pytest --cov=src --cov-report=html
# 报告位置：htmlcov/index.html

# XML 报告（CI/CD）
pytest --cov=src --cov-report=xml
```

### 使用测试脚本
```bash
# 运行所有测试
python run_tests.py

# 运行特定模块
python run_tests.py tests/test_ingestion/
```

## 测试分类

### 单元测试（Unit Tests）
测试单个函数或类的功能。

```bash
pytest -m unit
```

### 集成测试（Integration Tests）
测试多个模块之间的交互。

```bash
pytest -m integration
```

### 性能测试（Performance Tests）
测试性能指标（延迟、吞吐量）。

```bash
pytest -m performance
```

### 慢速测试（Slow Tests）
跳过慢速测试以加快开发迭代。

```bash
pytest -m "not slow"
```

## 测试覆盖范围

### 模块 A：Session 切片引擎
- ✅ 息屏 > 10min 切断规则
- ✅ LBS 地标跨越切断规则
- ✅ 应用类目跳变切断规则
- ✅ 特征聚合（App 切换频率、停留时长、时间张力）
- ✅ 多设备隔离

### 模块 B：语义特征工厂
- ✅ Log-to-Text 转换
- ✅ LLM 意图打标
- ✅ 双路向量融合
- ✅ Student Model 推理速度 < 1ms
- ✅ Student-Teacher 一致性 > 80%

### 模块 C：弱监督标签挖掘
- ✅ Label 3（正样本）：短信/通话检测
- ✅ Label 1（负样本）：资讯活跃无通讯
- ✅ Label 2（中性样本）
- ✅ Label 0（噪声样本）
- ✅ 隐私合规（不存储明文）

### 模块 D：SupCon 对比学习
- ✅ SupConLoss 计算逻辑
- ✅ 同标签样本吸引
- ✅ 不同标签样本排斥
- ✅ Projection Head 架构
- ✅ 训练流程
- ✅ 梯度流动

### 模块 E：在线推理服务
- ✅ API 端点可用性
- ✅ P99 延迟 < 10ms
- ✅ 吞吐量 > 100 QPS
- ✅ Redis 缓存
- ✅ gRPC 接口
- ✅ 错误处理

## 验证标准

### 功能验证
- ✅ 全链路打通，无阻塞环节
- ✅ LLM 解析成功率 > 95%
- ✅ Student Model 与 Teacher 一致性 > 80%

### 性能验证
- ✅ Student Model 推理 < 1ms（CPU）
- ✅ P99 延迟 < 10ms
- ✅ 吞吐量 > 100 QPS

### 质量验证
- ✅ Precision@100 > 50%
- ✅ 代码覆盖率 > 80%

## 持续集成

### GitHub Actions 配置示例
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
      - name: Run tests
        run: |
          pytest --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## 注意事项

1. **TODO 标记**：当前测试中包含 `TODO` 注释，表示需要在实现对应模块后取消注释。
2. **模拟测试**：部分测试使用模拟数据，实际实现后需要替换为真实逻辑。
3. **性能测试**：性能测试需要在接近生产环境的配置下运行。
4. **隐私合规**：所有涉及敏感数据的测试必须确保不存储明文。

## 故障排查

### 测试失败
```bash
# 显示详细错误信息
pytest -vv

# 显示完整堆栈跟踪
pytest --tb=long

# 在第一个失败时停止
pytest -x
```

### 覆盖率不足
```bash
# 查看未覆盖的代码行
pytest --cov=src --cov-report=term-missing

# 生成 HTML 报告查看详情
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### 性能测试超时
```bash
# 增加超时时间
pytest --timeout=300
```

## 贡献指南

添加新测试时：
1. 在对应模块的测试目录下创建测试文件
2. 使用 `Test*` 类名和 `test_*` 函数名
3. 添加清晰的文档字符串
4. 确保测试可重复运行
5. 运行 `pytest` 确保所有测试通过
6. 检查覆盖率是否达标
