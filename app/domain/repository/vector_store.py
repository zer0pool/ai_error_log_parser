from abc import ABC, abstractmethod
from typing import List, Dict, Any

class VectorStore(ABC):
    @abstractmethod
    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        pass

    @abstractmethod
    def save(self, index_path: str, metadata_path: str):
        pass

    @abstractmethod
    def load(self, index_path: str, metadata_path: str) -> bool:
        pass
