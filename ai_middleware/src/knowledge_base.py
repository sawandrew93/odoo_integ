from typing import List, Tuple
import os

class KnowledgeBase:
    def __init__(self):
        self.documents = []
        
    def add_documents(self, documents: List[str]):
        """Add documents to knowledge base"""
        self.documents.extend(documents)
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float]]:
        """Simple keyword search for relevant documents"""
        if not self.documents:
            return []
            
        query_words = query.lower().split()
        results = []
        
        for doc in self.documents:
            doc_lower = doc.lower()
            score = sum(1 for word in query_words if word in doc_lower)
            if score > 0:
                results.append((doc, score / len(query_words)))
        
        # Sort by score and return top_k
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