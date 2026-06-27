-- StudyMate AI - Rollback Database Migrations (Phase 2)
-- Created: 2026-06-27
-- Description: Cleanly drops all storage policies, RLS policies, indexes, triggers, functions, and tables.

-- =====================================================================
-- 1. DROP STORAGE OBJECTS POLICIES & DELETE BUCKETS
-- =====================================================================
DROP POLICY IF EXISTS "Allow public read access to profile pictures" ON storage.objects;
DROP POLICY IF EXISTS "Allow owners to upload profile pictures" ON storage.objects;
DROP POLICY IF EXISTS "Allow owners to update profile pictures" ON storage.objects;
DROP POLICY IF EXISTS "Allow owners to delete profile pictures" ON storage.objects;
DROP POLICY IF EXISTS "Allow owner select on private buckets" ON storage.objects;
DROP POLICY IF EXISTS "Allow owner insert on private buckets" ON storage.objects;
DROP POLICY IF EXISTS "Allow owner update on private buckets" ON storage.objects;
DROP POLICY IF EXISTS "Allow owner delete on private buckets" ON storage.objects;

DELETE FROM storage.buckets WHERE id IN ('user-uploads', 'extracted-images', 'profile-pictures', 'voice-recordings', 'exports', 'temporary-files');

-- =====================================================================
-- 2. DROP ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================================
-- users
DROP POLICY IF EXISTS select_users ON public.users;
DROP POLICY IF EXISTS insert_users ON public.users;
DROP POLICY IF EXISTS update_users ON public.users;
DROP POLICY IF EXISTS delete_users ON public.users;

-- user_preferences
DROP POLICY IF EXISTS select_user_preferences ON public.user_preferences;
DROP POLICY IF EXISTS insert_user_preferences ON public.user_preferences;
DROP POLICY IF EXISTS update_user_preferences ON public.user_preferences;
DROP POLICY IF EXISTS delete_user_preferences ON public.user_preferences;

-- audit_logs
DROP POLICY IF EXISTS select_audit_logs ON public.audit_logs;
DROP POLICY IF EXISTS insert_audit_logs ON public.audit_logs;
DROP POLICY IF EXISTS update_delete_audit_logs ON public.audit_logs;

-- subjects
DROP POLICY IF EXISTS select_subjects ON public.subjects;
DROP POLICY IF EXISTS insert_subjects ON public.subjects;
DROP POLICY IF EXISTS update_subjects ON public.subjects;
DROP POLICY IF EXISTS delete_subjects ON public.subjects;

-- uploaded_files
DROP POLICY IF EXISTS select_uploaded_files ON public.uploaded_files;
DROP POLICY IF EXISTS insert_uploaded_files ON public.uploaded_files;
DROP POLICY IF EXISTS update_uploaded_files ON public.uploaded_files;
DROP POLICY IF EXISTS delete_uploaded_files ON public.uploaded_files;

-- study_library
DROP POLICY IF EXISTS select_study_library ON public.study_library;
DROP POLICY IF EXISTS insert_study_library ON public.study_library;
DROP POLICY IF EXISTS update_study_library ON public.study_library;
DROP POLICY IF EXISTS delete_study_library ON public.study_library;

-- chat_sessions
DROP POLICY IF EXISTS select_chat_sessions ON public.chat_sessions;
DROP POLICY IF EXISTS insert_chat_sessions ON public.chat_sessions;
DROP POLICY IF EXISTS update_chat_sessions ON public.chat_sessions;
DROP POLICY IF EXISTS delete_chat_sessions ON public.chat_sessions;

-- chat_messages
DROP POLICY IF EXISTS select_chat_messages ON public.chat_messages;
DROP POLICY IF EXISTS insert_chat_messages ON public.chat_messages;
DROP POLICY IF EXISTS delete_chat_messages ON public.chat_messages;

-- ai_memory
DROP POLICY IF EXISTS select_ai_memory ON public.ai_memory;
DROP POLICY IF EXISTS insert_ai_memory ON public.ai_memory;
DROP POLICY IF EXISTS update_ai_memory ON public.ai_memory;
DROP POLICY IF EXISTS delete_ai_memory ON public.ai_memory;

-- flashcards
DROP POLICY IF EXISTS select_flashcards ON public.flashcards;
DROP POLICY IF EXISTS insert_flashcards ON public.flashcards;
DROP POLICY IF EXISTS update_flashcards ON public.flashcards;
DROP POLICY IF EXISTS delete_flashcards ON public.flashcards;

-- quizzes
DROP POLICY IF EXISTS select_quizzes ON public.quizzes;
DROP POLICY IF EXISTS insert_quizzes ON public.quizzes;
DROP POLICY IF EXISTS update_quizzes ON public.quizzes;
DROP POLICY IF EXISTS delete_quizzes ON public.quizzes;

-- revision_plans
DROP POLICY IF EXISTS select_revision_plans ON public.revision_plans;
DROP POLICY IF EXISTS insert_revision_plans ON public.revision_plans;
DROP POLICY IF EXISTS update_revision_plans ON public.revision_plans;
DROP POLICY IF EXISTS delete_revision_plans ON public.revision_plans;

-- user_api_keys
DROP POLICY IF EXISTS select_user_api_keys ON public.user_api_keys;
DROP POLICY IF EXISTS insert_user_api_keys ON public.user_api_keys;
DROP POLICY IF EXISTS update_user_api_keys ON public.user_api_keys;
DROP POLICY IF EXISTS delete_user_api_keys ON public.user_api_keys;

-- admin_settings
DROP POLICY IF EXISTS select_admin_settings ON public.admin_settings;
DROP POLICY IF EXISTS write_admin_settings ON public.admin_settings;

-- document_embeddings
DROP POLICY IF EXISTS select_document_embeddings ON public.document_embeddings;
DROP POLICY IF EXISTS write_document_embeddings ON public.document_embeddings;

-- remember_sessions
DROP POLICY IF EXISTS select_remember_sessions ON public.remember_sessions;
DROP POLICY IF EXISTS insert_remember_sessions ON public.remember_sessions;
DROP POLICY IF EXISTS update_remember_sessions ON public.remember_sessions;
DROP POLICY IF EXISTS delete_remember_sessions ON public.remember_sessions;


-- Disable RLS on tables
ALTER TABLE IF EXISTS public.remember_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.document_embeddings DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.admin_settings DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_api_keys DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.revision_plans DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.quizzes DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.flashcards DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.ai_memory DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.chat_messages DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.chat_sessions DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.study_library DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.uploaded_files DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.subjects DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.audit_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.user_preferences DISABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.users DISABLE ROW LEVEL SECURITY;

-- =====================================================================
-- 3. DROP INDEXES
-- =====================================================================
DROP INDEX IF EXISTS public.idx_remember_sessions_token_hash;
DROP INDEX IF EXISTS public.idx_remember_sessions_user_id;
DROP INDEX IF EXISTS public.idx_document_embeddings_vector;
DROP INDEX IF EXISTS public.idx_study_library_tags;
DROP INDEX IF EXISTS public.idx_subjects_deleted_at;
DROP INDEX IF EXISTS public.idx_users_deleted_at;
DROP INDEX IF EXISTS public.idx_document_embeddings_file_id;
DROP INDEX IF EXISTS public.idx_user_api_keys_owner_id;
DROP INDEX IF EXISTS public.idx_revision_plans_subject_id;
DROP INDEX IF EXISTS public.idx_revision_plans_owner_id;
DROP INDEX IF EXISTS public.idx_quizzes_subject_id;
DROP INDEX IF EXISTS public.idx_quizzes_owner_id;
DROP INDEX IF EXISTS public.idx_flashcards_subject_id;
DROP INDEX IF EXISTS public.idx_flashcards_owner_id;
DROP INDEX IF EXISTS public.idx_ai_memory_owner_id;
DROP INDEX IF EXISTS public.idx_chat_messages_session_id;
DROP INDEX IF EXISTS public.idx_chat_sessions_subject_id;
DROP INDEX IF EXISTS public.idx_chat_sessions_owner_id;
DROP INDEX IF EXISTS public.idx_study_library_file_id;
DROP INDEX IF EXISTS public.idx_study_library_subject_id;
DROP INDEX IF EXISTS public.idx_study_library_owner_id;
DROP INDEX IF EXISTS public.idx_uploaded_files_subject_id;
DROP INDEX IF EXISTS public.idx_uploaded_files_owner_id;
DROP INDEX IF EXISTS public.idx_subjects_owner_id;
DROP INDEX IF EXISTS public.idx_audit_logs_user_id;

-- =====================================================================
-- 4. DROP TRIGGERS
-- =====================================================================
DROP TRIGGER IF EXISTS set_users_updated_at ON public.users;
DROP TRIGGER IF EXISTS set_user_preferences_updated_at ON public.user_preferences;
DROP TRIGGER IF EXISTS set_subjects_updated_at ON public.subjects;
DROP TRIGGER IF EXISTS set_chat_sessions_updated_at ON public.chat_sessions;
DROP TRIGGER IF EXISTS set_ai_memory_updated_at ON public.ai_memory;
DROP TRIGGER IF EXISTS set_revision_plans_updated_at ON public.revision_plans;
DROP TRIGGER IF EXISTS set_user_api_keys_updated_at ON public.user_api_keys;
DROP TRIGGER IF EXISTS set_admin_settings_updated_at ON public.admin_settings;

-- =====================================================================
-- 5. DROP TABLES (Reverse Dependency Order)
-- =====================================================================
DROP TABLE IF EXISTS public.remember_sessions;
DROP TABLE IF EXISTS public.document_embeddings;
DROP TABLE IF EXISTS public.admin_settings;
DROP TABLE IF EXISTS public.user_api_keys;
DROP TABLE IF EXISTS public.revision_plans;
DROP TABLE IF EXISTS public.quizzes;
DROP TABLE IF EXISTS public.flashcards;
DROP TABLE IF EXISTS public.ai_memory;
DROP TABLE IF EXISTS public.chat_messages;
DROP TABLE IF EXISTS public.chat_sessions;
DROP TABLE IF EXISTS public.study_library;
DROP TABLE IF EXISTS public.uploaded_files;
DROP TABLE IF EXISTS public.subjects;
DROP TABLE IF EXISTS public.audit_logs;
DROP TABLE IF EXISTS public.user_preferences;
DROP TABLE IF EXISTS public.users;

-- =====================================================================
-- 6. DROP FUNCTIONS
-- =====================================================================
DROP FUNCTION IF EXISTS public.update_updated_at_column();
DROP FUNCTION IF EXISTS public.is_admin(UUID);

-- =====================================================================
-- 7. DROP EXTENSIONS (Optional - uncomment if desired)
-- =====================================================================
-- DROP EXTENSION IF EXISTS "vector";
-- DROP EXTENSION IF EXISTS "uuid-ossp";
