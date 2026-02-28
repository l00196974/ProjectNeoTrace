"""Prompt 模板 - 多意图识别

用于 LLM 标注用户行为意图。
"""

from src.agent.intent_taxonomy import ALL_INTENTS, INTENT_DESCRIPTIONS


# 多意图识别 Prompt 模板
MULTI_INTENT_PROMPT = """你是一个用户行为意图分析专家。根据用户的行为序列，识别其所有可能的意图。

用户行为序列：
{behavior_text}

可选意图类别：
1. automotive_purchase - 购车意向：用户有明确的购车需求
2. automotive_comparison - 车型对比：用户正在对比不同车型
3. automotive_financing - 汽车金融：用户关注汽车贷款和金融方案
4. automotive_insurance - 车险：用户关注车险产品
5. automotive_maintenance - 保养维修：用户关注汽车保养和维修
6. automotive_accessories - 汽车用品：用户关注汽车配件和用品
7. general_food_delivery - 外卖：用户使用外卖服务
8. general_shopping - 电商购物：用户进行网购
9. general_social - 社交：用户使用社交应用
10. general_entertainment - 娱乐：用户使用娱乐应用
11. general_finance - 金融理财：用户关注金融理财产品

请输出 JSON 格式（必须严格遵守格式）：
{{
  "intents": [
    {{
      "name": "<意图名称>",
      "confidence": <0-1 的浮点数>,
      "reasoning": "<简短推理>"
    }}
  ],
  "primary_intent": "<主要意图名称>",
  "urgency_score": <0-10 的整数，仅针对 automotive_purchase>
}}

示例：
输入：用户在汽车之家浏览了 5 款 SUV 配置页（停留 10 分钟），查看了金融贷款页面，然后打开美团点了外卖。
输出：
{{
  "intents": [
    {{"name": "automotive_comparison", "confidence": 0.95, "reasoning": "深度浏览多款车型配置"}},
    {{"name": "automotive_financing", "confidence": 0.85, "reasoning": "查看金融贷款页面"}},
    {{"name": "automotive_purchase", "confidence": 0.75, "reasoning": "对比车型并关注金融方案"}},
    {{"name": "general_food_delivery", "confidence": 0.90, "reasoning": "使用美团点外卖"}}
  ],
  "primary_intent": "automotive_comparison",
  "urgency_score": 7
}}

注意：
1. 只输出 JSON，不要有其他文字
2. confidence 必须是 0-1 之间的浮点数
3. urgency_score 只针对 automotive_purchase 意图，其他情况设为 0
4. 如果没有明确的汽车相关意图，urgency_score 设为 0
"""


def format_multi_intent_prompt(behavior_text: str) -> str:
    """
    格式化多意图识别 Prompt

    Args:
        behavior_text: 用户行为文本描述

    Returns:
        格式化后的 Prompt
    """
    return MULTI_INTENT_PROMPT.format(behavior_text=behavior_text)
