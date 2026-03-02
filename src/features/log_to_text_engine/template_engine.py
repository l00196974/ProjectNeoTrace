"""模板引擎

基于 Jinja2 的模板渲染引擎，支持自定义过滤器和函数
"""

import ast
from typing import Dict, List, Any
from jinja2 import Environment, BaseLoader


class TemplateEngine:
    """模板引擎

    支持 Jinja2 风格的模板语法，内置汽车领域相关的过滤器和函数
    """

    def __init__(self):
        self.env = Environment(loader=BaseLoader())
        self._register_filters()
        self._register_functions()

    def _register_filters(self):
        """注册内置过滤器"""
        self.env.filters['format_duration'] = self._format_duration
        self.env.filters['format_app_list'] = self._format_app_list
        self.env.filters['format_poi'] = self._format_poi
        self.env.filters['app_to_chinese'] = self._app_to_chinese

    def _register_functions(self):
        """注册内置函数"""
        self.env.globals['get_app_category'] = self._get_app_category

    def render(self, template_str: str, context: Dict[str, Any]) -> str:
        """渲染模板

        Args:
            template_str: 模板字符串
            context: 模板上下文

        Returns:
            渲染后的文本
        """
        template = self.env.from_string(template_str)
        return template.render(**context)

    def _format_duration(self, seconds: int) -> str:
        """格式化时长

        Args:
            seconds: 秒数

        Returns:
            格式化后的时长字符串
        """
        if seconds < 60:
            return f"{seconds} 秒"
        elif seconds < 3600:
            return f"{seconds // 60} 分钟"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours} 小时 {minutes} 分钟" if minutes > 0 else f"{hours} 小时"

    def _format_app_list(self, app_pkgs: List[str]) -> str:
        """格式化应用列表

        Args:
            app_pkgs: 应用包名列表

        Returns:
            格式化后的应用列表字符串
        """
        # 应用名称映射
        APP_NAME_MAP = {
            "com.autohome": "汽车之家",
            "com.yiche": "易车",
            "com.bitauto": "易车网",
            "com.xcar": "爱卡汽车",
            "com.pcauto": "太平洋汽车",
            "com.tencent.mm": "微信",
            "com.sina.weibo": "微博",
            "com.taobao.taobao": "淘宝",
            "com.jd.jdmobile": "京东",
        }

        # 转换为中文名称
        app_names = [APP_NAME_MAP.get(pkg, pkg) for pkg in app_pkgs]

        if len(app_names) == 0:
            return "应用"
        elif len(app_names) == 1:
            return app_names[0]
        elif len(app_names) == 2:
            return f"{app_names[0]} 和 {app_names[1]}"
        else:
            return f"{', '.join(app_names[:-1])} 和 {app_names[-1]}"

    def _format_poi(self, poi_list: List[str]) -> str:
        """格式化 POI 列表

        Args:
            poi_list: POI 列表

        Returns:
            格式化后的 POI 字符串
        """
        # POI 名称映射
        POI_NAME_MAP = {
            "auto_market": "汽车市场",
            "4s_store": "4S 店",
            "car_dealer": "汽车经销商",
            "repair_shop": "汽车维修店",
            "gas_station": "加油站",
            "parking_lot": "停车场",
        }

        poi_names = [POI_NAME_MAP.get(poi, poi) for poi in poi_list]
        return " → ".join(poi_names)

    def _app_to_chinese(self, pkg_name: str) -> str:
        """应用包名转中文

        Args:
            pkg_name: 应用包名

        Returns:
            中文名称
        """
        APP_NAME_MAP = {
            "com.autohome": "汽车之家",
            "com.yiche": "易车",
            "com.bitauto": "易车网",
            "com.xcar": "爱卡汽车",
            "com.pcauto": "太平洋汽车",
        }
        return APP_NAME_MAP.get(pkg_name, pkg_name)

    def _get_app_category(self, pkg_name: str) -> str:
        """获取应用类别

        Args:
            pkg_name: 应用包名

        Returns:
            应用类别
        """
        APP_CATEGORY_MAP = {
            "com.autohome": "automotive",
            "com.yiche": "automotive",
            "com.bitauto": "automotive",
            "com.xcar": "automotive",
            "com.pcauto": "automotive",
            "com.tencent.mm": "social",
            "com.sina.weibo": "social",
            "com.taobao.taobao": "shopping",
            "com.jd.jdmobile": "shopping",
        }
        return APP_CATEGORY_MAP.get(pkg_name, "other")
