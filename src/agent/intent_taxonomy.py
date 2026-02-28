"""多意图分类体系定义"""

# 11 个意图类别（多标签分类）
ALL_INTENTS = [
    "automotive_purchase",  # 0 - 购车意向
    "automotive_comparison",  # 1 - 车型对比
    "automotive_financing",  # 2 - 汽车金融
    "automotive_insurance",  # 3 - 车险
    "automotive_maintenance",  # 4 - 保养维修
    "automotive_accessories",  # 5 - 汽车用品
    "general_food_delivery",  # 6 - 外卖
    "general_shopping",  # 7 - 电商购物
    "general_social",  # 8 - 社交
    "general_entertainment",  # 9 - 娱乐
    "general_finance",  # 10 - 金融理财
]

NUM_INTENTS = 11

# 意图描述
INTENT_DESCRIPTIONS = {
    "automotive_purchase": "购车意向 - 用户有明确的购车需求",
    "automotive_comparison": "车型对比 - 用户正在对比不同车型",
    "automotive_financing": "汽车金融 - 用户关注汽车贷款和金融方案",
    "automotive_insurance": "车险 - 用户关注车险产品",
    "automotive_maintenance": "保养维修 - 用户关注汽车保养和维修",
    "automotive_accessories": "汽车用品 - 用户关注汽车配件和用品",
    "general_food_delivery": "外卖 - 用户使用外卖服务",
    "general_shopping": "电商购物 - 用户进行网购",
    "general_social": "社交 - 用户使用社交应用",
    "general_entertainment": "娱乐 - 用户使用娱乐应用",
    "general_finance": "金融理财 - 用户关注金融理财产品",
}

# 汽车相关意图（用于判断是否为汽车领域）
AUTOMOTIVE_INTENTS = [
    "automotive_purchase",
    "automotive_comparison",
    "automotive_financing",
    "automotive_insurance",
    "automotive_maintenance",
    "automotive_accessories",
]


def is_automotive_intent(intent: str) -> bool:
    """判断是否为汽车相关意图"""
    return intent in AUTOMOTIVE_INTENTS


def get_intent_index(intent: str) -> int:
    """获取意图索引"""
    if intent in ALL_INTENTS:
        return ALL_INTENTS.index(intent)
    return -1


def get_intent_by_index(index: int) -> str:
    """根据索引获取意图名称"""
    if 0 <= index < NUM_INTENTS:
        return ALL_INTENTS[index]
    return ""
