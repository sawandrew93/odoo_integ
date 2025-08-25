from typing import List, Tuple
import os
import numpy as np
import google.generativeai as genai

class KnowledgeBase:
    def __init__(self, api_key: str):
        self.documents = []
        self.embeddings = []
        genai.configure(api_key=api_key)
        
    def add_documents(self, documents: List[str]):
        """Add documents to knowledge base with embeddings"""
        self.documents.extend(documents)
        for doc in documents:
            embedding = genai.embed_content(
                model="models/text-embedding-001",
                content=doc
            )["embedding"]
            self.embeddings.append(embedding)
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Semantic search using embeddings"""
        if not self.documents:
            return []
            
        try:
            query_embedding = genai.embed_content(
                model="models/text-embedding-001",
                content=query
            )["embedding"]
            
            similarities = []
            for i, doc_embedding in enumerate(self.embeddings):
                similarity = np.dot(query_embedding, doc_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                )
                similarities.append((self.documents[i], similarity))
            
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_k]
            
        except Exception as e:
            print(f"Embedding search error: {e}")
            # Fallback to keyword search
            return self._keyword_search(query, top_k)
    
    def _keyword_search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Fallback keyword search"""
        query_lower = query.lower()
        results = []
        
        for doc in self.documents:
            doc_lower = doc.lower()
            query_words = [w for w in query_lower.split() if len(w) > 2]
            if query_words:
                score = sum(1 for word in query_words if word in doc_lower)
                if score > 0:
                    results.append((doc, score / len(query_words)))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
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