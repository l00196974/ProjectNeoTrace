"""生成模拟数据脚本

生成用户行为日志数据，用于测试和验证系统功能。

数据格式：
{
  "device_id": "abc123",
  "timestamp": 1709136000,
  "app_pkg": "com.autohome",
  "action": "app_foreground",
  "payload": {
    "dwell_time": 450,
    "lbs_poi": "auto_market"
  }
}
"""

import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 数据目录
DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)


# 应用包名映射
APP_PACKAGES = {
    # 汽车类
    "automotive": [
        "com.autohome",  # 汽车之家
        "com.yiche",  # 易车
        "com.bitauto",  # 懂车帝
        "com.xcar",  # 爱卡汽车
        "com.pcauto",  # 太平洋汽车
    ],
    # 社交类
    "social": [
        "com.tencent.mm",  # 微信
        "com.tencent.mobileqq",  # QQ
        "com.sina.weibo",  # 微博
        "com.tencent.wework",  # 企业微信
    ],
    # 外卖类
    "food_delivery": [
        "com.sankuai.meituan",  # 美团
        "me.ele",  # 饿了么
    ],
    # 电商类
    "shopping": [
        "com.taobao.taobao",  # 淘宝
        "com.jingdong.app.mall",  # 京东
        "com.xunmeng.pinduoduo",  # 拼多多
    ],
    # 娱乐类
    "entertainment": [
        "com.ss.android.ugc.aweme",  # 抖音
        "com.tencent.qqlive",  # 腾讯视频
        "com.youku.phone",  # 优酷
    ],
    # 金融类
    "finance": [
        "com.tencent.wemoney.app",  # 微信支付
        "com.eg.android.AlipayGphone",  # 支付宝
        "com.chinamworld.main",  # 中国银行
    ],
}

# 行为类型
ACTIONS = [
    "app_foreground",  # 应用前台
    "app_background",  # 应用后台
    "touch_scroll",  # 滑动
    "touch_click",  # 点击
    "screen_on",  # 亮屏
    "screen_off",  # 息屏
]

# LBS POI 类型
POI_TYPES = [
    "home",  # 住宅
    "office",  # 办公室
    "auto_market",  # 汽车市场
    "4s_store",  # 4S 店
    "shopping_mall",  # 商场
    "restaurant",  # 餐厅
    "gas_station",  # 加油站
]


def generate_device_id(index: int) -> str:
    """生成设备 ID"""
    return f"device_{index:06d}"


def generate_timestamp(base_time: datetime, offset_seconds: int) -> int:
    """生成时间戳"""
    return int((base_time + timedelta(seconds=offset_seconds)).timestamp())


def generate_user_profile(device_id: str) -> Dict:
    """
    生成用户画像

    用户类型：
    - high_intent: 高意向用户（30%）- 频繁浏览汽车应用
    - medium_intent: 中等意向用户（40%）- 偶尔浏览汽车应用
    - low_intent: 低意向用户（30%）- 很少浏览汽车应用
    """
    user_type = random.choices(
        ["high_intent", "medium_intent", "low_intent"], weights=[0.3, 0.4, 0.3]
    )[0]

    if user_type == "high_intent":
        automotive_ratio = random.uniform(0.4, 0.7)  # 40-70% 汽车应用
        session_count = random.randint(10, 20)  # 10-20 个 session
    elif user_type == "medium_intent":
        automotive_ratio = random.uniform(0.2, 0.4)  # 20-40% 汽车应用
        session_count = random.randint(5, 10)  # 5-10 个 session
    else:
        automotive_ratio = random.uniform(0.0, 0.2)  # 0-20% 汽车应用
        session_count = random.randint(3, 8)  # 3-8 个 session

    return {
        "device_id": device_id,
        "user_type": user_type,
        "automotive_ratio": automotive_ratio,
        "session_count": session_count,
    }


def generate_session_events(
    device_id: str, session_index: int, base_time: datetime, user_profile: Dict
) -> List[Dict]:
    """生成单个 Session 的事件序列"""
    events = []
    current_offset = session_index * 3600  # 每个 session 间隔 1 小时

    # 决定这个 session 是否为汽车相关
    is_automotive_session = random.random() < user_profile["automotive_ratio"]

    if is_automotive_session:
        # 汽车相关 session
        app_categories = ["automotive", "finance"]
        event_count = random.randint(20, 50)  # 汽车 session 事件较多
        poi_type = random.choice(["home", "auto_market", "4s_store"])
    else:
        # 非汽车 session
        app_categories = random.choices(
            ["social", "food_delivery", "shopping", "entertainment"], k=2
        )
        event_count = random.randint(10, 30)
        poi_type = random.choice(["home", "office", "shopping_mall", "restaurant"])

    # 生成事件序列
    for i in range(event_count):
        # 选择应用
        category = random.choice(app_categories)
        app_pkg = random.choice(APP_PACKAGES[category])

        # 选择行为
        if i == 0:
            action = "screen_on"
        elif i == event_count - 1:
            action = "screen_off"
        else:
            action = random.choice(["app_foreground", "touch_scroll", "touch_click"])

        # 生成 payload
        payload = {"lbs_poi": poi_type}

        if action in ["app_foreground", "touch_scroll"]:
            payload["dwell_time"] = random.randint(10, 600)  # 10 秒 - 10 分钟

        if action == "touch_click" and category == "automotive":
            # 汽车应用的点击可能是配置页或金融页
            page_type = random.choice(["config_page", "finance_page", "normal_page"])
            payload["page_type"] = page_type

        # 创建事件
        event = {
            "device_id": device_id,
            "timestamp": generate_timestamp(base_time, current_offset + i * 10),
            "app_pkg": app_pkg,
            "action": action,
            "payload": payload,
        }

        events.append(event)

        # 更新时间偏移
        if action == "app_foreground":
            current_offset += payload.get("dwell_time", 60)

    return events


def generate_mock_data(
    num_devices: int = 1000, days: int = 7, output_file: str = None
) -> List[Dict]:
    """
    生成模拟数据

    Args:
        num_devices: 设备数量
        days: 天数
        output_file: 输出文件路径

    Returns:
        事件列表
    """
    print(f"开始生成模拟数据：{num_devices} 个设备，{days} 天")

    all_events = []
    base_time = datetime.now() - timedelta(days=days)

    for device_index in range(num_devices):
        if device_index % 100 == 0:
            print(f"进度：{device_index}/{num_devices}")

        device_id = generate_device_id(device_index)
        user_profile = generate_user_profile(device_id)

        # 生成该用户的所有 session
        for session_index in range(user_profile["session_count"]):
            session_events = generate_session_events(
                device_id, session_index, base_time, user_profile
            )
            all_events.extend(session_events)

    # 按时间戳排序
    all_events.sort(key=lambda x: x["timestamp"])

    print(f"生成完成，共 {len(all_events)} 个事件")

    # 保存到文件
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for event in all_events:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")

        print(f"数据已保存到：{output_path}")

    return all_events


def main():
    """主函数"""
    # 生成模拟数据
    output_file = DATA_RAW_DIR / "events.json"

    events = generate_mock_data(
        num_devices=1000, days=7, output_file=str(output_file)
    )

    # 统计信息
    device_ids = set(event["device_id"] for event in events)
    print(f"设备数量：{len(device_ids)}")
    print(f"事件数量：{len(events)}")

    # 统计应用类别分布
    app_categories = {}
    for event in events:
        app_pkg = event["app_pkg"]
        for category, packages in APP_PACKAGES.items():
            if app_pkg in packages:
                app_categories[category] = app_categories.get(category, 0) + 1
                break

    print("应用类别分布：")
    for category, count in sorted(app_categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count} ({count/len(events)*100:.2f}%)")


if __name__ == "__main__":
    main()
