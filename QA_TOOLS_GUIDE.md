# QA 质量保证工具使用指南

本文档介绍如何使用项目中的代码质量检查和性能测试工具。

## 目录

1. [快速开始](#快速开始)
2. [代码质量检查](#代码质量检查)
3. [性能测试](#性能测试)
4. [代码审查流程](#代码审查流程)
5. [工具配置](#工具配置)

---

## 快速开始

### 安装依赖

```bash
# 安装所有依赖（包括 QA 工具）
pip install -r requirements.txt
```

### 运行所有检查

```bash
# 运行自动化代码质量检查脚本
./scripts/check_code_quality.sh
```

---

## 代码质量检查

### 1. 代码格式检查（Black）

Black 是一个自动代码格式化工具，确保代码风格一致。

```bash
# 检查代码格式
black --check src/ tests/

# 自动修复格式问题
black src/ tests/
```

**配置文件**: `pyproject.toml` 中的 `[tool.black]` 部分

---

### 2. 导入排序检查（Isort）

Isort 自动排序和格式化 Python 导入语句。

```bash
# 检查导入排序
isort --check-only src/ tests/

# 自动修复导入排序
isort src/ tests/
```

**配置文件**: `pyproject.toml` 中的 `[tool.isort]` 部分

---

### 3. 代码风格检查（Pylint）

Pylint 检查代码风格、错误和代码复杂度。

```bash
# 检查整个项目
pylint src/

# 检查特定文件
pylint src/feature_factory/student_model.py

# 生成详细报告
pylint src/ --output-format=text > pylint_report.txt
```

**配置文件**: `.pylintrc`

**评分标准**:
- 10.0/10: 完美
- 9.0-9.9: 优秀
- 8.0-8.9: 良好
- < 8.0: 需要改进

---

### 4. 类型检查（MyPy）

MyPy 进行静态类型检查，确保类型注解正确。

```bash
# 检查整个项目
mypy src/

# 检查特定文件
mypy src/feature_factory/student_model.py

# 生成详细报告
mypy src/ --html-report mypy_report/
```

**配置文件**: `pyproject.toml` 中的 `[tool.mypy]` 部分

---

### 5. 安全检查（Bandit）

Bandit 扫描代码中的安全漏洞。

```bash
# 扫描整个项目
bandit -r src/

# 只显示高危和中危问题
bandit -r src/ -ll

# 生成 JSON 报告
bandit -r src/ -f json -o bandit_report.json
```

**常见问题**:
- B101: assert 语句
- B201: Flask debug=True
- B301: pickle 使用
- B403: import pickle

---

### 6. 依赖安全检查（Pip-audit）

Pip-audit 检查依赖包中的已知漏洞。

```bash
# 检查所有依赖
pip-audit

# 显示详细描述
pip-audit --desc

# 生成 JSON 报告
pip-audit --format json > pip_audit_report.json
```

---

## 性能测试

### 1. Student Model 推理性能测试

测试 Student Model 的推理性能，确保满足性能目标。

```bash
# 运行推理性能测试
python tests/performance/test_student_model_performance.py
```

**性能目标**:
- 单样本推理时间 < 1ms
- 批处理推理时间 < 10ms (batch_size=32)
- 内存使用 < 2GB

**输出示例**:
```
==================================================
Performance Report
==================================================
Mean:   0.856 ms
Median: 0.842 ms
P50:    0.842 ms
P95:    0.921 ms
P99:    0.987 ms
Min:    0.723 ms
Max:    1.234 ms
Std:    0.089 ms

Target: 1.000 ms - ✓ PASS
==================================================
```

---

### 2. API 延迟性能测试

测试 API 的响应延迟和吞吐量。

```bash
# 运行 API 性能测试
python tests/performance/test_api_performance.py
```

**性能目标**:
- P50 延迟 < 5ms
- P99 延迟 < 10ms
- QPS > 1000

---

### 3. 内存泄漏检测

使用 MemoryProfiler 检测内存泄漏。

```python
from tests.performance.performance_utils import MemoryProfiler

profiler = MemoryProfiler()

def your_function():
    # 你的代码
    pass

has_leak, growth = profiler.check_memory_leak(your_function, num_iterations=1000)
print(f"Memory leak: {has_leak}, Growth: {growth:.2f} MB")
```

---

## 代码审查流程

### 1. 自动化检查

在提交代码前，运行自动化检查脚本：

```bash
./scripts/check_code_quality.sh
```

### 2. 手动审查

使用代码审查检查清单进行手动审查：

- 参考 `QA_CHECKLIST.md` 中的检查项
- 重点关注核心算法和关键逻辑
- 检查可追溯性实现

### 3. 生成审查报告

使用审查报告模板记录审查结果：

- 复制 `CODE_REVIEW_REPORT_TEMPLATE.md`
- 填写审查结果和发现的问题
- 提出优化建议

### 4. 提交审查报告

将审查报告提交到 `docs/code_reviews/` 目录：

```bash
cp CODE_REVIEW_REPORT_TEMPLATE.md docs/code_reviews/review_YYYYMMDD_module_name.md
# 编辑报告
git add docs/code_reviews/review_YYYYMMDD_module_name.md
git commit -m "Add code review report for [module_name]"
```

---

## 工具配置

### Pylint 配置 (.pylintrc)

主要配置项：
- `max-line-length`: 120
- `max-args`: 7
- `max-branches`: 15
- `max-statements`: 60

### Black 配置 (pyproject.toml)

主要配置项：
- `line-length`: 120
- `target-version`: py39

### MyPy 配置 (pyproject.toml)

主要配置项：
- `python_version`: 3.9
- `disallow_untyped_defs`: true
- `warn_return_any`: true

### Pytest 配置 (pyproject.toml)

主要配置项：
- `testpaths`: ["tests"]
- `addopts`: "--cov=src --cov-report=term-missing"

---

## 持续集成（CI）

### GitHub Actions 示例

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run quality checks
        run: ./scripts/check_code_quality.sh
```

---

## 常见问题

### Q1: Black 和 Pylint 的行长度配置不一致怎么办？

A: 确保 `.pylintrc` 和 `pyproject.toml` 中的 `max-line-length` 和 `line-length` 都设置为 120。

### Q2: MyPy 报告大量 "Missing type hints" 错误怎么办？

A: 逐步添加类型注解，可以先在 `pyproject.toml` 中设置 `disallow_untyped_defs = false`，然后逐步改进。

### Q3: 性能测试失败怎么办？

A: 检查是否有其他进程占用 CPU/内存，确保在相对空闲的环境中运行测试。

### Q4: Bandit 报告误报怎么办？

A: 可以在代码中添加 `# nosec` 注释来忽略特定的警告，但要确保确实是误报。

---

## 联系方式

如有问题，请联系 QA 团队或在项目 Issue 中提问。
