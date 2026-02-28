# QA 工具快速设置指南

本指南帮助开发人员快速设置代码质量检查工具。

## 1. 安装依赖

```bash
# 安装所有依赖（包括 QA 工具）
pip install -r requirements.txt
```

## 2. 设置 Pre-commit Hooks

Pre-commit hooks 会在每次 `git commit` 前自动运行代码质量检查。

```bash
# 安装 pre-commit hooks
pre-commit install

# 手动运行所有 hooks（测试配置）
pre-commit run --all-files
```

### Pre-commit 包含的检查：
- ✅ Black - 代码格式化
- ✅ Isort - 导入排序
- ✅ Flake8 - 代码风格检查
- ✅ MyPy - 类型检查
- ✅ Bandit - 安全扫描
- ✅ 文件大小检查
- ✅ YAML/JSON 语法检查
- ✅ 敏感信息检测

### 跳过 Pre-commit（紧急情况）：
```bash
git commit --no-verify -m "Emergency fix"
```

## 3. 手动运行代码质量检查

如果不想使用 pre-commit hooks，可以手动运行检查：

```bash
# 运行所有检查（推荐）
./scripts/check_code_quality.sh

# 或者单独运行各个工具
black --check src/ tests/
isort --check-only src/ tests/
pylint src/
mypy src/
bandit -r src/ -ll
pytest --cov=src
```

## 4. 自动修复代码格式

```bash
# 自动修复代码格式
black src/ tests/

# 自动修复导入排序
isort src/ tests/
```

## 5. 运行性能测试

```bash
# Student Model 推理性能测试
python tests/performance/test_student_model_performance.py

# API 延迟性能测试
python tests/performance/test_api_performance.py
```

## 6. 查看测试覆盖率

```bash
# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html

# 在浏览器中查看报告
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 7. 性能目标

确保你的代码满足以下性能目标：

| 指标 | 目标 |
|------|------|
| Student Model 推理时间 | < 1ms |
| API P99 延迟 | < 10ms |
| 内存使用 | < 2GB |
| 测试覆盖率 | > 80% |
| Pylint 评分 | > 8.0/10 |

## 8. 常见问题

### Q: Pre-commit 检查失败怎么办？
A: 根据错误信息修复代码，或运行自动修复工具（black, isort）。

### Q: MyPy 报告类型错误怎么办？
A: 添加类型注解或使用 `# type: ignore` 注释（谨慎使用）。

### Q: 如何更新 pre-commit hooks？
A: 运行 `pre-commit autoupdate`。

### Q: 如何临时禁用某个检查？
A: 编辑 `.pre-commit-config.yaml`，注释掉对应的 hook。

## 9. 推荐的开发工作流

1. **开发前**：确保 pre-commit hooks 已安装
2. **开发中**：定期运行 `black` 和 `isort` 保持代码整洁
3. **提交前**：pre-commit 会自动运行检查
4. **提交后**：CI/CD 会运行完整的测试套件

## 10. IDE 集成

### VS Code
安装以下扩展：
- Python (Microsoft)
- Pylance
- Black Formatter
- isort

在 `.vscode/settings.json` 中配置：
```json
{
  "python.formatting.provider": "black",
  "python.linting.pylintEnabled": true,
  "python.linting.enabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm
1. Settings → Tools → Black → Enable
2. Settings → Tools → External Tools → 添加 isort
3. Settings → Editor → Inspections → 启用 Pylint

## 11. 更多文档

- 完整 QA 工具指南：`QA_TOOLS_GUIDE.md`
- 代码审查检查清单：`QA_CHECKLIST.md`
- 代码审查报告模板：`CODE_REVIEW_REPORT_TEMPLATE.md`
- QA 工作总结：`QA_WORK_SUMMARY.md`

---

**提示**：保持代码质量是团队的共同责任。如有问题，请联系 QA 团队。
