"""端到端追踪系统

为每个样本生成唯一 trace_id，记录完整链路。
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import uuid
from datetime import datetime
from collections import defaultdict

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TraceRecord:
    """追踪记录"""

    def __init__(
        self,
        trace_id: str,
        stage: str,
        input_data: Any,
        output_data: Any,
        metadata: Dict = None,
        quality_metrics: Dict = None
    ):
        self.trace_id = trace_id
        self.stage = stage
        self.input_data = input_data
        self.output_data = output_data
        self.metadata = metadata or {}
        self.quality_metrics = quality_metrics or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            'trace_id': self.trace_id,
            'stage': self.stage,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'metadata': self.metadata,
            'quality_metrics': self.quality_metrics,
            'timestamp': self.timestamp
        }


class E2ETracer:
    """端到端追踪器"""

    def __init__(self, storage_path: str = "data/traces"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.traces = defaultdict(list)  # trace_id -> [TraceRecord]

    def generate_trace_id(self, prefix: str = "trace") -> str:
        """生成唯一 trace_id"""
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def record(
        self,
        trace_id: str,
        stage: str,
        input_data: Any,
        output_data: Any,
        metadata: Dict = None,
        quality_metrics: Dict = None
    ):
        """记录追踪信息"""
        record = TraceRecord(
            trace_id=trace_id,
            stage=stage,
            input_data=input_data,
            output_data=output_data,
            metadata=metadata,
            quality_metrics=quality_metrics
        )

        # 内存缓存
        self.traces[trace_id].append(record)

        # 持久化存储
        self._save_record(record)

    def _save_record(self, record: TraceRecord):
        """保存记录到磁盘"""
        # 按日期分目录
        date_dir = self.storage_path / datetime.now().strftime("%Y%m%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        # 保存到 JSONL 文件
        trace_file = date_dir / f"{record.trace_id}.jsonl"
        with open(trace_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + '\n')

    def get_trace(self, trace_id: str) -> List[TraceRecord]:
        """获取完整追踪链路"""
        # 先从内存获取
        if trace_id in self.traces:
            return self.traces[trace_id]

        # 从磁盘加载
        records = []
        for date_dir in self.storage_path.iterdir():
            if not date_dir.is_dir():
                continue

            trace_file = date_dir / f"{trace_id}.jsonl"
            if trace_file.exists():
                with open(trace_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        data = json.loads(line)
                        record = TraceRecord(
                            trace_id=data['trace_id'],
                            stage=data['stage'],
                            input_data=data['input_data'],
                            output_data=data['output_data'],
                            metadata=data.get('metadata', {}),
                            quality_metrics=data.get('quality_metrics', {})
                        )
                        record.timestamp = data['timestamp']
                        records.append(record)

        # 缓存到内存
        self.traces[trace_id] = records
        return records

    def get_full_lineage(self, trace_id: str) -> Dict:
        """获取完整数据血缘"""
        records = self.get_trace(trace_id)

        lineage = {
            'trace_id': trace_id,
            'stages': [],
            'quality_summary': {},
            'timeline': []
        }

        for record in records:
            stage_info = {
                'stage': record.stage,
                'timestamp': record.timestamp,
                'input_summary': self._summarize_data(record.input_data),
                'output_summary': self._summarize_data(record.output_data),
                'metadata': record.metadata,
                'quality_metrics': record.quality_metrics
            }
            lineage['stages'].append(stage_info)
            lineage['timeline'].append({
                'stage': record.stage,
                'timestamp': record.timestamp
            })

            # 汇总质量指标
            for metric, value in record.quality_metrics.items():
                if metric not in lineage['quality_summary']:
                    lineage['quality_summary'][metric] = []
                lineage['quality_summary'][metric].append({
                    'stage': record.stage,
                    'value': value
                })

        return lineage

    def _summarize_data(self, data: Any) -> str:
        """数据摘要"""
        if isinstance(data, str):
            return data[:100] + '...' if len(data) > 100 else data
        elif isinstance(data, (list, tuple)):
            return f"[{len(data)} items]"
        elif isinstance(data, dict):
            return f"{{{len(data)} keys}}"
        else:
            return str(type(data).__name__)

    def export_trace(self, trace_id: str, output_path: str):
        """导出追踪记录"""
        lineage = self.get_full_lineage(trace_id)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(lineage, f, indent=2, ensure_ascii=False)

        print(f"追踪记录已导出: {output_path}")

    def search_traces(
        self,
        stage: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[str]:
        """搜索追踪记录"""
        trace_ids = set()

        for date_dir in self.storage_path.iterdir():
            if not date_dir.is_dir():
                continue

            # 日期过滤
            dir_date = date_dir.name
            if start_date and dir_date < start_date:
                continue
            if end_date and dir_date > end_date:
                continue

            # 遍历追踪文件
            for trace_file in date_dir.glob("*.jsonl"):
                trace_id = trace_file.stem

                # 阶段过滤
                if stage:
                    with open(trace_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            data = json.loads(line)
                            if data['stage'] == stage:
                                trace_ids.add(trace_id)
                                break
                else:
                    trace_ids.add(trace_id)

        return sorted(trace_ids)


class PipelineTracer:
    """管道追踪器（集成到训练流程）"""

    def __init__(self, tracer: E2ETracer):
        self.tracer = tracer

    def trace_raw_event(self, event: Dict) -> str:
        """追踪原始事件"""
        trace_id = self.tracer.generate_trace_id("event")

        self.tracer.record(
            trace_id=trace_id,
            stage="raw_event",
            input_data=None,
            output_data=event,
            metadata={
                'device_id': event.get('oaid'),
                'timestamp': event.get('timestamp')
            }
        )

        return trace_id

    def trace_session_slice(
        self,
        trace_id: str,
        events: List[Dict],
        session: Dict,
        quality_metrics: Dict = None
    ):
        """追踪 Session 切片"""
        self.tracer.record(
            trace_id=trace_id,
            stage="session_slice",
            input_data={'event_count': len(events)},
            output_data={
                'session_id': session.get('session_id'),
                'duration': session.get('end_time', 0) - session.get('start_time', 0),
                'event_count': len(session.get('events', []))
            },
            metadata={
                'device_id': session.get('device_id'),
                'slice_reason': session.get('slice_reason')
            },
            quality_metrics=quality_metrics or {}
        )

    def trace_log_to_text(
        self,
        trace_id: str,
        session: Dict,
        text: str,
        quality_metrics: Dict = None
    ):
        """追踪 Log-to-Text 转换"""
        self.tracer.record(
            trace_id=trace_id,
            stage="log_to_text",
            input_data={
                'session_id': session.get('session_id'),
                'event_count': len(session.get('events', []))
            },
            output_data={
                'text': text,
                'text_length': len(text)
            },
            metadata={
                'device_id': session.get('device_id')
            },
            quality_metrics=quality_metrics or {}
        )

    def trace_intent_label(
        self,
        trace_id: str,
        session_text: str,
        intent_data: Dict,
        quality_metrics: Dict = None
    ):
        """追踪意图标注"""
        self.tracer.record(
            trace_id=trace_id,
            stage="intent_label",
            input_data={
                'text_length': len(session_text)
            },
            output_data={
                'intents': intent_data.get('intents', []),
                'confidence': intent_data.get('confidence')
            },
            quality_metrics=quality_metrics or {}
        )

    def trace_vector_generation(
        self,
        trace_id: str,
        text_vector: List[float],
        intent_vector: List[float],
        combined_vector: List[float],
        quality_metrics: Dict = None
    ):
        """追踪向量生成"""
        import numpy as np

        self.tracer.record(
            trace_id=trace_id,
            stage="vector_generation",
            input_data={
                'text_vector_dim': len(text_vector),
                'intent_vector_dim': len(intent_vector)
            },
            output_data={
                'combined_vector_dim': len(combined_vector),
                'text_vector_norm': float(np.linalg.norm(text_vector)),
                'intent_vector_norm': float(np.linalg.norm(intent_vector)),
                'combined_vector_norm': float(np.linalg.norm(combined_vector))
            },
            quality_metrics=quality_metrics or {}
        )

    def trace_label_assignment(
        self,
        trace_id: str,
        device_id: str,
        label: int,
        quality_metrics: Dict = None
    ):
        """追踪标签分配"""
        self.tracer.record(
            trace_id=trace_id,
            stage="label_assignment",
            input_data={
                'device_id': device_id
            },
            output_data={
                'label': label
            },
            quality_metrics=quality_metrics or {}
        )


def main():
    """测试函数"""
    print("=" * 60)
    print("端到端追踪系统测试")
    print("=" * 60)

    # 创建追踪器
    tracer = E2ETracer(storage_path="data/traces")
    pipeline_tracer = PipelineTracer(tracer)

    # 模拟完整流程
    print("\n模拟完整追踪流程...")

    # 1. 原始事件
    event = {
        'oaid': 'device_000001',
        'timestamp': 1709251200,
        'app_pkg': 'com.autohome',
        'action': 'app_foreground'
    }
    trace_id = pipeline_tracer.trace_raw_event(event)
    print(f"1. 原始事件追踪: {trace_id}")

    # 2. Session 切片
    session = {
        'device_id': 'device_000001',
        'session_id': 'session_000001',
        'start_time': 1709251200,
        'end_time': 1709251500,
        'events': [event],
        'slice_reason': 'screen_off'
    }
    pipeline_tracer.trace_session_slice(
        trace_id=trace_id,
        events=[event],
        session=session,
        quality_metrics={'duration': 300, 'event_count': 1}
    )
    print("2. Session 切片追踪完成")

    # 3. Log-to-Text
    text = "用户在 5 分钟 内，使用了汽车之家。"
    pipeline_tracer.trace_log_to_text(
        trace_id=trace_id,
        session=session,
        text=text,
        quality_metrics={'text_length': len(text)}
    )
    print("3. Log-to-Text 追踪完成")

    # 4. 意图标注
    intent_data = {
        'intents': ['购车意图'],
        'confidence': 0.85
    }
    pipeline_tracer.trace_intent_label(
        trace_id=trace_id,
        session_text=text,
        intent_data=intent_data,
        quality_metrics={'confidence': 0.85}
    )
    print("4. 意图标注追踪完成")

    # 5. 向量生成
    import numpy as np
    text_vector = np.random.randn(128).tolist()
    intent_vector = np.random.randn(128).tolist()
    combined_vector = text_vector + intent_vector
    pipeline_tracer.trace_vector_generation(
        trace_id=trace_id,
        text_vector=text_vector,
        intent_vector=intent_vector,
        combined_vector=combined_vector,
        quality_metrics={'vector_norm': np.linalg.norm(combined_vector)}
    )
    print("5. 向量生成追踪完成")

    # 6. 标签分配
    pipeline_tracer.trace_label_assignment(
        trace_id=trace_id,
        device_id='device_000001',
        label=3,
        quality_metrics={'label': 3}
    )
    print("6. 标签分配追踪完成")

    # 获取完整血缘
    print(f"\n获取完整数据血缘: {trace_id}")
    lineage = tracer.get_full_lineage(trace_id)

    print(f"\n追踪阶段数: {len(lineage['stages'])}")
    for stage_info in lineage['stages']:
        print(f"  - {stage_info['stage']}: {stage_info['timestamp']}")

    # 导出追踪记录
    output_path = "data/traces/example_trace.json"
    tracer.export_trace(trace_id, output_path)

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
