"""LLM API 客户端封装

支持 OpenAI 和 Anthropic API。
"""

import json
import time
import logging
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    @abstractmethod
    def call(self, prompt: str, **kwargs) -> str:
        """调用 LLM API。

        Args:
            prompt: 提示词
            **kwargs: 其他参数

        Returns:
            LLM 响应文本
        """
        pass

    def call_with_retry(self, prompt: str, max_retries: int = 3, **kwargs) -> str:
        """调用 LLM API 并支持重试。

        Args:
            prompt: 输入 Prompt
            max_retries: 最大重试次数
            **kwargs: 其他参数

        Returns:
            LLM 响应文本

        Raises:
            Exception: API 调用失败
        """
        for attempt in range(max_retries):
            try:
                response = self.call(prompt, **kwargs)
                if response:  # 成功返回非空响应
                    return response
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"LLM 调用失败（已重试 {max_retries} 次）: {e}")
                    raise

                wait_time = 2 ** attempt  # 指数退避
                logger.warning(f"LLM 调用失败，{wait_time}秒后重试（第 {attempt + 1}/{max_retries} 次）: {e}")
                time.sleep(wait_time)

        raise Exception("LLM 调用失败：返回空响应")

    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """获取文本向量。

        Args:
            text: 输入文本

        Returns:
            向量（128-dim）
        """
        pass


class OpenAIClient(LLMClient):
    """OpenAI API 客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 500,
    ):
        """
        初始化 OpenAI 客户端

        Args:
            api_key: API Key
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
        """
        try:
            import openai
            self.openai = openai
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("请安装 openai 库：pip install openai")

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def call(self, prompt: str, **kwargs) -> str:
        """调用 OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", self.temperature),
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API 调用失败：{e}")
            return ""

    def get_embedding(self, text: str) -> List[float]:
        """获取文本向量（使用 OpenAI Embedding API）"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002", input=text
            )
            # OpenAI 返回 1536 维，我们截取前 128 维
            embedding = response.data[0].embedding[:128]
            return embedding
        except Exception as e:
            print(f"OpenAI Embedding API 调用失败：{e}")
            return [0.0] * 128


class AnthropicClient(LLMClient):
    """Anthropic API 客户端"""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-2",
        temperature: float = 0.7,
        max_tokens: int = 500,
    ):
        """
        初始化 Anthropic 客户端

        Args:
            api_key: API Key
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
        """
        try:
            import anthropic
            self.anthropic = anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("请安装 anthropic 库：pip install anthropic")

        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def call(self, prompt: str, **kwargs) -> str:
        """调用 Anthropic API"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", self.max_tokens),
                temperature=kwargs.get("temperature", self.temperature),
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception as e:
            print(f"Anthropic API 调用失败：{e}")
            return ""

    def get_embedding(self, text: str) -> List[float]:
        """
        获取文本向量

        注意：Anthropic 不提供 Embedding API，这里返回模拟向量
        实际使用时应该用 BGE-m3 或其他开源模型
        """
        print("警告：Anthropic 不提供 Embedding API，返回零向量")
        return [0.0] * 128


class MockLLMClient(LLMClient):
    """Mock LLM 客户端（用于测试）"""

    def __init__(self):
        """初始化 Mock 客户端"""
        pass

    def call(self, prompt: str, **kwargs) -> str:
        """返回模拟响应"""
        # 模拟 LLM 响应（使用新的置信度格式）
        mock_response = {
            "intents": [
                {
                    "name": "automotive_purchase",
                    "confidence": "medium",
                    "reasoning": "用户浏览了多款车型配置页",
                },
                {
                    "name": "automotive_comparison",
                    "confidence": "high",
                    "reasoning": "用户对比了不同车型",
                },
            ],
            "primary_intent": "automotive_comparison",
            "urgency_score": 7,
        }
        return json.dumps(mock_response, ensure_ascii=False)

    def get_embedding(self, text: str) -> List[float]:
        """返回模拟向量"""
        import random

        random.seed(hash(text) % (2**32))
        return [random.random() for _ in range(128)]


def create_llm_client(
    provider: str = "openai",
    api_key: str = "",
    model: str = "",
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> LLMClient:
    """
    创建 LLM 客户端

    Args:
        provider: 提供商（openai, anthropic, mock）
        api_key: API Key
        model: 模型名称
        temperature: 温度参数
        max_tokens: 最大 token 数

    Returns:
        LLM 客户端实例
    """
    if provider == "openai":
        if not model:
            model = "gpt-3.5-turbo"
        return OpenAIClient(api_key, model, temperature, max_tokens)
    elif provider == "anthropic":
        if not model:
            model = "claude-2"
        return AnthropicClient(api_key, model, temperature, max_tokens)
    elif provider == "mock":
        return MockLLMClient()
    else:
        raise ValueError(f"不支持的 LLM 提供商：{provider}")
