"""Log-to-Text 转换模块

将 Session 事件序列转换为自然语言描述。
"""

from typing import Dict, List
from src.ingestion.state_machine import APP_CATEGORY_MAP


# 应用包名到中文名称的映射
APP_NAME_MAP = {
    # 汽车类
    "com.autohome": "汽车之家",
    "com.yiche": "易车",
    "com.bitauto": "懂车帝",
    "com.xcar": "爱卡汽车",
    "com.pcauto": "太平洋汽车",
    # 社交类
    "com.tencent.mm": "微信",
    "com.tencent.mobileqq": "QQ",
    "com.sina.weibo": "微博",
    "com.tencent.wework": "企业微信",
    # 外卖类
    "com.sankuai.meituan": "美团",
    "me.ele": "饿了么",
    # 电商类
    "com.taobao.taobao": "淘宝",
    "com.jingdong.app.mall": "京东",
    "com.xunmeng.pinduoduo": "拼多多",
    # 娱乐类
    "com.ss.android.ugc.aweme": "抖音",
    "com.tencent.qqlive": "腾讯视频",
    "com.youku.phone": "优酷",
    # 金融类
    "com.tencent.wemoney.app": "微信支付",
    "com.eg.android.AlipayGphone": "支付宝",
    "com.chinamworld.main": "中国银行",
}

# POI 类型到中文名称的映射
POI_NAME_MAP = {
    "home": "住宅",
    "office": "办公室",
    "auto_market": "汽车市场",
    "4s_store": "4S 店",
    "shopping_mall": "商场",
    "restaurant": "餐厅",
    "gas_station": "加油站",
}


class LogToTextConverter:
    """Log-to-Text 转换器"""

    def __init__(self):
        pass

    def convert_session(self, session: Dict) -> str:
        """
        将 Session 转换为自然语言描述

        Args:
            session: Session 字典

        Returns:
            自然语言描述
        """
        # 提取关键信息
        device_id = session.get("device_id", "")
        session_duration = session.get("session_duration", 0)
        app_switch_freq = session.get("app_switch_freq", 0)
        config_page_dwell = session.get("config_page_dwell", 0)
        finance_page_dwell = session.get("finance_page_dwell", 0)
        lbs_poi_list = session.get("lbs_poi_list", [])
        app_pkg_list = session.get("app_pkg_list", [])
        event_count = session.get("event_count", 0)

        # 构建描述
        parts = []

        # 1. 时长描述
        duration_text = self._format_duration(session_duration)
        parts.append(f"用户在 {duration_text} 内")

        # 2. 应用使用描述
        app_text = self._format_app_usage(app_pkg_list, app_switch_freq)
        parts.append(app_text)

        # 3. 特殊页面停留描述
        if config_page_dwell > 0:
            config_minutes = config_page_dwell // 60
            parts.append(f"在配置页停留了 {config_minutes} 分钟")

        if finance_page_dwell > 0:
            finance_minutes = finance_page_dwell // 60
            parts.append(f"在金融页停留了 {finance_minutes} 分钟")

        # 4. 地理位置描述
        if lbs_poi_list:
            poi_text = self._format_poi_list(lbs_poi_list)
            parts.append(f"位置：{poi_text}")

        # 5. 活跃度描述
        if event_count > 50:
            parts.append("行为非常活跃")
        elif event_count > 20:
            parts.append("行为较为活跃")

        return "，".join(parts) + "。"

    def _format_duration(self, duration: int) -> str:
        """
        格式化时长

        Args:
            duration: 时长（秒）

        Returns:
            格式化后的时长描述
        """
        if duration < 60:
            return f"{duration} 秒"
        elif duration < 3600:
            minutes = duration // 60
            return f"{minutes} 分钟"
        else:
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            if minutes > 0:
                return f"{hours} 小时 {minutes} 分钟"
            else:
                return f"{hours} 小时"

    def _format_app_usage(self, app_pkg_list: List[str], app_switch_freq: int) -> str:
        """
        格式化应用使用描述

        Args:
            app_pkg_list: 应用包名列表
            app_switch_freq: 应用切换频率

        Returns:
            应用使用描述
        """
        if not app_pkg_list:
            return "未使用任何应用"

        # 转换为中文名称
        app_names = [APP_NAME_MAP.get(pkg, pkg) for pkg in app_pkg_list]

        # 统计应用类别
        categories = {}
        for pkg in app_pkg_list:
            category = APP_CATEGORY_MAP.get(pkg, "other")
            categories[category] = categories.get(category, 0) + 1

        # 构建描述
        if len(app_names) == 1:
            text = f"使用了 {app_names[0]}"
        elif len(app_names) == 2:
            text = f"使用了 {app_names[0]} 和 {app_names[1]}"
        elif len(app_names) <= 5:
            text = f"使用了 {', '.join(app_names[:-1])} 和 {app_names[-1]}"
        else:
            # 超过 5 个应用，按类别描述
            category_texts = []
            for category, count in categories.items():
                category_name = self._get_category_name(category)
                category_texts.append(f"{count} 个{category_name}应用")

            text = f"使用了 {', '.join(category_texts)}"

        # 添加切换频率描述
        if app_switch_freq > 10:
            text += f"（频繁切换，共 {app_switch_freq} 次）"
        elif app_switch_freq > 5:
            text += f"（切换了 {app_switch_freq} 次）"

        return text

    def _format_poi_list(self, poi_list: List[str]) -> str:
        """
        格式化 POI 列表

        Args:
            poi_list: POI 列表

        Returns:
            POI 描述
        """
        if not poi_list:
            return "未知"

        # 转换为中文名称
        poi_names = [POI_NAME_MAP.get(poi, poi) for poi in poi_list]

        if len(poi_names) == 1:
            return poi_names[0]
        elif len(poi_names) == 2:
            return f"{poi_names[0]} → {poi_names[1]}"
        else:
            return " → ".join(poi_names)

    def _get_category_name(self, category: str) -> str:
        """
        获取类别中文名称

        Args:
            category: 类别英文名

        Returns:
            类别中文名
        """
        category_map = {
            "automotive": "汽车",
            "social": "社交",
            "food_delivery": "外卖",
            "shopping": "电商",
            "entertainment": "娱乐",
            "finance": "金融",
        }
        return category_map.get(category, "其他")
