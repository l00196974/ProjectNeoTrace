"""数据管道验证门禁

在每个环节设置质量门禁，确保数据质量。
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import numpy as np
from datetime import datetime

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class ValidationResult:
    """验证结果"""

    def __init__(self, stage: str, passed: bool, errors: List[str] = None, warnings: List[str] = None):
        self.stage = stage
        self.passed = passed
        self.errors = errors or []
        self.warnings = warnings or []
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            'stage': self.stage,
            'passed': self.passed,
            'errors': self.errors,
            'warnings': self.warnings,
            'timestamp': self.timestamp
        }


class RawEventValidator:
    """原始事件验证器"""

    REQUIRED_FIELDS = ['oaid', 'timestamp', 'app_pkg', 'action']
    VALID_ACTIONS = [
        'touch_scroll', 'app_foreground', 'app_background',
        'screen_on', 'screen_off', 'location_update'
    ]

    @staticmethod
    def validate(event: Dict) -> ValidationResult:
        """验证原始事件"""
        errors = []
        warnings = []

        # 检查必填字段
        for field in RawEventValidator.REQUIRED_FIELDS:
            if field not in event:
                errors.append(f"缺少必填字段: {field}")

        if errors:
            return ValidationResult('raw_event', False, errors, warnings)

        # 检查数据格式
        if not isinstance(event.get('oaid'), str) or len(event['oaid']) == 0:
            errors.append("oaid 必须是非空字符串")

        if not isinstance(event.get('timestamp'), (int, float)) or event['timestamp'] <= 0:
            errors.append("timestamp 必须是正整数")

        if not isinstance(event.get('app_pkg'), str):
            errors.append("app_pkg 必须是字符串")

        if event.get('action') not in RawEventValidator.VALID_ACTIONS:
            warnings.append(f"未知的 action: {event.get('action')}")

        # 检查时间戳合理性
        current_timestamp = datetime.now().timestamp()
        if event.get('timestamp', 0) > current_timestamp:
            errors.append("timestamp 不能是未来时间")

        # 检查 payload
        if 'payload' in event and not isinstance(event['payload'], dict):
            errors.append("payload 必须是字典类型")

        passed = len(errors) == 0
        return ValidationResult('raw_event', passed, errors, warnings)


class SessionValidator:
    """Session 切片验证器"""

    @staticmethod
    def validate(session: Dict) -> ValidationResult:
        """验证 Session 切片"""
        errors = []
        warnings = []

        # 检查必填字段
        required_fields = ['device_id', 'session_id', 'start_time', 'end_time', 'events']
        for field in required_fields:
            if field not in session:
                errors.append(f"缺少必填字段: {field}")

        if errors:
            return ValidationResult('session', False, errors, warnings)

        # 检查 Session 时长合理性
        duration = session['end_time'] - session['start_time']
        if duration <= 0:
            errors.append("Session 时长必须大于 0")
        elif duration > 86400:  # 24 小时
            warnings.append(f"Session 时长过长: {duration} 秒")

        # 检查事件数量
        event_count = len(session.get('events', []))
        if event_count == 0:
            errors.append("Session 必须包含至少一个事件")
        elif event_count > 10000:
            warnings.append(f"Session 事件数量过多: {event_count}")

        # 检查切片规则触发原因
        if 'slice_reason' not in session:
            warnings.append("缺少 slice_reason 字段")

        # 检查事件时间顺序
        events = session.get('events', [])
        for i in range(1, len(events)):
            if events[i].get('timestamp', 0) < events[i-1].get('timestamp', 0):
                errors.append(f"事件时间顺序错误: 事件 {i} 的时间早于事件 {i-1}")

        passed = len(errors) == 0
        return ValidationResult('session', passed, errors, warnings)


class LogToTextValidator:
    """Log-to-Text 验证器"""

    @staticmethod
    def validate(session_id: str, text: str, session: Dict) -> ValidationResult:
        """验证 Log-to-Text 转换"""
        errors = []
        warnings = []

        # 检查文本长度
        if not text or len(text.strip()) == 0:
            errors.append("文本不能为空")
        elif len(text) < 10:
            warnings.append(f"文本过短: {len(text)} 字符")
        elif len(text) > 1000:
            warnings.append(f"文本过长: {len(text)} 字符")

        # 检查关键信息完整性
        if session.get('app_pkg_list'):
            # 至少应该提到一个应用
            has_app_mention = any(app in text for app in session['app_pkg_list'])
            if not has_app_mention:
                warnings.append("文本中未提及任何应用")

        # 检查时长信息
        if 'session_duration' in session and session['session_duration'] > 0:
            # 应该包含时长相关的词
            time_keywords = ['分钟', '小时', '秒', 'minute', 'hour', 'second']
            has_time_mention = any(keyword in text for keyword in time_keywords)
            if not has_time_mention:
                warnings.append("文本中未提及时长信息")

        # 检查映射覆盖率
        if 'app_pkg_list' in session:
            unmapped_apps = []
            for app_pkg in session['app_pkg_list']:
                if app_pkg in text:  # 如果原始包名出现在文本中，说明未映射
                    unmapped_apps.append(app_pkg)

            if unmapped_apps:
                warnings.append(f"以下应用未映射: {', '.join(unmapped_apps)}")

        passed = len(errors) == 0
        return ValidationResult('log_to_text', passed, errors, warnings)


class IntentLabelValidator:
    """意图标注验证器"""

    @staticmethod
    def validate(session_id: str, intent_data: Dict) -> ValidationResult:
        """验证意图标注"""
        errors = []
        warnings = []

        # 检查 LLM 响应格式
        required_fields = ['intents', 'confidence']
        for field in required_fields:
            if field not in intent_data:
                errors.append(f"缺少必填字段: {field}")

        if errors:
            return ValidationResult('intent_label', False, errors, warnings)

        # 检查意图数组
        intents = intent_data.get('intents', [])
        if not isinstance(intents, list):
            errors.append("intents 必须是数组")
        elif len(intents) == 0:
            warnings.append("未识别到任何意图")
        elif len(intents) > 11:
            errors.append(f"意图数量过多: {len(intents)}")

        # 检查置信度合理性
        confidence = intent_data.get('confidence')
        if not isinstance(confidence, (int, float)):
            errors.append("confidence 必须是数字")
        elif confidence < 0 or confidence > 1:
            errors.append(f"confidence 必须在 [0, 1] 范围内: {confidence}")
        elif confidence < 0.3:
            warnings.append(f"置信度较低: {confidence}")

        # 检查意图向量
        if 'intent_vector' in intent_data:
            intent_vector = intent_data['intent_vector']
            if not isinstance(intent_vector, (list, np.ndarray)):
                errors.append("intent_vector 必须是数组")
            elif len(intent_vector) != 128:
                errors.append(f"intent_vector 维度错误: {len(intent_vector)}, 期望 128")

        passed = len(errors) == 0
        return ValidationResult('intent_label', passed, errors, warnings)


class VectorValidator:
    """向量生成验证器"""

    @staticmethod
    def validate(session_id: str, vector: np.ndarray, vector_type: str = 'combined') -> ValidationResult:
        """验证向量生成"""
        errors = []
        warnings = []

        # 检查向量维度
        expected_dims = {
            'text': 128,
            'intent': 128,
            'combined': 256
        }

        expected_dim = expected_dims.get(vector_type, 256)
        if len(vector) != expected_dim:
            errors.append(f"向量维度错误: {len(vector)}, 期望 {expected_dim}")

        # 检查向量范数
        norm = np.linalg.norm(vector)
        if norm == 0:
            errors.append("向量范数为 0（零向量）")
        elif norm > 100:
            warnings.append(f"向量范数过大: {norm}")

        # 检查向量分布
        if not np.isfinite(vector).all():
            errors.append("向量包含 NaN 或 Inf")

        # 检查向量值范围
        if np.abs(vector).max() > 100:
            warnings.append(f"向量值范围过大: max={np.abs(vector).max()}")

        passed = len(errors) == 0
        return ValidationResult(f'{vector_type}_vector', passed, errors, warnings)


class PipelineValidator:
    """管道验证器"""

    def __init__(self):
        self.raw_event_validator = RawEventValidator()
        self.session_validator = SessionValidator()
        self.log_to_text_validator = LogToTextValidator()
        self.intent_label_validator = IntentLabelValidator()
        self.vector_validator = VectorValidator()

    def validate_pipeline(self, data: Dict) -> Dict[str, ValidationResult]:
        """验证完整管道"""
        results = {}

        # 1. 验证原始事件
        if 'raw_events' in data:
            for event in data['raw_events']:
                result = self.raw_event_validator.validate(event)
                if not result.passed:
                    results['raw_event'] = result
                    return results  # 早期失败

        # 2. 验证 Session 切片
        if 'session' in data:
            result = self.session_validator.validate(data['session'])
            results['session'] = result
            if not result.passed:
                return results

        # 3. 验证 Log-to-Text
        if 'session_text' in data and 'session' in data:
            result = self.log_to_text_validator.validate(
                data['session'].get('session_id', 'unknown'),
                data['session_text'],
                data['session']
            )
            results['log_to_text'] = result
            if not result.passed:
                return results

        # 4. 验证意图标注
        if 'intent_data' in data:
            result = self.intent_label_validator.validate(
                data.get('session', {}).get('session_id', 'unknown'),
                data['intent_data']
            )
            results['intent_label'] = result
            if not result.passed:
                return results

        # 5. 验证向量生成
        if 'text_vector' in data:
            result = self.vector_validator.validate(
                data.get('session', {}).get('session_id', 'unknown'),
                np.array(data['text_vector']),
                'text'
            )
            results['text_vector'] = result

        if 'intent_vector' in data:
            result = self.vector_validator.validate(
                data.get('session', {}).get('session_id', 'unknown'),
                np.array(data['intent_vector']),
                'intent'
            )
            results['intent_vector'] = result

        if 'combined_vector' in data:
            result = self.vector_validator.validate(
                data.get('session', {}).get('session_id', 'unknown'),
                np.array(data['combined_vector']),
                'combined'
            )
            results['combined_vector'] = result

        return results


def validate_pipeline(data_path: str) -> Dict:
    """验证管道数据"""
    print(f"验证管道数据: {data_path}")

    # 加载数据
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 验证
    validator = PipelineValidator()
    results = validator.validate_pipeline(data)

    # 输出结果
    print("\n验证结果:")
    all_passed = True
    for stage, result in results.items():
        status = "✓" if result.passed else "✗"
        print(f"  {status} {stage}")

        if result.errors:
            print(f"    错误:")
            for error in result.errors:
                print(f"      - {error}")
            all_passed = False

        if result.warnings:
            print(f"    警告:")
            for warning in result.warnings:
                print(f"      - {warning}")

    return {
        'passed': all_passed,
        'results': {stage: result.to_dict() for stage, result in results.items()}
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='数据管道验证')
    parser.add_argument('--data', type=str, required=True, help='数据文件路径')
    parser.add_argument('--output', type=str, help='输出报告路径')

    args = parser.parse_args()

    result = validate_pipeline(args.data)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n验证报告已保存: {args.output}")

    sys.exit(0 if result['passed'] else 1)
