"""具体转换规则实现

包含模板规则、汽车领域规则和兜底规则
"""

import ast
import logging
from typing import Dict, List, Any
from .base import BaseConversionRule, ConversionContext, ConversionResult
from .template_engine import TemplateEngine

logger = logging.getLogger(__name__)


class TemplateRule(BaseConversionRule):
    """基于模板的转换规则

    使用 Jinja2 模板引擎进行文本生成
    """

    def __init__(
        self,
        rule_id: str,
        priority: int = 50,
        enabled: bool = True,
        params: Dict[str, Any] = None
    ):
        super().__init__(rule_id, priority, enabled, params)
        self.template_engine = TemplateEngine()
        self.template_str = params.get("template", "")
        self.match_conditions = params.get("match_conditions", {})

    def match(self, context: ConversionContext) -> bool:
        """判断是否匹配

        根据 match_conditions 检查 session 是否满足条件
        """
        session = context.session

        # 检查匹配条件
        for key, condition in self.match_conditions.items():
            if key == "app_category":
                # 检查应用类别
                app_pkgs = self._parse_list(session.get("app_pkg_list", []))
                categories = [self.template_engine._get_app_category(pkg) for pkg in app_pkgs]
                if condition not in categories:
                    return False

            elif key == "min_duration":
                if session.get("session_duration", 0) < condition:
                    return False

            elif key == "min_config_dwell":
                if session.get("config_page_dwell", 0) < condition:
                    return False

            elif key == "min_finance_dwell":
                if session.get("finance_page_dwell", 0) < condition:
                    return False

            elif key == "has_poi":
                poi_list = self._parse_list(session.get("lbs_poi_list", []))
                if not poi_list:
                    return False

        return True

    def convert(self, context: ConversionContext) -> ConversionResult:
        """执行转换"""
        try:
            session = context.session

            # 准备模板上下文
            template_context = {
                **session,
                # 解析列表字段
                "app_pkg_list": self._parse_list(session.get("app_pkg_list", [])),
                "lbs_poi_list": self._parse_list(session.get("lbs_poi_list", [])),
            }

            # 渲染模板
            text = self.template_engine.render(self.template_str, template_context)

            return ConversionResult(
                success=True,
                text=text.strip(),
                rule_id=self.rule_id,
                priority=self.priority
            )

        except Exception as e:
            logger.warning(f"TemplateRule {self.rule_id} conversion failed: {e}")
            return ConversionResult(
                success=False,
                text="",
                rule_id=self.rule_id,
                priority=self.priority,
                metadata={"error": str(e)}
            )

    def _parse_list(self, value):
        """解析列表字段"""
        if isinstance(value, str):
            try:
                return ast.literal_eval(value)
            except:
                return []
        return value if isinstance(value, list) else []


class AutomotiveRule(BaseConversionRule):
    """汽车领域专用规则

    针对汽车相关 session 的专用转换逻辑
    """

    def __init__(
        self,
        rule_id: str,
        priority: int = 100,
        enabled: bool = True,
        params: Dict[str, Any] = None
    ):
        super().__init__(rule_id, priority, enabled, params)
        self.template_engine = TemplateEngine()

    def match(self, context: ConversionContext) -> bool:
        """判断是否为汽车相关 session"""
        session = context.session
        app_pkgs = self._parse_list(session.get("app_pkg_list", []))

        # 检查是否包含汽车类应用
        automotive_apps = ["com.autohome", "com.yiche", "com.bitauto", "com.xcar", "com.pcauto"]
        return any(pkg in automotive_apps for pkg in app_pkgs)

    def convert(self, context: ConversionContext) -> ConversionResult:
        """汽车领域专用转换"""
        try:
            session = context.session

            # 提取关键信息
            duration = session.get("session_duration", 0)
            app_pkgs = self._parse_list(session.get("app_pkg_list", []))
            poi_list = self._parse_list(session.get("lbs_poi_list", []))
            config_dwell = session.get("config_page_dwell", 0)
            finance_dwell = session.get("finance_page_dwell", 0)
            app_switch_freq = session.get("app_switch_freq", 0)

            # 构建文本
            parts = []

            # 1. 时长和应用
            duration_text = self.template_engine._format_duration(duration)
            app_text = self._format_automotive_apps(app_pkgs)
            parts.append(f"用户在 {duration_text} 内{app_text}")

            # 2. 应用切换频率
            if app_switch_freq > 5:
                parts.append(f"频繁切换，共 {app_switch_freq} 次")

            # 3. 特殊页面停留
            if config_dwell > 0:
                parts.append(f"在配置页停留了 {config_dwell // 60} 分钟")
            if finance_dwell > 0:
                parts.append(f"在金融页停留了 {finance_dwell // 60} 分钟")

            # 4. 地理位置
            if poi_list:
                poi_text = self.template_engine._format_poi(poi_list)
                parts.append(f"位置：{poi_text}")

            # 5. 购车意向判断
            intent_level = self._infer_intent_level(config_dwell, finance_dwell, poi_list)
            if intent_level:
                parts.append(intent_level)

            text = "，".join(parts) + "。"

            return ConversionResult(
                success=True,
                text=text,
                rule_id=self.rule_id,
                priority=self.priority,
                metadata={"domain": "automotive"}
            )

        except Exception as e:
            logger.warning(f"AutomotiveRule conversion failed: {e}")
            return ConversionResult(
                success=False,
                text="",
                rule_id=self.rule_id,
                priority=self.priority,
                metadata={"error": str(e)}
            )

    def _format_automotive_apps(self, app_pkgs: List[str]) -> str:
        """格式化汽车应用"""
        app_names = [
            self.template_engine._app_to_chinese(pkg)
            for pkg in app_pkgs
            if self.template_engine._get_app_category(pkg) == "automotive"
        ]

        if len(app_names) == 0:
            return "使用了汽车应用"
        elif len(app_names) == 1:
            return f"使用了 {app_names[0]}"
        elif len(app_names) == 2:
            return f"使用了 {app_names[0]} 和 {app_names[1]}"
        else:
            return f"使用了 {', '.join(app_names[:-1])} 和 {app_names[-1]}"

    def _infer_intent_level(
        self,
        config_dwell: int,
        finance_dwell: int,
        poi_list: List[str]
    ) -> str:
        """推断购车意向等级"""
        # 高意向：配置页 + 金融页 + 4S 店
        if config_dwell > 120 and finance_dwell > 60 and "4s_store" in poi_list:
            return "显示出强烈的购车意向"

        # 中意向：配置页或金融页 + 汽车市场
        if (config_dwell > 60 or finance_dwell > 30) and "auto_market" in poi_list:
            return "显示出一定的购车意向"

        # 低意向：仅浏览配置
        if config_dwell > 30:
            return "处于信息收集阶段"

        return ""

    def _parse_list(self, value):
        """解析列表字段"""
        if isinstance(value, str):
            try:
                return ast.literal_eval(value)
            except:
                return []
        return value if isinstance(value, list) else []


class FallbackRule(BaseConversionRule):
    """兜底规则

    确保所有 session 都能生成文本
    """

    def __init__(
        self,
        rule_id: str = "fallback",
        priority: int = 0,
        enabled: bool = True,
        params: Dict[str, Any] = None
    ):
        super().__init__(rule_id, priority, enabled, params)
        self.template_engine = TemplateEngine()

    def match(self, context: ConversionContext) -> bool:
        """总是匹配"""
        return True

    def convert(self, context: ConversionContext) -> ConversionResult:
        """生成通用文本"""
        try:
            session = context.session

            duration = session.get("session_duration", 0)
            event_count = session.get("event_count", 0)
            app_pkgs = self._parse_list(session.get("app_pkg_list", []))

            # 构建简单描述
            duration_text = self.template_engine._format_duration(duration)

            if app_pkgs:
                app_text = self.template_engine._format_app_list(app_pkgs)
                text = f"用户在 {duration_text} 内使用了 {app_text}，产生了 {event_count} 个事件。"
            else:
                text = f"用户活动了 {duration_text}，产生了 {event_count} 个事件。"

            return ConversionResult(
                success=True,
                text=text,
                rule_id=self.rule_id,
                priority=self.priority,
                metadata={"fallback": True}
            )

        except Exception as e:
            logger.warning(f"FallbackRule conversion failed: {e}")
            # 即使兜底规则失败，也返回一个最基本的文本
            return ConversionResult(
                success=True,
                text="用户进行了一段活动。",
                rule_id=self.rule_id,
                priority=self.priority,
                metadata={"fallback": True, "error": str(e)}
            )

    def _parse_list(self, value):
        """解析列表字段"""
        if isinstance(value, str):
            try:
                return ast.literal_eval(value)
            except:
                return []
        return value if isinstance(value, list) else []
