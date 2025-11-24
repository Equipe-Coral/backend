-- Instalar extensão pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Adicionar coluna de embedding em demands
ALTER TABLE demands 
ADD COLUMN embedding vector(768);  -- Gemini usa 768 dimensões

-- Criar índice HNSW para busca vetorial rápida
CREATE INDEX idx_demands_embedding ON demands 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Índice adicional para filtrar por tema + busca vetorial
CREATE INDEX idx_demands_theme_status ON demands(theme, status);
