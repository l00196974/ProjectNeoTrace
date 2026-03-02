"""
测试配置管理
"""

import pytest
import tempfile
from pathlib import Path
from src.ingestion.rule_engine.config import RuleConfig


class TestRuleConfig:
    """测试规则配置管理"""

    def test_load_from_yaml_success(self):
        """测试成功加载 YAML 配置"""
        yaml_content = """
rules:
  - id: test_rule
    type: test_type
    enabled: true
    priority: 100
    params:
      key: value

execution:
  mode: chain
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            config = RuleConfig.load_from_yaml(temp_path)

            assert "rules" in config
            assert len(config["rules"]) == 1
            assert config["rules"][0]["id"] == "test_rule"
            assert config["execution"]["mode"] == "chain"
        finally:
            Path(temp_path).unlink()

    def test_load_from_yaml_file_not_found(self):
        """测试配置文件不存在"""
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            RuleConfig.load_from_yaml("/nonexistent/path.yaml")

    def test_load_from_yaml_empty_file(self):
        """测试空配置文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="配置文件为空"):
                RuleConfig.load_from_yaml(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_from_yaml_invalid_yaml(self):
        """测试无效的 YAML 格式"""
        yaml_content = """
rules:
  - id: test
    invalid yaml: [
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="YAML 解析错误"):
                RuleConfig.load_from_yaml(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_from_dict_success(self):
        """测试从字典加载配置"""
        config_dict = {
            "rules": [
                {
                    "id": "test_rule",
                    "type": "test_type",
                    "enabled": True,
                    "priority": 100,
                }
            ],
            "execution": {"mode": "chain"}
        }

        config = RuleConfig.load_from_dict(config_dict)

        assert config == config_dict

    def test_validate_config_missing_rules(self):
        """测试缺少 rules 字段"""
        config = {"execution": {"mode": "chain"}}

        with pytest.raises(ValueError, match="缺少 'rules' 字段"):
            RuleConfig.validate_config(config)

    def test_validate_config_rules_not_list(self):
        """测试 rules 不是列表"""
        config = {"rules": "not a list"}

        with pytest.raises(ValueError, match="'rules' 必须是列表类型"):
            RuleConfig.validate_config(config)

    def test_validate_config_empty_rules(self):
        """测试空 rules 列表"""
        config = {"rules": []}

        with pytest.raises(ValueError, match="'rules' 列表不能为空"):
            RuleConfig.validate_config(config)

    def test_validate_config_rule_not_dict(self):
        """测试规则不是字典"""
        config = {"rules": ["not a dict"]}

        with pytest.raises(ValueError, match="规则 0 必须是字典类型"):
            RuleConfig.validate_config(config)

    def test_validate_config_rule_missing_id(self):
        """测试规则缺少 id 字段"""
        config = {"rules": [{"type": "test_type"}]}

        with pytest.raises(ValueError, match="规则 0 缺少必需字段: id"):
            RuleConfig.validate_config(config)

    def test_validate_config_rule_missing_type(self):
        """测试规则缺少 type 字段"""
        config = {"rules": [{"id": "test_rule"}]}

        with pytest.raises(ValueError, match="规则 0 缺少必需字段: type"):
            RuleConfig.validate_config(config)

    def test_validate_config_enabled_not_bool(self):
        """测试 enabled 不是布尔类型"""
        config = {
            "rules": [
                {
                    "id": "test_rule",
                    "type": "test_type",
                    "enabled": "true"
                }
            ]
        }

        with pytest.raises(ValueError, match="'enabled' 必须是布尔类型"):
            RuleConfig.validate_config(config)

    def test_validate_config_priority_not_number(self):
        """测试 priority 不是数字"""
        config = {
            "rules": [
                {
                    "id": "test_rule",
                    "type": "test_type",
                    "priority": "high"
                }
            ]
        }

        with pytest.raises(ValueError, match="'priority' 必须是数字类型"):
            RuleConfig.validate_config(config)

    def test_validate_config_params_not_dict(self):
        """测试 params 不是字典"""
        config = {
            "rules": [
                {
                    "id": "test_rule",
                    "type": "test_type",
                    "params": "not a dict"
                }
            ]
        }

        with pytest.raises(ValueError, match="'params' 必须是字典类型"):
            RuleConfig.validate_config(config)

    def test_validate_config_execution_not_dict(self):
        """测试 execution 不是字典"""
        config = {
            "rules": [{"id": "test_rule", "type": "test_type"}],
            "execution": "not a dict"
        }

        with pytest.raises(ValueError, match="'execution' 必须是字典类型"):
            RuleConfig.validate_config(config)

    def test_validate_config_invalid_execution_mode(self):
        """测试无效的 execution mode"""
        config = {
            "rules": [{"id": "test_rule", "type": "test_type"}],
            "execution": {"mode": "invalid"}
        }

        with pytest.raises(ValueError, match="'execution.mode' 必须是"):
            RuleConfig.validate_config(config)

    def test_validate_config_not_dict(self):
        """测试配置不是字典"""
        with pytest.raises(ValueError, match="配置必须是字典类型"):
            RuleConfig.validate_config("not a dict")

    def test_get_default_config(self):
        """测试获取默认配置"""
        config = RuleConfig.get_default_config()

        assert "rules" in config
        assert "execution" in config
        assert len(config["rules"]) == 3
        assert config["execution"]["mode"] == "chain"

        # 验证三个内置规则
        rule_ids = [r["id"] for r in config["rules"]]
        assert "screen_off_rule" in rule_ids
        assert "lbs_crossing_rule" in rule_ids
        assert "app_category_rule" in rule_ids

    def test_default_config_is_valid(self):
        """测试默认配置是有效的"""
        config = RuleConfig.get_default_config()

        # 不应该抛出异常
        RuleConfig.validate_config(config)
