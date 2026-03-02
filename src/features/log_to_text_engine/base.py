"""Log-to-Text 转换引擎基础类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class ConversionContext:
    """转换上下文

    封装 session 数据和元数据，传递给规则进行匹配和转换
    """
    session: Dict[str, Any]  # Session 数据
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class ConversionResult:
    """转换结果

    标准化的转换结果，包含成功标志、文本、规则信息
    """
    success: bool  # 是否成功
    text: str  # 生成的文本
    rule_id: str  # 匹配的规则 ID
    priority: int  # 规则优先级
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外信息


class BaseConversionRule(ABC):
    """转换规则基类

    所有转换规则必须继承此类并实现 match() 和 convert() 方法
    """

    def __init__(
        self,
        rule_id: str,
        priority: int = 50,
        enabled: bool = True,
        params: Dict[str, Any] = None
    ):
        """初始化规则

        Args:
            rule_id: 规则唯一标识
            priority: 优先级（数值越大优先级越高）
            enabled: 是否启用
            params: 规则参数
        """
        self.rule_id = rule_id
        self.priority = priority
        self.enabled = enabled
        self.params = params or {}

    @abstractmethod
    def match(self, context: ConversionContext) -> bool:
        """判断规则是否匹配

        Args:
            context: 转换上下文

        Returns:
            是否匹配
        """
        pass

    @abstractmethod
    def convert(self, context: ConversionContext) -> ConversionResult:
        """执行转换

        Args:
            context: 转换上下文

        Returns:
            转换结果
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.rule_id}, priority={self.priority}, enabled={self.enabled})"
