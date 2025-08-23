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
        
        # Split documents into individual Q&A pairs
        qa_pairs = []
        for doc in self.documents:
            lines = doc.strip().split('\n')
            for i in range(0, len(lines)-1, 2):
                if i+1 < len(lines) and lines[i].startswith('Q:'):
                    qa_pair = f"{lines[i]}\n{lines[i+1]}"
                    qa_pairs.append(qa_pair)
        
        # Search in Q&A pairs
        for qa in qa_pairs:
            qa_lower = qa.lower()
            # Look for keyword matches in questions
            query_words = [w for w in query_lower.split() if len(w) > 2]
            if query_words:
                score = sum(1 for word in query_words if word in qa_lower)
                if score > 0:
                    results.append((qa, score / len(query_words)))
        
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