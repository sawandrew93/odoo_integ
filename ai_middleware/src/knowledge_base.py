import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Tuple
import json
import os

class KnowledgeBase:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.encoder = SentenceTransformer(model_name)
        self.index = None
        self.documents = []
        self.embeddings = []
        
    def add_documents(self, documents: List[str]):
        """Add documents to knowledge base"""
        self.documents.extend(documents)
        new_embeddings = self.encoder.encode(documents)
        
        if len(self.embeddings) == 0:
            self.embeddings = new_embeddings
            dimension = new_embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dimension)
        else:
            self.embeddings = np.vstack([self.embeddings, new_embeddings])
            
        self.index.add(new_embeddings.astype('float32'))
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Search for relevant documents"""
        if not self.index or len(self.documents) == 0:
            return []
            
        query_embedding = self.encoder.encode([query])
        scores, indices = self.index.search(query_embedding.astype('float32'), top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                results.append((self.documents[idx], float(score)))
        
        return results
    
    def load_from_directory(self, directory: str):
        """Load text files from directory"""
        documents = []
        for filename in os.listdir(directory):
            if filename.endswith('.txt'):
                with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        documents.append(content)
        
        if documents:
            self.add_documents(documents)