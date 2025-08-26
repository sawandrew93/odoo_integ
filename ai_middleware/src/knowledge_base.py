from typing import List, Tuple
import os
import numpy as np
import google.generativeai as genai
from supabase import create_client, Client
import hashlib
import json

class KnowledgeBase:
    def __init__(self, api_key: str, supabase_url: str = None, supabase_key: str = None):
        self.documents = []
        self.embeddings = []
        genai.configure(api_key=api_key)
        
        # Initialize Supabase if credentials provided
        self.supabase = None
        if supabase_url and supabase_key:
            try:
                self.supabase: Client = create_client(supabase_url, supabase_key)
                self._ensure_table_exists()
            except Exception as e:
                print(f"Supabase connection failed: {e}")
        
    def add_documents(self, documents: List[str]):
        """Add documents to knowledge base with embeddings"""
        self.documents.extend(documents)
        for doc in documents:
            embedding = genai.embed_content(
                model="models/embedding-001",
                content=doc
            )["embedding"]
            self.embeddings.append(embedding)
    
    def search(self, query: str, top_k: int = 3) -> List[dict]:
        """Semantic search using embeddings"""
        if not self.documents:
            print(f"No documents loaded in knowledge base")
            return []
            
        try:
            query_embedding = genai.embed_content(
                model="models/embedding-001",
                content=query
            )["embedding"]
            
            similarities = []
            for i, doc_embedding in enumerate(self.embeddings):
                similarity = np.dot(query_embedding, doc_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                )
                similarities.append({'content': self.documents[i], 'score': similarity})
            
            similarities.sort(key=lambda x: x['score'], reverse=True)
            print(f"Found {len(similarities)} documents for query: {query}")
            return similarities[:top_k]
            
        except Exception as e:
            print(f"Embedding search error: {e}")
            # Fallback to keyword search
            return self._keyword_search(query, top_k)
    
    def _keyword_search(self, query: str, top_k: int = 3) -> List[dict]:
        """Fallback keyword search"""
        query_lower = query.lower()
        results = []
        
        for doc in self.documents:
            doc_lower = doc.lower()
            query_words = [w for w in query_lower.split() if len(w) > 2]
            if query_words:
                score = sum(1 for word in query_words if word in doc_lower)
                if score > 0:
                    results.append({'content': doc, 'score': score / len(query_words)})
        
        results.sort(key=lambda x: x['score'], reverse=True)
        print(f"Keyword search found {len(results)} results for: {query}")
        return results[:top_k]
    
    def _ensure_table_exists(self):
        """Create embeddings table if it doesn't exist"""
        try:
            # Check if table exists by trying to select from it
            self.supabase.table('knowledge_embeddings').select('id').limit(1).execute()
        except:
            # Table doesn't exist, but we can't create it via client
            print("Please create table 'knowledge_embeddings' in Supabase with columns: id, content, embedding, content_hash")
    
    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content to check if it's already embedded"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def load_from_directory(self, directory: str):
        """Load text files from directory with Supabase caching"""
        documents = []
        for filename in os.listdir(directory):
            if filename.endswith('.txt'):
                filepath = os.path.join(directory, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        sections = content.split('\n\n')
                        for section in sections:
                            if section.strip():
                                documents.append(section.strip())
        
        print(f"Found {len(documents)} documents from {directory}")
        
        if self.supabase:
            self._load_from_supabase(documents)
        else:
            # Fallback to in-memory embedding
            if documents:
                self.add_documents(documents)
    
    def _load_from_supabase(self, documents: List[str]):
        """Load embeddings from Supabase or create new ones"""
        for doc in documents:
            content_hash = self._get_content_hash(doc)
            
            # Check if embedding already exists
            try:
                result = self.supabase.table('knowledge_embeddings').select('*').eq('content_hash', content_hash).execute()
                
                if result.data:
                    # Use existing embedding
                    row = result.data[0]
                    self.documents.append(row['content'])
                    self.embeddings.append(json.loads(row['embedding']))
                    print(f"Loaded cached embedding for: {doc[:50]}...")
                else:
                    # Create new embedding
                    embedding = genai.embed_content(
                        model="models/embedding-001",
                        content=doc
                    )["embedding"]
                    
                    # Store in Supabase
                    self.supabase.table('knowledge_embeddings').insert({
                        'content': doc,
                        'embedding': json.dumps(embedding),
                        'content_hash': content_hash
                    }).execute()
                    
                    self.documents.append(doc)
                    self.embeddings.append(embedding)
                    print(f"Created new embedding for: {doc[:50]}...")
                    
            except Exception as e:
                print(f"Supabase error for doc, falling back to memory: {e}")
                # Fallback to in-memory
                embedding = genai.embed_content(
                    model="models/embedding-001",
                    content=doc
                )["embedding"]
                self.documents.append(doc)
                self.embeddings.append(embedding)