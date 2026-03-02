"""
配置管理 - 支持从 YAML 文件或字典加载规则配置
"""

import logging
from typing import Dict, Any, List
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)


class RuleConfig:
    """规则配置管理"""

    @staticmethod
    def load_from_yaml(config_path: str) -> Dict[str, Any]:
        """
        从 YAML 文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            配置字典

        Raises:
            FileNotFoundError: 配置文件不存在
            ValueError: 配置格式错误
        """
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config:
                raise ValueError("配置文件为空")

            # 验证配置
            RuleConfig.validate_config(config)

            logger.info(f"成功加载配置: {config_path}")
            return config

        except yaml.YAMLError as e:
            raise ValueError(f"YAML 解析错误: {str(e)}")
        except Exception as e:
            raise ValueError(f"配置加载失败: {str(e)}")

    @staticmethod
    def load_from_dict(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        从字典加载配置

        Args:
            config: 配置字典

        Returns:
            验证后的配置字典

        Raises:
            ValueError: 配置格式错误
        """
        RuleConfig.validate_config(config)
        logger.info("成功加载字典配置")
        return config

    @staticmethod
    def validate_config(config: Dict[str, Any]):
        """
        验证配置格式

        Args:
            config: 配置字典

        Raises:
            ValueError: 配置格式错误
        """
        if not isinstance(config, dict):
            raise ValueError("配置必须是字典类型")

        # 验证 rules 字段
        if "rules" not in config:
            raise ValueError("配置缺少 'rules' 字段")

        rules = config["rules"]
        if not isinstance(rules, list):
            raise ValueError("'rules' 必须是列表类型")

        if len(rules) == 0:
            raise ValueError("'rules' 列表不能为空")

        # 验证每个规则
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise ValueError(f"规则 {i} 必须是字典类型")

            # 必需字段
            required_fields = ["id", "type"]
            for field in required_fields:
                if field not in rule:
                    raise ValueError(f"规则 {i} 缺少必需字段: {field}")

            # 可选字段类型检查
            if "enabled" in rule and not isinstance(rule["enabled"], bool):
                raise ValueError(f"规则 {i} 的 'enabled' 必须是布尔类型")

            if "priority" in rule and not isinstance(rule["priority"], (int, float)):
                raise ValueError(f"规则 {i} 的 'priority' 必须是数字类型")

            if "params" in rule and not isinstance(rule["params"], dict):
                raise ValueError(f"规则 {i} 的 'params' 必须是字典类型")

        # 验证 execution 字段
        if "execution" in config:
            execution = config["execution"]
            if not isinstance(execution, dict):
                raise ValueError("'execution' 必须是字典类型")

            if "mode" in execution:
                valid_modes = ["chain", "all"]
                if execution["mode"] not in valid_modes:
                    raise ValueError(f"'execution.mode' 必须是 {valid_modes} 之一")

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """
        获取默认配置

        Returns:
            默认配置字典
        """
        return {
            "rules": [
                {
                    "id": "screen_off_rule",
                    "type": "screen_off",
                    "enabled": True,
                    "priority": 100,
                    "params": {
                        "threshold_seconds": 600
                    }
                },
                {
                    "id": "lbs_crossing_rule",
                    "type": "lbs_crossing",
                    "enabled": True,
                    "priority": 50,
                    "params": {
                        "poi_hierarchy": {
                            "home": 1,
                            "office": 1,
                            "auto_market": 2,
                            "4s_store": 2,
                            "shopping_mall": 1,
                            "restaurant": 1,
                            "gas_station": 1,
                        }
                    }
                },
                {
                    "id": "app_category_rule",
                    "type": "app_category_change",
                    "enabled": True,
                    "priority": 30,
                    "params": {
                        "category_map": {
                            "com.autohome": "automotive",
                            "com.yiche": "automotive",
                            "com.bitauto": "automotive",
                            "com.xcar": "automotive",
                            "com.pcauto": "automotive",
                            "com.tencent.mm": "social",
                            "com.tencent.mobileqq": "social",
                            "com.sina.weibo": "social",
                            "com.tencent.wework": "social",
                            "com.sankuai.meituan": "food_delivery",
                            "me.ele": "food_delivery",
                            "com.taobao.taobao": "shopping",
                            "com.jingdong.app.mall": "shopping",
                            "com.xunmeng.pinduoduo": "shopping",
                            "com.ss.android.ugc.aweme": "entertainment",
                            "com.tencent.qqlive": "entertainment",
                            "com.youku.phone": "entertainment",
                            "com.tencent.wemoney.app": "finance",
                            "com.eg.android.AlipayGphone": "finance",
                            "com.chinamworld.main": "finance",
                        }
                    }
                }
            ],
            "execution": {
                "mode": "chain"
            }
        }
