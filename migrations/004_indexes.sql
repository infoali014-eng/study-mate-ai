-- Migration: 004_Indexes
-- Created: 2026-06-27
-- Description: Create indexes on foreign keys, soft-delete columns, and vector embeddings.

-- =====================================================================
-- 1. FOREIGN KEY INDEXES (B-Tree)
-- =====================================================================
-- audit_logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON public.audit_logs (user_id);

-- subjects
CREATE INDEX IF NOT EXISTS idx_subjects_owner_id ON public.subjects (owner_id);

-- uploaded_files
CREATE INDEX IF NOT EXISTS idx_uploaded_files_owner_id ON public.uploaded_files (owner_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_subject_id ON public.uploaded_files (subject_id);

-- study_library
CREATE INDEX IF NOT EXISTS idx_study_library_owner_id ON public.study_library (owner_id);
CREATE INDEX IF NOT EXISTS idx_study_library_subject_id ON public.study_library (subject_id);
CREATE INDEX IF NOT EXISTS idx_study_library_file_id ON public.study_library (uploaded_file_id);

-- chat_sessions
CREATE INDEX IF NOT EXISTS idx_chat_sessions_owner_id ON public.chat_sessions (owner_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_subject_id ON public.chat_sessions (subject_id);

-- chat_messages
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON public.chat_messages (session_id);

-- ai_memory
CREATE INDEX IF NOT EXISTS idx_ai_memory_owner_id ON public.ai_memory (owner_id);

-- flashcards
CREATE INDEX IF NOT EXISTS idx_flashcards_owner_id ON public.flashcards (owner_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_subject_id ON public.flashcards (subject_id);

-- quizzes
CREATE INDEX IF NOT EXISTS idx_quizzes_owner_id ON public.quizzes (owner_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_subject_id ON public.quizzes (subject_id);

-- revision_plans
CREATE INDEX IF NOT EXISTS idx_revision_plans_owner_id ON public.revision_plans (owner_id);
CREATE INDEX IF NOT EXISTS idx_revision_plans_subject_id ON public.revision_plans (subject_id);

-- user_api_keys
CREATE INDEX IF NOT EXISTS idx_user_api_keys_owner_id ON public.user_api_keys (owner_id);

-- document_embeddings
CREATE INDEX IF NOT EXISTS idx_document_embeddings_file_id ON public.document_embeddings (uploaded_file_id);

-- =====================================================================
-- 2. SOFT DELETE INDEXES (Partial B-Tree)
-- =====================================================================
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON public.users (deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_subjects_deleted_at ON public.subjects (deleted_at) WHERE deleted_at IS NULL;

-- =====================================================================
-- 3. ADVANCED SPECIALIZED INDEXES
-- =====================================================================
-- GIN index for study_library tag array search queries
CREATE INDEX IF NOT EXISTS idx_study_library_tags ON public.study_library USING GIN (tags);

-- HNSW index for pgvector cosine similarity searches
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector ON public.document_embeddings USING hnsw (embedding_vector vector_cosine_ops);
