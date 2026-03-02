# Log-to-Text 转换引擎

基于规则引擎和模板引擎的灵活 Session 文本转换系统。

## 概述

Log-to-Text 转换引擎将用户行为 Session 数据转换为自然语言文本描述，支持：

- **规则引擎**：基于优先级的规则匹配和执行
- **模板引擎**：Jinja2 语法，支持自定义过滤器和函数
- **兜底机制**：FallbackRule 确保全量覆盖
- **监控系统**：规则命中统计、转换质量监控
- **配置驱动**：通过 YAML 配置文件管理规则

## 架构

```
LogToTextEngine (执行引擎)
├── TemplateRule (模板规则)
│   └── TemplateEngine (Jinja2 模板引擎)
├── AutomotiveRule (汽车领域专用规则)
└── FallbackRule (兜底规则)

ConversionRuleRegistry (规则注册表)
└── 工厂方法：从配置创建规则实例

ConversionMonitor (监控系统)
└── 统计规则命中率、转换质量
```

## 快速开始

### 1. 基本使用

```python
from src.features.log_to_text_engine import (
    LogToTextEngine,
    ConversionRuleRegistry,
    TemplateRule,
    AutomotiveRule,
    FallbackRule
)
from src.features.log_to_text_engine.config import load_config

# 注册规则类型
ConversionRuleRegistry.register("template", TemplateRule)
ConversionRuleRegistry.register("automotive", AutomotiveRule)
ConversionRuleRegistry.register("fallback", FallbackRule)

# 加载配置并创建引擎
config = load_config()  # 使用默认配置
rules = [ConversionRuleRegistry.create_rule(r) for r in config["rules"]]
engine = LogToTextEngine(rules=rules, mode=config["execution"]["mode"])

# 转换 session
session = {
    "device_id": "device_001",
    "session_id": "session_001",
    "session_duration": 600,
    "app_pkg_list": ["com.autohome", "com.yiche"],
    "lbs_poi_list": ["auto_market"],
    "config_page_dwell": 120,
    "finance_page_dwell": 0,
    "app_switch_freq": 3,
    "event_count": 20
}

result = engine.convert(session)
print(result.text)
# 输出: "用户在 10 分钟 内使用了 汽车之家 和 易车，在配置页停留了 2 分钟，位置：汽车市场，处于信息收集阶段。"
```

### 2. 使用命令行工具

```bash
# 转换 sessions.csv 为 session_texts.csv
python scripts/convert_sessions_to_text.py \
  --input data/processed/sessions.csv \
  --output data/processed/session_texts.csv

# 使用自定义配置
python scripts/convert_sessions_to_text.py \
  --input data/processed/sessions.csv \
  --output data/processed/session_texts.csv \
  --config config/log_to_text_rules.yaml
```

## 规则系统

### 内置规则

1. **AutomotiveRule** (优先级: 100)
   - 匹配条件：包含汽车类应用
   - 转换逻辑：汽车领域专用文本生成
   - 意图推断：根据配置页、金融页、POI 推断购车意向

2. **TemplateRule** (优先级: 50)
   - 匹配条件：可配置（应用类别、时长、POI 等）
   - 转换逻辑：基于 Jinja2 模板渲染

3. **FallbackRule** (优先级: 0)
   - 匹配条件：总是匹配
   - 转换逻辑：生成通用文本描述

### 自定义规则

```python
from src.features.log_to_text_engine.base import BaseConversionRule, ConversionContext, ConversionResult

class CustomRule(BaseConversionRule):
    """自定义规则"""

    def match(self, context: ConversionContext) -> bool:
        """判断是否匹配"""
        # 自定义匹配逻辑
        return True

    def convert(self, context: ConversionContext) -> ConversionResult:
        """执行转换"""
        session = context.session
        text = f"自定义文本: {session['device_id']}"

        return ConversionResult(
            success=True,
            text=text,
            rule_id=self.rule_id,
            priority=self.priority
        )

# 注册自定义规则
ConversionRuleRegistry.register("custom", CustomRule)
```

## 模板引擎

### 内置过滤器

- `format_duration`: 格式化时长（秒 → "X 分钟"）
- `format_app_list`: 格式化应用列表（包名 → 中文名）
- `format_poi`: 格式化 POI 列表
- `app_to_chinese`: 应用包名转中文

### 内置函数

- `get_app_category`: 获取应用类别

### 模板示例

```jinja2
用户在 {{ session_duration | format_duration }} 内使用了 {{ app_pkg_list | format_app_list }}
{% if app_switch_freq > 5 %}（频繁切换，共 {{ app_switch_freq }} 次）{% endif %}
{% if config_page_dwell > 0 %}，在配置页停留了 {{ config_page_dwell // 60 }} 分钟{% endif %}
{% if lbs_poi_list %}，位置：{{ lbs_poi_list | format_poi }}{% endif %}。
```

## 配置文件

### 配置格式

```yaml
rules:
  # 汽车领域专用规则
  - id: automotive_rule
    type: automotive
    enabled: true
    priority: 100
    params: {}

  # 模板规则
  - id: template_general
    type: template
    enabled: true
    priority: 50
    params:
      template: |
        用户在 {{ session_duration | format_duration }} 内使用了 {{ app_pkg_list | format_app_list }}。
      match_conditions: {}

  # 兜底规则
  - id: fallback
    type: fallback
    enabled: true
    priority: 0
    params: {}

execution:
  mode: first_match  # 或 "all"
```

### 生成示例配置

```python
from src.features.log_to_text_engine.config import create_example_config

create_example_config("config/my_rules.yaml")
```

## 监控系统

### 使用监控器

```python
from src.features.log_to_text_engine.monitor import ConversionMonitor

monitor = ConversionMonitor()

# 在转换过程中记录
result = engine.convert(session)
monitor.record_conversion(result, duration_ms=1.5)

# 获取统计信息
stats = monitor.get_statistics()
print(f"总转换次数: {stats['total_conversions']}")
print(f"平均转换时间: {stats['avg_conversion_time_ms']:.2f} ms")
print(f"平均文本长度: {stats['avg_text_length']:.1f} 字符")

# 打印摘要
monitor.print_summary()
```

### 监控指标

- 总转换次数
- 规则命中统计（次数、命中率）
- 转换时间（平均、P95、P99）
- 文本长度（平均、最小、最大）
- 失败次数和失败率

## 输出格式

转换后的 `session_texts.csv` 包含以下字段：

| 字段 | 说明 |
|------|------|
| device_id | 设备 ID |
| session_id | Session ID |
| session_text | 生成的文本 |
| matched_rule | 匹配的规则 ID |
| rule_priority | 规则优先级 |
| session_duration | Session 时长（秒） |
| app_count | 应用数量 |
| poi_count | POI 数量 |
| event_count | 事件数量 |
| app_switch_freq | 应用切换频率 |
| config_page_dwell | 配置页停留时长（秒） |
| finance_page_dwell | 金融页停留时长（秒） |

## 测试

```bash
# 运行测试
python tests/test_log_to_text_engine.py

# 或使用 pytest
pytest tests/test_log_to_text_engine.py -v
```

## 性能

- 平均转换时间：< 1 ms/session
- 支持大规模批量转换（10 万+ sessions）
- 内存占用：取决于规则数量和模板复杂度

## 扩展性

### 添加新规则

1. 继承 `BaseConversionRule`
2. 实现 `match()` 和 `convert()` 方法
3. 注册规则类型
4. 在配置文件中使用

### 添加新过滤器

```python
from src.features.log_to_text_engine.template_engine import TemplateEngine

engine = TemplateEngine()

# 添加自定义过滤器
def custom_filter(value):
    return f"自定义: {value}"

engine.env.filters['custom'] = custom_filter
```

## 最佳实践

1. **规则优先级**：高质量规则使用高优先级（100+），通用规则使用中等优先级（50），兜底规则使用最低优先级（0）
2. **模板设计**：保持模板简洁，避免过于复杂的逻辑
3. **监控统计**：定期查看规则命中率，优化规则配置
4. **配置管理**：使用版本控制管理配置文件，便于回滚
5. **测试验证**：添加新规则后进行充分测试

## 故障排查

### 问题：转换结果为空

- 检查规则是否启用（`enabled: true`）
- 检查匹配条件是否正确
- 查看日志中的警告信息

### 问题：规则未命中

- 检查规则优先级顺序
- 验证匹配条件逻辑
- 使用监控系统查看规则命中统计

### 问题：模板渲染错误

- 检查模板语法是否正确
- 验证上下文变量是否存在
- 查看错误日志中的详细信息

## 相关文档

- [CLAUDE.md](../../CLAUDE.md) - 项目整体文档
- [config/log_to_text_rules.yaml](../../config/log_to_text_rules.yaml) - 示例配置文件
- [scripts/convert_sessions_to_text.py](../../scripts/convert_sessions_to_text.py) - 转换脚本
