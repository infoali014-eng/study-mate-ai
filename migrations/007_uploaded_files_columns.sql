-- Migration: 007_Uploaded_Files_Columns
-- Created: 2026-06-28
-- Description: Expand uploaded_files and document_embeddings schema for Phase 4B metadata, lifecycle tracking, and pgvector match RPC.

-- 1. Alter uploaded_files metadata and status tracking columns
ALTER TABLE public.uploaded_files
ADD COLUMN IF NOT EXISTS page_count INT,
ADD COLUMN IF NOT EXISTS language TEXT,
ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'UPLOADED',
ADD COLUMN IF NOT EXISTS processing_duration NUMERIC,
ADD COLUMN IF NOT EXISTS ocr_used BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS embedding_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS text_length INT,
ADD COLUMN IF NOT EXISTS chunk_count INT,
ADD COLUMN IF NOT EXISTS processing_version TEXT DEFAULT '1.0',
ADD COLUMN IF NOT EXISTS embedding_model TEXT DEFAULT 'hash_384',
ADD COLUMN IF NOT EXISTS embedding_dimension INT DEFAULT 384,
ADD COLUMN IF NOT EXISTS ocr_engine TEXT DEFAULT 'pytesseract',
ADD COLUMN IF NOT EXISTS parser_version TEXT DEFAULT '1.0';

-- 2. Alter document_embeddings to support user isolation and page numbers
ALTER TABLE public.document_embeddings
ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS page_number INT;

-- 3. Adjust embedding_vector to match the 384 dimensions used by local hash embeddings
-- Drop old column and recreate with vector(384) dimension
ALTER TABLE public.document_embeddings DROP COLUMN IF EXISTS embedding_vector;
ALTER TABLE public.document_embeddings ADD COLUMN embedding_vector vector(384) NOT NULL;

-- 4. Create similarity search function for pgvector queries
CREATE OR REPLACE FUNCTION public.match_document_embeddings(
    query_embedding vector(384),
    match_limit INT,
    filter_subject_id UUID DEFAULT NULL,
    filter_user_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    uploaded_file_id UUID,
    chunk_index INT,
    text_chunk TEXT,
    page_number INT,
    similarity NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        de.id,
        de.uploaded_file_id,
        de.chunk_index,
        de.text_chunk,
        de.page_number,
        (1 - (de.embedding_vector <=> query_embedding))::numeric AS similarity
    FROM public.document_embeddings de
    JOIN public.uploaded_files uf ON de.uploaded_file_id = uf.id
    WHERE (filter_subject_id IS NULL OR uf.subject_id = filter_subject_id)
      AND (filter_user_id IS NULL OR uf.owner_id = filter_user_id)
    ORDER BY de.embedding_vector <=> query_embedding
    LIMIT match_limit;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
