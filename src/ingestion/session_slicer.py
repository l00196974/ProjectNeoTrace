"""Session 切片引擎

将用户原始行为序列切割成有意义的 Session 片段。

输入：OSEventLog (JSON)
输出：SessionFeature (Parquet)
"""

import json
import pandas as pd
import time
from pathlib import Path
from typing import List, Dict
from collections import defaultdict
import logging

from src.ingestion.state_machine import SessionStateMachine
from src.ingestion.feature_aggregator import FeatureAggregator
from src.types import OSEventLog, SessionDict
from src.utils.traceability import TraceabilityManager

logger = logging.getLogger(__name__)


class SessionSlicer:
    """Session 切片器"""

    def __init__(self, screen_off_threshold: int = 600, enable_traceability: bool = True):
        """初始化切片器。

        Args:
            screen_off_threshold: 息屏阈值（秒），默认 10 分钟
            enable_traceability: 是否启用可追溯性记录
        """
        self.screen_off_threshold = screen_off_threshold
        self.feature_aggregator = FeatureAggregator()
        self.enable_traceability = enable_traceability

        if self.enable_traceability:
            self.traceability_mgr = TraceabilityManager()

    def slice_from_file(self, input_file: str) -> List[SessionDict]:
        """从文件读取事件并切片。

        Args:
            input_file: 输入文件路径（JSON Lines 格式）

        Returns:
            Session 列表，每个 Session 包含完整的特征信息

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 解析失败
            ValueError: 数据格式不正确
        """
        print(f"读取事件数据：{input_file}")

        # 读取事件
        events: List[OSEventLog] = []
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        try:
                            event = json.loads(line)
                            events.append(event)
                        except json.JSONDecodeError as e:
                            logger.warning(f"跳过无效 JSON 行 {line_num}: {e}")
                            continue
        except FileNotFoundError:
            logger.error(f"文件不存在: {input_file}")
            raise
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            raise

        print(f"共读取 {len(events)} 个事件")

        # 按设备分组
        device_events = self._group_by_device(events)
        print(f"共 {len(device_events)} 个设备")

        # 切片
        sessions = self.slice_events(device_events)
        print(f"切片完成，共 {len(sessions)} 个 Session")

        return sessions

    def slice_events(self, device_events: Dict[str, List[OSEventLog]]) -> List[SessionDict]:
        """切片事件序列。

        Args:
            device_events: 按设备分组的事件字典 {device_id: [events]}

        Returns:
            Session 列表
        """
        all_sessions = []
        device_count = len(device_events)
        processed = 0

        for device_id, events in device_events.items():
            # 按时间排序
            events.sort(key=lambda x: x["timestamp"])

            # 切片
            sessions = self._slice_device_events(device_id, events)
            all_sessions.extend(sessions)

            processed += 1
            if processed % 100 == 0:
                print(f"  进度：{processed}/{device_count}")

        return all_sessions

    def _slice_device_events(self, device_id: str, events: List[OSEventLog]) -> List[SessionDict]:
        """切片单个设备的事件序列。

        Args:
            device_id: 设备 ID
            events: 事件列表

        Returns:
            Session 列表
        """
        if not events:
            return []

        sessions = []
        current_session_events = []
        state_machine = SessionStateMachine(screen_off_threshold=self.screen_off_threshold)

        for event in events:
            # 判断是否开始新 Session
            if state_machine.should_start_new_session(event):
                # 保存当前 Session
                if current_session_events:
                    session = self._create_session(
                        device_id, len(sessions), current_session_events
                    )
                    sessions.append(session)

                # 开始新 Session
                current_session_events = [event]
            else:
                current_session_events.append(event)

        # 保存最后一个 Session
        if current_session_events:
            session = self._create_session(
                device_id, len(sessions), current_session_events
            )
            sessions.append(session)

        return sessions

    def _create_session(
        self, device_id: str, session_index: int, events: List[OSEventLog]
    ) -> SessionDict:
        """创建 Session 对象。

        Args:
            device_id: 设备 ID
            session_index: Session 索引
            events: 事件列表

        Returns:
            Session 字典
        """
        # 聚合特征
        features = self.feature_aggregator.aggregate(events)

        # 生成 Session ID
        session_id = f"{device_id}_session_{session_index:04d}"

        # 添加 Session ID
        features["session_id"] = session_id

        # 记录可追溯性
        if self.enable_traceability:
            try:
                # 提取事件 ID（如果存在）
                raw_event_ids = [
                    str(event.get("event_id", f"{event['timestamp']}_{i}"))
                    for i, event in enumerate(events)
                ]

                record = {
                    "session_id": session_id,
                    "device_id": device_id,
                    "raw_event_ids": raw_event_ids,
                    "semantic_text": "",  # 后续填充
                    "intent_labels": [],  # 后续填充
                    "raw_vector": [],  # 后续填充
                    "optimized_vector": [],  # 后续填充
                    "model_version": "v1.0",
                    "timestamp": int(time.time())
                }
                self.traceability_mgr.save_record(record)
            except Exception as e:
                logger.warning(f"保存可追溯性记录失败: {e}")

        return features

    def _group_by_device(self, events: List[OSEventLog]) -> Dict[str, List[OSEventLog]]:
        """按设备分组事件。

        Args:
            events: 事件列表

        Returns:
            按设备分组的事件字典
        """
        device_events = defaultdict(list)

        for event in events:
            device_id = event["device_id"]
            device_events[device_id].append(event)

        return dict(device_events)

    def save_to_csv(self, sessions: List[SessionDict], output_file: str) -> None:
        """保存 Session 到 CSV 文件。

        Args:
            sessions: Session 列表
            output_file: 输出文件路径
        """
        if not sessions:
            print("警告：没有 Session 数据可保存")
            return

        # 转换为 DataFrame
        df = pd.DataFrame(sessions)

        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存为 CSV
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Session 数据已保存到：{output_file}")
        print(f"  行数：{len(df)}")
        print(f"  列数：{len(df.columns)}")

    def save_to_parquet(self, sessions: List[SessionDict], output_file: str) -> None:
        """保存 Session 到 Parquet 文件。

        Args:
            sessions: Session 列表
            output_file: 输出文件路径
        """
        if not sessions:
            print("警告：没有 Session 数据可保存")
            return

        # 转换为 DataFrame
        df = pd.DataFrame(sessions)

        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存为 Parquet
        df.to_parquet(output_file, index=False)
        print(f"Session 数据已保存到：{output_file}")
        print(f"  行数：{len(df)}")
        print(f"  列数：{len(df.columns)}")

    def load_from_parquet(self, input_file: str) -> List[SessionDict]:
        """从 Parquet 文件加载 Session。

        Args:
            input_file: 输入文件路径

        Returns:
            Session 列表
        """
        df = pd.read_parquet(input_file)
        sessions = df.to_dict("records")
        print(f"从 {input_file} 加载了 {len(sessions)} 个 Session")
        return sessions


def main():
    """测试函数"""
    import sys
    from pathlib import Path

    # 添加项目根目录到 Python 路径
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))

    # 输入输出路径
    input_file = PROJECT_ROOT / "data" / "raw" / "events.json"
    output_file = PROJECT_ROOT / "data" / "processed" / "sessions.parquet"

    # 创建切片器
    slicer = SessionSlicer(screen_off_threshold=600)

    # 切片
    sessions = slicer.slice_from_file(str(input_file))

    # 保存
    slicer.save_to_parquet(sessions, str(output_file))

    # 统计信息
    print("\n=== 统计信息 ===")
    print(f"Session 总数：{len(sessions)}")

    if sessions:
        # 统计每个设备的 Session 数量
        device_session_count = {}
        for session in sessions:
            device_id = session["device_id"]
            device_session_count[device_id] = device_session_count.get(device_id, 0) + 1

        print(f"设备数量：{len(device_session_count)}")
        print(
            f"平均每设备 Session 数：{sum(device_session_count.values()) / len(device_session_count):.2f}"
        )

        # 统计 Session 时长分布
        durations = [s["session_duration"] for s in sessions]
        print(f"Session 平均时长：{sum(durations) / len(durations):.2f} 秒")
        print(f"Session 最短时长：{min(durations)} 秒")
        print(f"Session 最长时长：{max(durations)} 秒")


if __name__ == "__main__":
    main()
