import time
import tiktoken
import google.generativeai as genai
from typing import List, Dict, Any

class EmbeddingService:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.embedding_model = genai.GenerativeModel('embedding-001')
        
        # Free-tier limits
        self.MAX_TOKENS_PER_MIN = 5_000_000
        self.batch_size = 5
        
        # Track token usage
        self.tokens_used = []
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except:
            self.tokenizer = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Fallback: rough estimate
            return len(text.split()) * 1.3
    
    def record_tokens(self, tokens: int):
        """Record token usage and prune older entries"""
        now = time.time() * 1000  # milliseconds
        self.tokens_used.append({"tokens": tokens, "time": now})
        
        # Keep only last 60 seconds
        self.tokens_used = [entry for entry in self.tokens_used if now - entry["time"] < 60_000]
    
    def get_tokens_last_minute(self) -> int:
        """Calculate tokens used in the last minute"""
        return sum(entry["tokens"] for entry in self.tokens_used)
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with rate limiting"""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Clean and prepare
        clean_text = text.strip()
        token_count = self.count_tokens(clean_text)
        
        # Rate limiting: wait if this would exceed quota
        while self.get_tokens_last_minute() + token_count > self.MAX_TOKENS_PER_MIN:
            print("⏳ Waiting for token budget to reset...")
            time.sleep(1)
        
        try:
            result = genai.embed_content(
                model="models/embedding-001",
                content=clean_text,
                task_type="retrieval_document"
            )
            embedding = result["embedding"]
            
            if not embedding or len(embedding) == 0:
                raise ValueError("Failed to generate embedding")
            
            self.record_tokens(token_count)
            return embedding
            
        except Exception as error:
            print(f"❌ Error generating embedding: {error}")
            raise error
    
    async def generate_batch_embeddings(self, documents: List[Dict[str, str]], progress_callback=None) -> Dict[str, Any]:
        """Generate embeddings for batch of documents with progress tracking"""
        results = []
        successful = 0
        failed = 0
        
        total_batches = (len(documents) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            if progress_callback:
                progress_callback(f"📦 Processing batch {batch_num}/{total_batches}")
            
            for j, doc_obj in enumerate(batch):
                doc_index = i + j + 1
                content = doc_obj['content']
                filename = doc_obj['filename']
                
                try:
                    if progress_callback:
                        progress_callback(f"🔄 Embedding chunk {doc_index}/{len(documents)} from {filename}")
                    
                    embedding = await self.generate_embedding(content)
                    results.append({
                        "success": True,
                        "embedding": embedding,
                        "content": content,
                        "filename": filename,
                        "original_index": doc_index - 1
                    })
                    successful += 1
                    
                    if progress_callback:
                        progress_callback(f"✅ Chunk {doc_index} embedded successfully")
                        
                except Exception as error:
                    results.append({
                        "success": False,
                        "error": str(error),
                        "content": content,
                        "filename": filename,
                        "original_index": doc_index - 1
                    })
                    failed += 1
                    
                    if progress_callback:
                        progress_callback(f"❌ Chunk {doc_index} failed: {str(error)}")
            
            # Delay between batches
            if i + self.batch_size < len(documents):
                if progress_callback:
                    progress_callback("⏳ Waiting 10 seconds before next batch...")
                time.sleep(10)
        
        return {
            "results": results,
            "successful": successful,
            "failed": failed,
            "total": len(documents)
        }