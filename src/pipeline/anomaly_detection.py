"""异常检测和告警系统

检测向量分布异常、质量指标下降，自动告警和回滚。
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import numpy as np
from datetime import datetime, timedelta
from collections import deque

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class AnomalyDetector:
    """异常检测器"""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.history = {
            'vector_norms': deque(maxlen=window_size),
            'vector_means': deque(maxlen=window_size),
            'vector_stds': deque(maxlen=window_size),
            'quality_metrics': {}
        }

    def detect_vector_anomaly(self, vector: np.ndarray) -> Dict:
        """检测向量异常"""
        anomalies = []
        warnings = []

        # 计算向量统计量
        norm = np.linalg.norm(vector)
        mean = np.mean(vector)
        std = np.std(vector)

        # 检查 NaN 或 Inf
        if not np.isfinite(vector).all():
            anomalies.append({
                'type': 'invalid_values',
                'severity': 'critical',
                'message': '向量包含 NaN 或 Inf'
            })

        # 检查零向量
        if norm < 1e-6:
            anomalies.append({
                'type': 'zero_vector',
                'severity': 'critical',
                'message': '向量范数接近 0（零向量）'
            })

        # 与历史数据对比
        if len(self.history['vector_norms']) > 10:
            hist_norms = np.array(self.history['vector_norms'])
            hist_mean = np.mean(hist_norms)
            hist_std = np.std(hist_norms)

            # 检测范数异常（3-sigma 规则）
            if abs(norm - hist_mean) > 3 * hist_std:
                anomalies.append({
                    'type': 'norm_outlier',
                    'severity': 'high',
                    'message': f'向量范数异常: {norm:.4f} (历史均值: {hist_mean:.4f})'
                })

            # 检测分布偏移
            hist_means = np.array(self.history['vector_means'])
            hist_mean_avg = np.mean(hist_means)
            if abs(mean - hist_mean_avg) > 0.5:
                warnings.append({
                    'type': 'distribution_shift',
                    'severity': 'medium',
                    'message': f'向量均值偏移: {mean:.4f} (历史均值: {hist_mean_avg:.4f})'
                })

        # 更新历史
        self.history['vector_norms'].append(norm)
        self.history['vector_means'].append(mean)
        self.history['vector_stds'].append(std)

        return {
            'has_anomaly': len(anomalies) > 0,
            'anomalies': anomalies,
            'warnings': warnings,
            'statistics': {
                'norm': float(norm),
                'mean': float(mean),
                'std': float(std)
            }
        }

    def detect_quality_metric_anomaly(
        self,
        metric_name: str,
        metric_value: float,
        threshold: Optional[float] = None
    ) -> Dict:
        """检测质量指标异常"""
        anomalies = []
        warnings = []

        # 初始化指标历史
        if metric_name not in self.history['quality_metrics']:
            self.history['quality_metrics'][metric_name] = deque(maxlen=self.window_size)

        metric_history = self.history['quality_metrics'][metric_name]

        # 检查阈值
        if threshold is not None and metric_value < threshold:
            anomalies.append({
                'type': 'below_threshold',
                'severity': 'high',
                'message': f'{metric_name} 低于阈值: {metric_value:.4f} < {threshold:.4f}'
            })

        # 与历史数据对比
        if len(metric_history) > 10:
            hist_values = np.array(metric_history)
            hist_mean = np.mean(hist_values)
            hist_std = np.std(hist_values)

            # 检测突然下降
            if metric_value < hist_mean - 2 * hist_std:
                anomalies.append({
                    'type': 'sudden_drop',
                    'severity': 'high',
                    'message': f'{metric_name} 突然下降: {metric_value:.4f} (历史均值: {hist_mean:.4f})'
                })

            # 检测持续下降趋势
            if len(metric_history) >= 5:
                recent_values = list(metric_history)[-5:]
                if all(recent_values[i] > recent_values[i+1] for i in range(len(recent_values)-1)):
                    warnings.append({
                        'type': 'declining_trend',
                        'severity': 'medium',
                        'message': f'{metric_name} 持续下降趋势'
                    })

        # 更新历史
        metric_history.append(metric_value)

        return {
            'has_anomaly': len(anomalies) > 0,
            'anomalies': anomalies,
            'warnings': warnings,
            'current_value': float(metric_value)
        }


class AlertManager:
    """告警管理器"""

    def __init__(self, alert_log_path: str = "data/alerts/alerts.jsonl"):
        self.alert_log_path = Path(alert_log_path)
        self.alert_log_path.parent.mkdir(parents=True, exist_ok=True)

    def send_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        metadata: Dict = None
    ):
        """发送告警"""
        alert = {
            'type': alert_type,
            'severity': severity,
            'message': message,
            'metadata': metadata or {},
            'timestamp': datetime.now().isoformat()
        }

        # 记录到日志
        with open(self.alert_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alert, ensure_ascii=False) + '\n')

        # 输出到控制台
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🟢'
        }
        emoji = severity_emoji.get(severity, '⚪')
        print(f"{emoji} [{severity.upper()}] {alert_type}: {message}")

        # TODO: 集成外部告警系统（邮件、Slack、钉钉等）
        # self._send_email_alert(alert)
        # self._send_slack_alert(alert)

    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """获取最近的告警"""
        if not self.alert_log_path.exists():
            return []

        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_alerts = []

        with open(self.alert_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                alert = json.loads(line)
                alert_time = datetime.fromisoformat(alert['timestamp'])
                if alert_time >= cutoff_time:
                    recent_alerts.append(alert)

        return recent_alerts


class ModelRollbackManager:
    """模型回滚管理器"""

    def __init__(self, model_dir: str = "data/models"):
        self.model_dir = Path(model_dir)
        self.backup_dir = self.model_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_model(self, model_name: str) -> str:
        """备份模型"""
        model_path = self.model_dir / model_name

        if not model_path.exists():
            raise FileNotFoundError(f"模型文件不存在: {model_path}")

        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{model_name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name

        # 复制文件
        import shutil
        shutil.copy2(model_path, backup_path)

        print(f"模型已备份: {backup_path}")
        return str(backup_path)

    def rollback_model(self, model_name: str, backup_name: Optional[str] = None):
        """回滚模型"""
        model_path = self.model_dir / model_name

        # 如果未指定备份，使用最新的备份
        if backup_name is None:
            backups = sorted(self.backup_dir.glob(f"{model_name}.*.backup"), reverse=True)
            if not backups:
                raise FileNotFoundError(f"没有找到 {model_name} 的备份")
            backup_path = backups[0]
        else:
            backup_path = self.backup_dir / backup_name

        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        # 备份当前模型
        if model_path.exists():
            self.backup_model(model_name)

        # 恢复备份
        import shutil
        shutil.copy2(backup_path, model_path)

        print(f"模型已回滚: {model_path} <- {backup_path}")

    def list_backups(self, model_name: str) -> List[str]:
        """列出模型备份"""
        backups = sorted(self.backup_dir.glob(f"{model_name}.*.backup"), reverse=True)
        return [backup.name for backup in backups]


class PipelineMonitor:
    """管道监控器"""

    def __init__(
        self,
        anomaly_detector: AnomalyDetector,
        alert_manager: AlertManager,
        rollback_manager: ModelRollbackManager
    ):
        self.anomaly_detector = anomaly_detector
        self.alert_manager = alert_manager
        self.rollback_manager = rollback_manager

        # 质量指标阈值
        self.thresholds = {
            'precision@100': 0.45,
            'recall@100': 0.25,
            'auc': 0.70,
            'conversion_rate': 0.04,
            'high_intent_concentration': 0.15
        }

    def monitor_vector(self, vector: np.ndarray, trace_id: str):
        """监控向量生成"""
        result = self.anomaly_detector.detect_vector_anomaly(vector)

        # 发送告警
        for anomaly in result['anomalies']:
            self.alert_manager.send_alert(
                alert_type=anomaly['type'],
                severity=anomaly['severity'],
                message=anomaly['message'],
                metadata={'trace_id': trace_id}
            )

        for warning in result['warnings']:
            self.alert_manager.send_alert(
                alert_type=warning['type'],
                severity=warning['severity'],
                message=warning['message'],
                metadata={'trace_id': trace_id}
            )

        return result

    def monitor_quality_metrics(self, metrics: Dict):
        """监控质量指标"""
        results = {}

        for metric_name, metric_value in metrics.items():
            threshold = self.thresholds.get(metric_name)
            result = self.anomaly_detector.detect_quality_metric_anomaly(
                metric_name=metric_name,
                metric_value=metric_value,
                threshold=threshold
            )

            results[metric_name] = result

            # 发送告警
            for anomaly in result['anomalies']:
                self.alert_manager.send_alert(
                    alert_type=anomaly['type'],
                    severity=anomaly['severity'],
                    message=anomaly['message'],
                    metadata={'metric': metric_name, 'value': metric_value}
                )

                # 如果是关键指标严重下降，触发回滚
                if anomaly['severity'] == 'high' and metric_name in ['precision@100', 'auc']:
                    self._trigger_rollback(metric_name, metric_value)

        return results

    def _trigger_rollback(self, metric_name: str, metric_value: float):
        """触发模型回滚"""
        print(f"\n⚠️ 关键指标严重下降，触发自动回滚: {metric_name} = {metric_value:.4f}")

        try:
            # 回滚 SupCon 模型
            self.rollback_manager.rollback_model("supcon_model.pth")

            # 回滚 Student 模型
            self.rollback_manager.rollback_model("intent_student_model.pth")

            self.alert_manager.send_alert(
                alert_type='model_rollback',
                severity='critical',
                message=f'模型已自动回滚（原因: {metric_name} = {metric_value:.4f}）',
                metadata={'metric': metric_name, 'value': metric_value}
            )

            print("✓ 模型回滚完成")

        except Exception as e:
            self.alert_manager.send_alert(
                alert_type='rollback_failed',
                severity='critical',
                message=f'模型回滚失败: {str(e)}',
                metadata={'metric': metric_name, 'value': metric_value}
            )
            print(f"✗ 模型回滚失败: {e}")


def main():
    """测试函数"""
    print("=" * 60)
    print("异常检测和告警系统测试")
    print("=" * 60)

    # 创建组件
    anomaly_detector = AnomalyDetector(window_size=100)
    alert_manager = AlertManager(alert_log_path="data/alerts/test_alerts.jsonl")
    rollback_manager = ModelRollbackManager(model_dir="data/models")
    monitor = PipelineMonitor(anomaly_detector, alert_manager, rollback_manager)

    # 测试向量异常检测
    print("\n测试 1: 正常向量")
    normal_vector = np.random.randn(256)
    result = monitor.monitor_vector(normal_vector, "trace_001")
    print(f"异常检测结果: {result['has_anomaly']}")

    # 添加一些历史数据
    for i in range(20):
        vector = np.random.randn(256)
        monitor.monitor_vector(vector, f"trace_{i:03d}")

    print("\n测试 2: 零向量")
    zero_vector = np.zeros(256)
    result = monitor.monitor_vector(zero_vector, "trace_zero")
    print(f"异常检测结果: {result['has_anomaly']}")

    print("\n测试 3: 异常向量（范数过大）")
    abnormal_vector = np.random.randn(256) * 100
    result = monitor.monitor_vector(abnormal_vector, "trace_abnormal")
    print(f"异常检测结果: {result['has_anomaly']}")

    # 测试质量指标监控
    print("\n测试 4: 正常质量指标")
    metrics = {
        'precision@100': 0.55,
        'recall@100': 0.35,
        'auc': 0.78
    }
    results = monitor.monitor_quality_metrics(metrics)
    print(f"质量指标监控完成")

    print("\n测试 5: 异常质量指标（低于阈值）")
    metrics = {
        'precision@100': 0.40,  # 低于阈值 0.45
        'auc': 0.65  # 低于阈值 0.70
    }
    results = monitor.monitor_quality_metrics(metrics)
    print(f"质量指标监控完成")

    # 查看最近的告警
    print("\n最近的告警:")
    recent_alerts = alert_manager.get_recent_alerts(hours=24)
    for alert in recent_alerts[-5:]:  # 显示最近 5 条
        print(f"  [{alert['severity']}] {alert['type']}: {alert['message']}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
