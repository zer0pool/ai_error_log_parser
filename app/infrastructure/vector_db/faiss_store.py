import os
import faiss
import pickle
import numpy as np
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from app.domain.repository.vector_store import VectorStore

class FaissVectorStore(VectorStore):
    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.metadata = []
        self.dimension = 384

    def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        if self.index is None:
            return []
        query_vector = self.model.encode([query])
        distances, indices = self.index.search(np.array(query_vector).astype('float32'), k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.metadata):
                item = self.metadata[idx].copy()
                item['distance'] = float(dist)
                results.append(item)
        return results

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]]):
        embeddings = self.model.encode(texts)
        if self.index is None:
            self.dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(self.dimension)
        self.index.add(np.array(embeddings).astype('float32'))
        self.metadata.extend(metadatas)

    def save(self, index_path: str, metadata_path: str):
        if self.index:
            faiss.write_index(self.index, index_path)
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)

    def load(self, index_path: str, metadata_path: str) -> bool:
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            self.index = faiss.read_index(index_path)
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            return True
        return False
