-- Create new table with proper vector column
CREATE TABLE knowledge_embeddings (
  id SERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  embedding vector(768) NOT NULL,  -- Gemini embeddings are 768 dimensions
  content_hash VARCHAR(32) UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for faster similarity search
CREATE INDEX ON knowledge_embeddings USING ivfflat (embedding vector_cosine_ops);
