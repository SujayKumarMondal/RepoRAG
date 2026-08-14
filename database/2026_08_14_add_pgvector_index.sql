-- Add pgvector extension and IVFFLAT index for embeddings.vector

-- Enable vector extension (requires superuser)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create an IVFFLAT index on the embeddings.vector column for KNN search.
-- Adjust the 'lists' parameter for your data size; higher lists -> faster search but more memory.
CREATE INDEX IF NOT EXISTS embeddings_vector_ivfflat_idx ON embeddings USING ivfflat (vector) WITH (lists = 100);

-- Analyze to update planner statistics
VACUUM ANALYZE embeddings;
