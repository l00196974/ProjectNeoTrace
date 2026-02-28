"""弱监督标签挖掘模块

基于用户行为特征生成代理标签。

标签定义：
- Label 0 (Noise): 无效数据（如测试设备）
- Label 1 (Fans): 汽车爱好者，但无购车意向
- Label 2 (Consider): 考虑购车，但未采取行动
- Label 3 (Leads): 高意向用户，已留资或到店
"""

from typing import Dict, List
import pandas as pd


class ProxyLabelMiner:
    """代理标签挖掘器"""

    def __init__(self):
        """初始化标签挖掘器"""
        pass

    def mine_labels(self, sessions: List[Dict]) -> List[Dict]:
        """
        为 Session 生成代理标签

        Args:
            sessions: Session 列表

        Returns:
            带标签的 Session 列表
        """
        labeled_sessions = []

        for session in sessions:
            label = self._determine_label(session)
            session_with_label = {**session, "proxy_label": label}
            labeled_sessions.append(session_with_label)

        return labeled_sessions

    def _determine_label(self, session: Dict) -> int:
        """
        判断 Session 的标签

        Args:
            session: Session 字典

        Returns:
            标签（0/1/2/3）
        """
        # 提取特征
        app_pkg_list = session.get("app_pkg_list", [])
        lbs_poi_list = session.get("lbs_poi_list", [])
        config_page_dwell = session.get("config_page_dwell", 0)
        finance_page_dwell = session.get("finance_page_dwell", 0)
        session_duration = session.get("session_duration", 0)
        app_switch_freq = session.get("app_switch_freq", 0)

        # 解析列表（如果是字符串）
        if isinstance(app_pkg_list, str):
            try:
                app_pkg_list = eval(app_pkg_list)
            except:
                app_pkg_list = []

        if isinstance(lbs_poi_list, str):
            try:
                lbs_poi_list = eval(lbs_poi_list)
            except:
                lbs_poi_list = []

        # 判断是否为 Label 3（高意向用户）
        if self._is_label_3(
            app_pkg_list, lbs_poi_list, config_page_dwell, finance_page_dwell
        ):
            return 3

        # 判断是否为 Label 2（考虑购车）
        if self._is_label_2(
            app_pkg_list, lbs_poi_list, config_page_dwell, finance_page_dwell
        ):
            return 2

        # 判断是否为 Label 1（汽车爱好者）
        if self._is_label_1(app_pkg_list, session_duration):
            return 1

        # 默认为 Label 0（噪声）
        return 0

    def _is_label_3(
        self,
        app_pkg_list: List[str],
        lbs_poi_list: List[str],
        config_page_dwell: int,
        finance_page_dwell: int,
    ) -> bool:
        """
        判断是否为 Label 3（高意向用户）

        规则：
        1. 到访过 4S 店或汽车市场
        2. 在配置页停留 > 5 分钟
        3. 在金融页停留 > 2 分钟
        """
        # 检测 LBS（到访 4S 店或汽车市场）
        has_4s_visit = any(poi in ["4s_store", "auto_market"] for poi in lbs_poi_list)

        # 检测配置页停留
        has_config_dwell = config_page_dwell > 300  # 5 分钟

        # 检测金融页停留
        has_finance_dwell = finance_page_dwell > 120  # 2 分钟

        # 满足任意一个条件即为 Label 3
        return has_4s_visit or has_config_dwell or has_finance_dwell

    def _is_label_2(
        self,
        app_pkg_list: List[str],
        lbs_poi_list: List[str],
        config_page_dwell: int,
        finance_page_dwell: int,
    ) -> bool:
        """
        判断是否为 Label 2（考虑购车）

        规则：
        1. 使用汽车类 App
        2. 在配置页或金融页有停留（但不满足 Label 3）
        """
        # 检测汽车类 App
        automotive_apps = [
            "com.autohome",
            "com.yiche",
            "com.bitauto",
            "com.xcar",
            "com.pcauto",
        ]
        has_automotive_app = any(app in automotive_apps for app in app_pkg_list)

        # 检测配置页或金融页停留
        has_page_dwell = config_page_dwell > 0 or finance_page_dwell > 0

        return has_automotive_app and has_page_dwell

    def _is_label_1(self, app_pkg_list: List[str], session_duration: int) -> bool:
        """
        判断是否为 Label 1（汽车爱好者）

        规则：
        1. 使用汽车类 App
        2. Session 时长 > 1 分钟
        """
        # 检测汽车类 App
        automotive_apps = [
            "com.autohome",
            "com.yiche",
            "com.bitauto",
            "com.xcar",
            "com.pcauto",
        ]
        has_automotive_app = any(app in automotive_apps for app in app_pkg_list)

        # 检测 Session 时长
        has_duration = session_duration > 60  # 1 分钟

        return has_automotive_app and has_duration

    def get_label_distribution(self, labeled_sessions: List[Dict]) -> Dict[int, int]:
        """
        获取标签分布

        Args:
            labeled_sessions: 带标签的 Session 列表

        Returns:
            标签分布字典
        """
        distribution = {0: 0, 1: 0, 2: 0, 3: 0}

        for session in labeled_sessions:
            label = session.get("proxy_label", 0)
            distribution[label] = distribution.get(label, 0) + 1

        return distribution


def main():
    """测试函数"""
    import sys
    from pathlib import Path

    # 添加项目根目录到 Python 路径
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))

    print("=" * 60)
    print("测试弱监督标签挖掘")
    print("=" * 60)

    # 加载 Session 数据
    sessions_file = PROJECT_ROOT / "data" / "processed" / "sessions.csv"
    print(f"\n加载 Session 数据：{sessions_file}")

    df = pd.read_csv(sessions_file)
    sessions = df.head(100).to_dict("records")  # 测试前 100 个
    print(f"加载了 {len(sessions)} 个 Session")

    # 创建标签挖掘器
    miner = ProxyLabelMiner()

    # 挖掘标签
    print("\n挖掘标签...")
    labeled_sessions = miner.mine_labels(sessions)

    # 统计标签分布
    distribution = miner.get_label_distribution(labeled_sessions)

    print("\n标签分布：")
    label_names = {
        0: "Label 0 (Noise)",
        1: "Label 1 (Fans)",
        2: "Label 2 (Consider)",
        3: "Label 3 (Leads)",
    }

    for label, count in sorted(distribution.items()):
        percentage = count / len(labeled_sessions) * 100
        print(f"  {label_names[label]}: {count} ({percentage:.2f}%)")

    # 保存结果
    output_file = PROJECT_ROOT / "data" / "processed" / "labeled_sessions_sample.csv"
    df_labeled = pd.DataFrame(labeled_sessions)
    df_labeled.to_csv(output_file, index=False)
    print(f"\n标注结果已保存到：{output_file}")


if __name__ == "__main__":
    main()
