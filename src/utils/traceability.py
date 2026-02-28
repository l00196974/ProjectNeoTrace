"""数据可追溯性管理模块

提供完整的数据血缘追踪能力，记录从原始事件到最终向量的完整链路。
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from src.types import TraceabilityRecord

logger = logging.getLogger(__name__)


class TraceabilityManager:
    """可追溯性管理器"""

    def __init__(self, storage_path: str = "data/traceability"):
        """初始化可追溯性管理器。

        Args:
            storage_path: 存储路径
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_record(self, record: TraceabilityRecord) -> None:
        """保存可追溯性记录。

        Args:
            record: 可追溯性记录
        """
        device_id = record["device_id"]
        file_path = self.storage_path / f"{device_id}.jsonl"

        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            logger.debug(f"保存可追溯性记录: {record['session_id']}")
        except Exception as e:
            logger.error(f"保存可追溯性记录失败: {e}")
            raise

    def query_by_device_id(self, device_id: str) -> List[TraceabilityRecord]:
        """根据设备 ID 查询完整链路。

        Args:
            device_id: 设备 ID

        Returns:
            可追溯性记录列表
        """
        file_path = self.storage_path / f"{device_id}.jsonl"

        if not file_path.exists():
            logger.warning(f"设备 {device_id} 没有可追溯性记录")
            return []

        records = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError as e:
                            logger.warning(f"跳过无效 JSON 行: {e}")
                            continue
        except Exception as e:
            logger.error(f"读取可追溯性记录失败: {e}")
            raise

        return records

    def query_by_session_id(self, session_id: str) -> Optional[TraceabilityRecord]:
        """根据 Session ID 查询记录。

        Args:
            session_id: Session ID

        Returns:
            可追溯性记录，如果不存在则返回 None
        """
        # 从 session_id 提取 device_id
        try:
            device_id = session_id.split("_session_")[0]
        except Exception:
            logger.error(f"无效的 session_id 格式: {session_id}")
            return None

        records = self.query_by_device_id(device_id)

        for record in records:
            if record["session_id"] == session_id:
                return record

        logger.warning(f"未找到 session_id {session_id} 的可追溯性记录")
        return None

    def update_record(self, session_id: str, updates: dict) -> bool:
        """更新可追溯性记录。

        Args:
            session_id: Session ID
            updates: 要更新的字段

        Returns:
            是否更新成功
        """
        record = self.query_by_session_id(session_id)
        if not record:
            logger.error(f"未找到 session_id {session_id} 的记录")
            return False

        # 更新记录
        record.update(updates)

        # 重新保存（追加模式）
        try:
            self.save_record(record)
            return True
        except Exception as e:
            logger.error(f"更新可追溯性记录失败: {e}")
            return False

    def get_statistics(self) -> dict:
        """获取可追溯性统计信息。

        Returns:
            统计信息字典
        """
        total_devices = 0
        total_sessions = 0

        for file_path in self.storage_path.glob("*.jsonl"):
            total_devices += 1
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        total_sessions += 1

        return {
            "total_devices": total_devices,
            "total_sessions": total_sessions,
            "storage_path": str(self.storage_path)
        }
