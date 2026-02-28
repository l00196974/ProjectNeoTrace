"""Flask API 接口

提供在线推理服务。
"""

import sys
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import time

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.serving.inference import ProductionInference
from src.agent.log_to_text import LogToTextConverter

# 创建 Flask 应用
app = Flask(__name__)
CORS(app)

# 全局推理引擎（延迟初始化）
inference_engine = None
log_to_text_converter = None


def get_inference_engine():
    """获取推理引擎（单例模式）"""
    global inference_engine
    if inference_engine is None:
        student_model_path = PROJECT_ROOT / "data" / "models" / "intent_student_model.pth"
        supcon_model_path = PROJECT_ROOT / "data" / "models" / "supcon_model.pth"

        inference_engine = ProductionInference(
            student_model_path=str(student_model_path),
            supcon_model_path=str(supcon_model_path),
            use_mock_embedding=True,  # 使用 Mock 向量化器
        )
    return inference_engine


def get_log_to_text_converter():
    """获取 Log-to-Text 转换器（单例模式）"""
    global log_to_text_converter
    if log_to_text_converter is None:
        log_to_text_converter = LogToTextConverter()
    return log_to_text_converter


@app.route("/health", methods=["GET"])
def health():
    """健康检查接口"""
    return jsonify({"status": "ok", "timestamp": int(time.time())})


@app.route("/predict", methods=["POST"])
def predict():
    """
    预测接口

    请求格式：
    {
        "session": {
            "device_id": "device_000001",
            "app_switch_freq": 5,
            "config_page_dwell": 180,
            "finance_page_dwell": 60,
            "time_tension_bucket": 2,
            "session_duration": 300,
            "event_count": 20,
            "lbs_poi_list": ["home", "auto_market"],
            "app_pkg_list": ["com.autohome", "com.yiche"]
        }
    }

    响应格式：
    {
        "device_id": "device_000001",
        "lead_score": 0.75,
        "intent_probs": [0.1, 0.2, ...],
        "timestamp": 1234567890
    }
    """
    try:
        # 解析请求
        data = request.json
        if not data or "session" not in data:
            return jsonify({"error": "Missing session data"}), 400

        session = data["session"]

        # 获取推理引擎
        engine = get_inference_engine()
        converter = get_log_to_text_converter()

        # 1. Log-to-Text 转换
        session_text = converter.convert_session(session)

        # 2. 提取 Session 特征（256-dim）
        session_features = np.array(
            [
                float(session.get("app_switch_freq", 0)),
                float(session.get("config_page_dwell", 0)) / 60.0,
                float(session.get("finance_page_dwell", 0)) / 60.0,
                float(session.get("time_tension_bucket", 0)),
                float(session.get("session_duration", 0)) / 3600.0,
                float(session.get("event_count", 0)) / 100.0,
            ]
            + [0.0] * 250  # 填充到 256 维
        )

        # 3. 预测
        result = engine.predict_lead_score(session_text, session_features)

        # 4. 构建响应
        response = {
            "device_id": session.get("device_id", "unknown"),
            "lead_score": result["lead_score"],
            "intent_probs": result["intent_probs"],
            "timestamp": int(time.time()),
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/batch_predict", methods=["POST"])
def batch_predict():
    """
    批量预测接口

    请求格式：
    {
        "sessions": [
            {...},
            {...}
        ]
    }

    响应格式：
    {
        "results": [
            {"device_id": "...", "lead_score": 0.75, ...},
            {"device_id": "...", "lead_score": 0.82, ...}
        ],
        "timestamp": 1234567890
    }
    """
    try:
        # 解析请求
        data = request.json
        if not data or "sessions" not in data:
            return jsonify({"error": "Missing sessions data"}), 400

        sessions = data["sessions"]

        # 获取推理引擎
        engine = get_inference_engine()
        converter = get_log_to_text_converter()

        # 批量预测
        results = []
        for session in sessions:
            # Log-to-Text 转换
            session_text = converter.convert_session(session)

            # 提取特征
            session_features = np.array(
                [
                    float(session.get("app_switch_freq", 0)),
                    float(session.get("config_page_dwell", 0)) / 60.0,
                    float(session.get("finance_page_dwell", 0)) / 60.0,
                    float(session.get("time_tension_bucket", 0)),
                    float(session.get("session_duration", 0)) / 3600.0,
                    float(session.get("event_count", 0)) / 100.0,
                ]
                + [0.0] * 250
            )

            # 预测
            result = engine.predict_lead_score(session_text, session_features)

            results.append(
                {
                    "device_id": session.get("device_id", "unknown"),
                    "lead_score": result["lead_score"],
                    "intent_probs": result["intent_probs"],
                }
            )

        response = {"results": results, "timestamp": int(time.time())}

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    """主函数"""
    import os

    # 从环境变量读取配置
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    print("=" * 60)
    print("ProjectNeoTrace 推理服务")
    print("=" * 60)
    print(f"\n服务地址：http://{host}:{port}")
    print(f"健康检查：http://{host}:{port}/health")
    print(f"预测接口：http://{host}:{port}/predict")
    print(f"批量预测：http://{host}:{port}/batch_predict")
    print("\n启动服务...")

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
