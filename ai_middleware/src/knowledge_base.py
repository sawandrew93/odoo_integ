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
        
        # Initialize Supabase - required for operation
        self.supabase = None
        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials required. Please set SUPABASE_URL and SUPABASE_KEY in .env")
        
        try:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            self._ensure_table_exists()
            print(f"✅ Supabase connected successfully")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {e}")
        
    def add_documents(self, documents: List[str]):
        """Add documents to knowledge base with embeddings via Supabase"""
        if not self.supabase:
            raise ConnectionError("Supabase not connected. Cannot add documents.")
        
        print(f"Processing {len(documents)} documents for embedding...")
        
        for i, doc in enumerate(documents):
            print(f"Processing document {i+1}/{len(documents)}: {len(doc)} chars")
            content_hash = self._get_content_hash(doc)
            
            # Check if already exists
            result = self.supabase.table('knowledge_embeddings').select('*').eq('content_hash', content_hash).execute()
            
            if not result.data:
                try:
                    # Create new embedding using Gemini's recommended approach
                    response = genai.embed_content(
                        model="models/embedding-001",
                        content=doc,
                        task_type="retrieval_document",
                        title="Knowledge Base Document"
                    )
                    embedding = response["embedding"]
                    
                    print(f"Generated embedding with {len(embedding)} dimensions")
                    
                    # Store in Supabase
                    insert_result = self.supabase.table('knowledge_embeddings').insert({
                        'content': doc,
                        'embedding': embedding,
                        'content_hash': content_hash
                    }).execute()
                    
                    if insert_result.data:
                        # Add to local cache
                        self.documents.append(doc)
                        self.embeddings.append(embedding)
                        print(f"✅ Added document {i+1}: {doc[:100]}...")
                    else:
                        print(f"❌ Failed to insert document {i+1}")
                        
                except Exception as e:
                    print(f"❌ Error processing document {i+1}: {e}")
                    continue
            else:
                print(f"⏭️ Document {i+1} already exists, skipping")
    
    def search(self, query: str, top_k: int = 3) -> List[dict]:
        """Semantic search using embeddings with Gemini's recommended approach"""
        if not self.supabase:
            print(f"❌ Supabase not connected. Cannot search knowledge base.")
            return []
            
        # Load all documents from Supabase for search
        try:
            all_docs = self.supabase.table('knowledge_embeddings').select('*').execute()
            if not all_docs.data:
                print(f"No documents in knowledge base")
                return []
            
            print(f"Searching through {len(all_docs.data)} documents for: {query}")
            
            # Generate query embedding
            query_response = genai.embed_content(
                model="models/embedding-001",
                content=query,
                task_type="retrieval_query"
            )
            query_embedding = query_response["embedding"]
            
            similarities = []
            for doc in all_docs.data:
                doc_embedding = doc['embedding']
                
                # Handle both array and JSON string formats
                if isinstance(doc_embedding, str):
                    doc_embedding = json.loads(doc_embedding)
                
                # Calculate cosine similarity
                similarity = np.dot(query_embedding, doc_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                )
                
                similarities.append({
                    'content': doc['content'], 
                    'score': similarity,
                    'id': doc['id']
                })
            
            # Sort by similarity score
            similarities.sort(key=lambda x: x['score'], reverse=True)
            
            # Log top results
            print(f"Top {min(top_k, len(similarities))} results:")
            for i, result in enumerate(similarities[:top_k]):
                print(f"  {i+1}. Score: {result['score']:.3f} - {result['content'][:100]}...")
            
            return similarities[:top_k]
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    

    
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
        if not self.supabase:
            print(f"❌ Supabase not connected. Cannot load knowledge base.")
            return
            
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
        self._load_from_supabase(documents)
    
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
                    # Handle both array and JSON string formats
                    embedding = row['embedding']
                    if isinstance(embedding, str):
                        embedding = json.loads(embedding)
                    self.embeddings.append(embedding)
                    print(f"✅ Loaded cached embedding for: {doc[:50]}...")
                else:
                    # Create new embedding
                    embedding = genai.embed_content(
                        model="models/embedding-001",
                        content=doc
                    )["embedding"]
                    
                    # Store in Supabase
                    self.supabase.table('knowledge_embeddings').insert({
                        'content': doc,
                        'embedding': embedding,  # Store as array
                        'content_hash': content_hash
                    }).execute()
                    
                    self.documents.append(doc)
                    self.embeddings.append(embedding)
                    print(f"✅ Created new embedding for: {doc[:50]}...")
                    
            except Exception as e:
                print(f"Supabase error for document: {e}")
                raise