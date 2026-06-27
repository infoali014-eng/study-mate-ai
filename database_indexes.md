# Database Indexing Strategy & Specifications

This document outlines the indexing strategy implemented in the StudyMate AI Supabase architecture to ensure production-level query speeds and semantic search efficiency.

## Overview of Indexes

PostgreSQL automatically creates unique B-Tree indexes on all Primary Keys and Unique constraint combinations. In addition to these defaults, we have defined three specialized index types.

### 1. B-Tree Indexes on Foreign Keys (Query Optimization)

By default, PostgreSQL does not automatically index foreign keys. To prevent full-table scans during relational joins (`JOIN` queries), we have created B-Tree indexes on every foreign key column:

- `idx_audit_logs_user_id` on `public.audit_logs(user_id)`
- `idx_subjects_owner_id` on `public.subjects(owner_id)`
- `idx_uploaded_files_owner_id` on `public.uploaded_files(owner_id)`
- `idx_uploaded_files_subject_id` on `public.uploaded_files(subject_id)`
- `idx_study_library_owner_id` on `public.study_library(owner_id)`
- `idx_study_library_subject_id` on `public.study_library(subject_id)`
- `idx_study_library_file_id` on `public.study_library(uploaded_file_id)`
- `idx_chat_sessions_owner_id` on `public.chat_sessions(owner_id)`
- `idx_chat_sessions_subject_id` on `public.chat_sessions(subject_id)`
- `idx_chat_messages_session_id` on `public.chat_messages(session_id)`
- `idx_ai_memory_owner_id` on `public.ai_memory(owner_id)`
- `idx_flashcards_owner_id` on `public.flashcards(owner_id)`
- `idx_flashcards_subject_id` on `public.flashcards(subject_id)`
- `idx_quizzes_owner_id` on `public.quizzes(owner_id)`
- `idx_quizzes_subject_id` on `public.quizzes(subject_id)`
- `idx_revision_plans_owner_id` on `public.revision_plans(owner_id)`
- `idx_revision_plans_subject_id` on `public.revision_plans(subject_id)`
- `idx_user_api_keys_owner_id` on `public.user_api_keys(owner_id)`
- `idx_document_embeddings_file_id` on `public.document_embeddings(uploaded_file_id)`

### 2. Partial B-Tree Indexes for Soft Deletes

Since the application soft-deletes users and subjects by setting `deleted_at`, normal query operations will filter for active records using `WHERE deleted_at IS NULL`. We have defined partial B-Tree indexes to index only active records, drastically reducing index size and lookup times:

- `idx_users_deleted_at` on `public.users(deleted_at) WHERE deleted_at IS NULL`
- `idx_subjects_deleted_at` on `public.subjects(deleted_at) WHERE deleted_at IS NULL`

### 3. GIN (Generalized Inverted Index) on Arrays

The `study_library` table supports array-based tagging (`tags TEXT[]`). Traditional B-tree indexes cannot index array elements individually. We use a GIN index on the tags array to allow instantaneous lookups when filtering by tags (e.g., `WHERE tags @> ARRAY['exam-prep']`):

- `idx_study_library_tags` on `public.study_library USING GIN (tags)`

### 4. HNSW (Hierarchical Navigable Small World) on Vectors

For future semantic search capabilities, the `document_embeddings` table stores 1536-dimensional OpenAI embeddings in the `embedding_vector` column. 

To execute fast Approximate Nearest Neighbor (ANN) cosine similarity searches, we define a state-of-the-art HNSW index:

- `idx_document_embeddings_vector` on `public.document_embeddings USING hnsw (embedding_vector vector_cosine_ops)`

*Note: HNSW is highly performant compared to IVFFlat, maintaining high query recall even as the dataset scales.*
