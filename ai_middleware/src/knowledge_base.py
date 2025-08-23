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
            
        query_lower = query.lower()
        results = []
        
        for doc in self.documents:
            doc_lower = doc.lower()
            # Look for exact phrase matches first
            if query_lower in doc_lower:
                results.append((doc, 1.0))
            else:
                # Then keyword matches
                query_words = query_lower.split()
                important_words = [w for w in query_words if len(w) > 3]  # Skip short words
                if important_words:
                    score = sum(1 for word in important_words if word in doc_lower)
                    if score > 0:
                        results.append((doc, score / len(important_words)))
        
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