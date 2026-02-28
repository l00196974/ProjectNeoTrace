#!/bin/bash

# 代码质量自动检查脚本
# 运行所有代码质量检查工具

set -e

echo "=========================================="
echo "代码质量自动检查"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查结果统计
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 检查函数
check_tool() {
    local tool_name=$1
    local check_command=$2

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    echo "----------------------------------------"
    echo "检查: $tool_name"
    echo "----------------------------------------"

    if eval "$check_command"; then
        echo -e "${GREEN}✓ $tool_name 检查通过${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗ $tool_name 检查失败${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# 1. Black 格式检查
check_tool "Black (代码格式)" "black --check src/ tests/" || true

# 2. Isort 导入排序检查
check_tool "Isort (导入排序)" "isort --check-only src/ tests/" || true

# 3. Pylint 代码风格检查
check_tool "Pylint (代码风格)" "pylint src/ --exit-zero" || true

# 4. MyPy 类型检查
check_tool "MyPy (类型检查)" "mypy src/ --ignore-missing-imports" || true

# 5. Bandit 安全检查
check_tool "Bandit (安全扫描)" "bandit -r src/ -ll" || true

# 6. 单元测试
check_tool "Pytest (单元测试)" "pytest tests/ -v --tb=short" || true

# 7. 测试覆盖率
check_tool "Coverage (测试覆盖率)" "pytest --cov=src --cov-report=term-missing --cov-fail-under=80" || true

# 8. 依赖安全检查
check_tool "Pip-audit (依赖安全)" "pip-audit --desc" || true

# 总结
echo ""
echo "=========================================="
echo "检查总结"
echo "=========================================="
echo "总检查项: $TOTAL_CHECKS"
echo -e "${GREEN}通过: $PASSED_CHECKS${NC}"
echo -e "${RED}失败: $FAILED_CHECKS${NC}"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过！${NC}"
    exit 0
else
    echo -e "${RED}✗ 部分检查失败，请修复后重新运行${NC}"
    exit 1
fi
