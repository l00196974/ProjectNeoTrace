"""汽车领域本体知识库

包含汽车品牌、车型、用户行为模式等领域知识。
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Optional
import json

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class AutomotiveOntology:
    """汽车领域本体"""

    def __init__(self):
        # 汽车品牌分类
        self.brands = {
            'luxury': ['奔驰', '宝马', 'BMW', '奥迪', 'Audi', '雷克萨斯', 'Lexus', '保时捷', 'Porsche'],
            'premium': ['凯迪拉克', 'Cadillac', '沃尔沃', 'Volvo', '英菲尼迪', 'Infiniti', '讴歌', 'Acura'],
            'mainstream': ['大众', 'VW', '丰田', 'Toyota', '本田', 'Honda', '日产', 'Nissan', '福特', 'Ford'],
            'domestic': ['比亚迪', 'BYD', '吉利', 'Geely', '长城', 'Great Wall', '长安', 'Changan'],
            'ev': ['特斯拉', 'Tesla', '蔚来', 'NIO', '小鹏', 'Xpeng', '理想', 'Li Auto']
        }

        # 车型类别
        self.vehicle_types = {
            'sedan': ['轿车', '三厢车', 'Sedan'],
            'suv': ['SUV', '越野车', 'Sport Utility Vehicle'],
            'mpv': ['MPV', '商务车', 'Multi-Purpose Vehicle'],
            'coupe': ['跑车', '轿跑', 'Coupe'],
            'ev': ['电动车', '新能源车', 'Electric Vehicle']
        }

        # 价格区间（万元）
        self.price_ranges = {
            'budget': (0, 10),
            'economy': (10, 20),
            'mid_range': (20, 40),
            'premium': (40, 80),
            'luxury': (80, float('inf'))
        }

        # 高意向行为特征
        self.high_intent_behaviors = [
            '多次访问配置页',
            '查看金融方案',
            '对比多款车型',
            '访问经销商页面',
            '查看试驾信息',
            '访问汽车市场',
            '长时间停留在车型详情页',
            '查看车主评价',
            '计算贷款',
            '查看优惠信息'
        ]

        # 典型购车路径
        self.typical_purchase_paths = [
            {
                'stage': 'awareness',
                'behaviors': ['浏览汽车资讯', '观看汽车视频', '阅读车型评测'],
                'duration': '1-7天',
                'next_stage_probability': 0.3
            },
            {
                'stage': 'consideration',
                'behaviors': ['对比车型', '查看配置', '阅读车主评价', '计算预算'],
                'duration': '7-30天',
                'next_stage_probability': 0.5
            },
            {
                'stage': 'decision',
                'behaviors': ['查看金融方案', '访问经销商', '预约试驾', '查看优惠'],
                'duration': '1-14天',
                'next_stage_probability': 0.7
            },
            {
                'stage': 'purchase',
                'behaviors': ['到店试驾', '提交留资', '咨询销售', '下订单'],
                'duration': '1-7天',
                'next_stage_probability': 1.0
            }
        ]

        # 应用包名到品牌映射
        self.app_to_brand = {
            'com.autohome': '汽车之家',
            'com.yiche': '易车网',
            'com.bitauto': '汽车报价大全',
            'com.xcar': '爱卡汽车',
            'com.pcauto': '太平洋汽车',
            'com.dongchedi': '懂车帝'
        }

    def get_brand_category(self, brand: str) -> Optional[str]:
        """获取品牌类别"""
        for category, brands in self.brands.items():
            if brand in brands:
                return category
        return None

    def get_price_range_category(self, price: float) -> Optional[str]:
        """获取价格区间类别"""
        for category, (min_price, max_price) in self.price_ranges.items():
            if min_price <= price < max_price:
                return category
        return None

    def is_high_intent_behavior(self, behavior: str) -> bool:
        """判断是否为高意向行为"""
        return any(pattern in behavior for pattern in self.high_intent_behaviors)

    def get_purchase_stage(self, behaviors: List[str]) -> Optional[str]:
        """根据行为推断购车阶段"""
        stage_scores = {}

        for path in self.typical_purchase_paths:
            stage = path['stage']
            stage_behaviors = path['behaviors']

            # 计算匹配度
            matches = sum(1 for b in behaviors if any(sb in b for sb in stage_behaviors))
            stage_scores[stage] = matches

        # 返回匹配度最高的阶段
        if stage_scores:
            return max(stage_scores, key=stage_scores.get)
        return None

    def get_similar_user_patterns(self, current_behaviors: List[str]) -> List[Dict]:
        """获取相似用户的行为模式"""
        # 这里简化实现，实际应该从数据库查询
        current_stage = self.get_purchase_stage(current_behaviors)

        if not current_stage:
            return []

        # 找到当前阶段
        current_stage_idx = None
        for idx, path in enumerate(self.typical_purchase_paths):
            if path['stage'] == current_stage:
                current_stage_idx = idx
                break

        if current_stage_idx is None:
            return []

        # 返回后续阶段的典型行为
        similar_patterns = []
        for idx in range(current_stage_idx, len(self.typical_purchase_paths)):
            path = self.typical_purchase_paths[idx]
            similar_patterns.append({
                'stage': path['stage'],
                'typical_behaviors': path['behaviors'],
                'probability': path['next_stage_probability']
            })

        return similar_patterns


class KnowledgeBase:
    """知识库管理器"""

    def __init__(self, storage_path: str = "data/knowledge"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.ontology = AutomotiveOntology()
        self.user_patterns = {}  # device_id -> behavior patterns

    def query_similar_users(self, device_id: str, current_behaviors: List[str]) -> List[Dict]:
        """查询相似用户的后续行为"""
        # 获取当前用户的购车阶段
        current_stage = self.ontology.get_purchase_stage(current_behaviors)

        # 获取相似用户模式
        similar_patterns = self.ontology.get_similar_user_patterns(current_behaviors)

        return similar_patterns

    def update_user_pattern(self, device_id: str, behaviors: List[str], outcome: str):
        """更新用户行为模式"""
        if device_id not in self.user_patterns:
            self.user_patterns[device_id] = []

        self.user_patterns[device_id].append({
            'behaviors': behaviors,
            'outcome': outcome,
            'timestamp': Path(__file__).stat().st_mtime
        })

        # 持久化
        self._save_user_patterns()

    def _save_user_patterns(self):
        """保存用户模式到磁盘"""
        pattern_file = self.storage_path / "user_patterns.json"
        with open(pattern_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_patterns, f, indent=2, ensure_ascii=False)

    def _load_user_patterns(self):
        """从磁盘加载用户模式"""
        pattern_file = self.storage_path / "user_patterns.json"
        if pattern_file.exists():
            with open(pattern_file, 'r', encoding='utf-8') as f:
                self.user_patterns = json.load(f)

    def get_domain_context(self, session_text: str, behaviors: List[str]) -> str:
        """获取领域上下文（用于增强 LLM Prompt）"""
        context_parts = []

        # 识别品牌
        mentioned_brands = []
        for app_pkg, brand in self.ontology.app_to_brand.items():
            if app_pkg in session_text or brand in session_text:
                mentioned_brands.append(brand)

        if mentioned_brands:
            context_parts.append(f"用户访问了以下汽车平台: {', '.join(mentioned_brands)}")

        # 识别高意向行为
        high_intent_behaviors = [
            b for b in behaviors
            if self.ontology.is_high_intent_behavior(b)
        ]

        if high_intent_behaviors:
            context_parts.append(f"用户表现出以下高意向行为: {', '.join(high_intent_behaviors[:3])}")

        # 推断购车阶段
        stage = self.ontology.get_purchase_stage(behaviors)
        if stage:
            stage_names = {
                'awareness': '认知阶段',
                'consideration': '考虑阶段',
                'decision': '决策阶段',
                'purchase': '购买阶段'
            }
            context_parts.append(f"用户当前处于购车的{stage_names.get(stage, stage)}")

        # 获取相似用户模式
        similar_patterns = self.ontology.get_similar_user_patterns(behaviors)
        if similar_patterns:
            next_stage = similar_patterns[0]
            context_parts.append(
                f"相似用户通常会进行以下行为: {', '.join(next_stage['typical_behaviors'][:3])}"
            )

        return '\n'.join(context_parts)


def main():
    """测试函数"""
    print("=" * 60)
    print("汽车领域本体知识库测试")
    print("=" * 60)

    # 创建知识库
    kb = KnowledgeBase()

    # 测试品牌识别
    print("\n测试 1: 品牌识别")
    brand = "宝马"
    category = kb.ontology.get_brand_category(brand)
    print(f"品牌: {brand}, 类别: {category}")

    # 测试价格区间
    print("\n测试 2: 价格区间")
    price = 35.0
    price_category = kb.ontology.get_price_range_category(price)
    print(f"价格: {price}万, 类别: {price_category}")

    # 测试购车阶段推断
    print("\n测试 3: 购车阶段推断")
    behaviors = ['浏览汽车资讯', '对比车型', '查看配置']
    stage = kb.ontology.get_purchase_stage(behaviors)
    print(f"行为: {behaviors}")
    print(f"推断阶段: {stage}")

    # 测试相似用户模式
    print("\n测试 4: 相似用户模式")
    similar_patterns = kb.query_similar_users('device_001', behaviors)
    print(f"相似用户的后续行为:")
    for pattern in similar_patterns:
        print(f"  阶段: {pattern['stage']}")
        print(f"  典型行为: {pattern['typical_behaviors']}")
        print(f"  转化概率: {pattern['probability']:.2%}")

    # 测试领域上下文生成
    print("\n测试 5: 领域上下文生成")
    session_text = "用户在汽车之家浏览了宝马 5 系，查看了配置和金融方案"
    behaviors = ['访问汽车之家', '查看配置', '查看金融方案']
    context = kb.get_domain_context(session_text, behaviors)
    print(f"Session 文本: {session_text}")
    print(f"领域上下文:\n{context}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
