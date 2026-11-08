from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseLLMProvider(ABC):
    """LLMプロバイダの抽象基底クラス"""

    @abstractmethod
    def is_available(self) -> bool:
        """プロバイダが現在利用可能か（サーバー起動中、CLI存在など）"""
        pass

    @abstractmethod
    def generate_explanation(self, finding: Dict[str, Any], context_code: str) -> str:
        """
        脆弱性情報と周辺コードを受け取り、Markdown形式の日本語解説・修正提案を返す。
        """
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """利用可能なモデル一覧を返す"""
        pass

