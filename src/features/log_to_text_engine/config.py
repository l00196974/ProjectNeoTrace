"""配置管理

加载和验证规则配置文件
"""

import yaml
from pathlib import Path
from typing import Dict, List

# 默认配置
DEFAULT_CONFIG = {
    "rules": [
        {
            "id": "automotive_rule",
            "type": "automotive",
            "enabled": True,
            "priority": 100,
            "params": {}
        },
        {
            "id": "template_general",
            "type": "template",
            "enabled": True,
            "priority": 50,
            "params": {
                "template": "用户在 {{ session_duration | format_duration }} 内使用了 {{ app_pkg_list | format_app_list }}。",
                "match_conditions": {}
            }
        },
        {
            "id": "fallback",
            "type": "fallback",
            "enabled": True,
            "priority": 0,
            "params": {}
        }
    ],
    "execution": {
        "mode": "first_match"
    }
}


def load_config(config_path: str = None) -> Dict:
    """加载配置文件

    Args:
        config_path: 配置文件路径，如果为 None 则使用默认配置

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: 配置格式错误
    """
    if config_path is None:
        return DEFAULT_CONFIG

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 验证配置
    _validate_config(config)

    return config


def _validate_config(config: Dict):
    """验证配置格式

    Args:
        config: 配置字典

    Raises:
        ValueError: 配置格式错误
    """
    if "rules" not in config:
        raise ValueError("Config must contain 'rules' key")

    if not isinstance(config["rules"], list):
        raise ValueError("'rules' must be a list")

    for i, rule_config in enumerate(config["rules"]):
        if not isinstance(rule_config, dict):
            raise ValueError(f"Rule {i} must be a dictionary")

        if "id" not in rule_config:
            raise ValueError(f"Rule {i} must have 'id' field")

        if "type" not in rule_config:
            raise ValueError(f"Rule {i} must have 'type' field")

    # 验证执行模式
    if "execution" in config:
        mode = config["execution"].get("mode", "first_match")
        if mode not in ["first_match", "all"]:
            raise ValueError(f"Invalid execution mode: {mode}")


def save_default_config(output_path: str):
    """保存默认配置到文件

    Args:
        output_path: 输出文件路径
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(DEFAULT_CONFIG, f, allow_unicode=True, default_flow_style=False)


def create_example_config(output_path: str):
    """创建示例配置文件

    Args:
        output_path: 输出文件路径
    """
    example_config = {
        "rules": [
            {
                "id": "automotive_rule",
                "type": "automotive",
                "enabled": True,
                "priority": 100,
                "params": {},
                "description": "汽车领域专用规则（最高优先级）"
            },
            {
                "id": "template_automotive_config",
                "type": "template",
                "enabled": True,
                "priority": 90,
                "params": {
                    "template": (
                        "用户在 {{ session_duration | format_duration }} 内使用了 {{ app_pkg_list | format_app_list }}，"
                        "在配置页停留了 {{ config_page_dwell // 60 }} 分钟，"
                        "{% if lbs_poi_list %}位置：{{ lbs_poi_list | format_poi }}，{% endif %}"
                        "显示出购车配置意向。"
                    ),
                    "match_conditions": {
                        "app_category": "automotive",
                        "min_config_dwell": 60
                    }
                },
                "description": "模板规则：汽车类应用 + 配置页"
            },
            {
                "id": "template_automotive_finance",
                "type": "template",
                "enabled": True,
                "priority": 85,
                "params": {
                    "template": (
                        "用户在 {{ session_duration | format_duration }} 内使用了 {{ app_pkg_list | format_app_list }}，"
                        "在金融页停留了 {{ finance_page_dwell // 60 }} 分钟，"
                        "{% if lbs_poi_list %}位置：{{ lbs_poi_list | format_poi }}，{% endif %}"
                        "显示出汽车金融意向。"
                    ),
                    "match_conditions": {
                        "app_category": "automotive",
                        "min_finance_dwell": 30
                    }
                },
                "description": "模板规则：汽车类应用 + 金融页"
            },
            {
                "id": "template_general",
                "type": "template",
                "enabled": True,
                "priority": 50,
                "params": {
                    "template": (
                        "用户在 {{ session_duration | format_duration }} 内使用了 {{ app_pkg_list | format_app_list }}"
                        "{% if app_switch_freq > 5 %}（频繁切换，共 {{ app_switch_freq }} 次）{% endif %}"
                        "{% if lbs_poi_list %}，位置：{{ lbs_poi_list | format_poi }}{% endif %}。"
                    ),
                    "match_conditions": {}
                },
                "description": "通用模板规则"
            },
            {
                "id": "fallback",
                "type": "fallback",
                "enabled": True,
                "priority": 0,
                "params": {},
                "description": "兜底规则（最低优先级，确保全量覆盖）"
            }
        ],
        "execution": {
            "mode": "first_match"
        }
    }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(example_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
