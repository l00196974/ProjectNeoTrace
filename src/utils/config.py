"""配置管理模块"""
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """全局配置类"""

    # 项目根目录
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # LLM API 配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))

    # 数据路径
    DATA_RAW_DIR = PROJECT_ROOT / os.getenv("DATA_RAW_DIR", "data/raw")
    DATA_PROCESSED_DIR = PROJECT_ROOT / os.getenv("DATA_PROCESSED_DIR", "data/processed")
    DATA_LABELS_DIR = PROJECT_ROOT / os.getenv("DATA_LABELS_DIR", "data/labels")
    DATA_MODELS_DIR = PROJECT_ROOT / os.getenv("DATA_MODELS_DIR", "data/models")

    # 模型配置
    STUDENT_MODEL_HIDDEN_DIM = int(os.getenv("STUDENT_MODEL_HIDDEN_DIM", "64"))
    STUDENT_MODEL_INTENT_DIM = int(os.getenv("STUDENT_MODEL_INTENT_DIM", "11"))
    STUDENT_MODEL_EMBEDDING_DIM = int(os.getenv("STUDENT_MODEL_EMBEDDING_DIM", "128"))

    PROJECTION_HEAD_INPUT_DIM = int(os.getenv("PROJECTION_HEAD_INPUT_DIM", "256"))
    PROJECTION_HEAD_HIDDEN_DIM = int(os.getenv("PROJECTION_HEAD_HIDDEN_DIM", "128"))
    PROJECTION_HEAD_OUTPUT_DIM = int(os.getenv("PROJECTION_HEAD_OUTPUT_DIM", "128"))

    # 训练配置
    STUDENT_MODEL_EPOCHS = int(os.getenv("STUDENT_MODEL_EPOCHS", "30"))
    STUDENT_MODEL_BATCH_SIZE = int(os.getenv("STUDENT_MODEL_BATCH_SIZE", "32"))
    STUDENT_MODEL_LR = float(os.getenv("STUDENT_MODEL_LR", "0.001"))

    SUPCON_EPOCHS = int(os.getenv("SUPCON_EPOCHS", "30"))
    SUPCON_BATCH_SIZE = int(os.getenv("SUPCON_BATCH_SIZE", "16"))
    SUPCON_LR = float(os.getenv("SUPCON_LR", "0.001"))
    SUPCON_TEMPERATURE = float(os.getenv("SUPCON_TEMPERATURE", "0.07"))

    # 推理服务配置
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR = PROJECT_ROOT / os.getenv("LOG_DIR", "logs")

    @classmethod
    def ensure_dirs(cls):
        """确保所有必要的目录存在"""
        for dir_path in [
            cls.DATA_RAW_DIR,
            cls.DATA_PROCESSED_DIR,
            cls.DATA_LABELS_DIR,
            cls.DATA_MODELS_DIR,
            cls.LOG_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """转换为字典"""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and not callable(getattr(cls, key))
        }


# 初始化时确保目录存在
Config.ensure_dirs()
