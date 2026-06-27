-- StudyMate AI - Consolidated Supabase Schema Definition (Phase 2)
-- Generated: 2026-06-27
-- Database Backend: PostgreSQL / Supabase

-- =====================================================================
-- 1. EXTENSIONS
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =====================================================================
-- 2. CORE TABLES DEFINITIONS
-- =====================================================================

-- 2.1 users table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    profile_picture TEXT,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

-- 2.2 user_preferences table
CREATE TABLE IF NOT EXISTS public.user_preferences (
    id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    theme TEXT NOT NULL DEFAULT 'light',
    language TEXT NOT NULL DEFAULT 'en',
    sidebar_state TEXT NOT NULL DEFAULT 'expanded',
    default_ai_provider TEXT NOT NULL DEFAULT 'Gemini',
    default_model TEXT NOT NULL DEFAULT 'gemini-2.0-flash',
    teach_me_level TEXT NOT NULL DEFAULT 'Normal',
    voice_enabled BOOLEAN NOT NULL DEFAULT false,
    notifications BOOLEAN NOT NULL DEFAULT true,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.3 audit_logs table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    resource_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.4 subjects table
CREATE TABLE IF NOT EXISTS public.subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subject_name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#14b8b4',
    icon TEXT DEFAULT '📚',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ
);

-- 2.5 uploaded_files table
CREATE TABLE IF NOT EXISTS public.uploaded_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size BIGINT NOT NULL,
    storage_provider TEXT NOT NULL DEFAULT 'supabase',
    storage_path TEXT NOT NULL,
    checksum TEXT,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed BOOLEAN NOT NULL DEFAULT false,
    extracted_text_available BOOLEAN NOT NULL DEFAULT false
);

-- 2.6 study_library table
CREATE TABLE IF NOT EXISTS public.study_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    uploaded_file_id UUID REFERENCES public.uploaded_files(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.7 chat_sessions table
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'Study Chat',
    chat_mode TEXT NOT NULL DEFAULT 'General Chat',
    subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
    model TEXT NOT NULL DEFAULT 'gemini-2.0-flash',
    provider TEXT NOT NULL DEFAULT 'Gemini',
    temperature NUMERIC(3, 2) NOT NULL DEFAULT 0.70 CHECK (temperature >= 0.00 AND temperature <= 2.00),
    system_prompt_version TEXT NOT NULL DEFAULT '1.0',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.8 chat_messages table
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    message TEXT NOT NULL,
    attachments JSONB NOT NULL DEFAULT '[]'::jsonb,
    token_count INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.9 ai_memory table
CREATE TABLE IF NOT EXISTS public.ai_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    memory_key TEXT NOT NULL,
    memory_value TEXT NOT NULL,
    importance INT NOT NULL DEFAULT 1 CHECK (importance >= 1 AND importance <= 10),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT unique_user_memory_key UNIQUE (owner_id, memory_key)
);

-- 2.10 flashcards table
CREATE TABLE IF NOT EXISTS public.flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    difficulty TEXT NOT NULL DEFAULT 'medium' CHECK (difficulty IN ('easy', 'medium', 'hard')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.11 quizzes table
CREATE TABLE IF NOT EXISTS public.quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    score INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.12 revision_plans table
CREATE TABLE IF NOT EXISTS public.revision_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    schedule JSONB NOT NULL DEFAULT '{}'::jsonb,
    progress INT NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.13 user_api_keys table
CREATE TABLE IF NOT EXISTS public.user_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    encrypted_api_key TEXT NOT NULL,
    default_model TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT unique_user_provider_key UNIQUE (owner_id, provider)
);

-- 2.14 admin_settings table
CREATE TABLE IF NOT EXISTS public.admin_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_name TEXT UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2.15 document_embeddings table
CREATE TABLE IF NOT EXISTS public.document_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uploaded_file_id UUID NOT NULL REFERENCES public.uploaded_files(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    text_chunk TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    embedding_vector vector(1536) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- 3. FUNCTIONS & TRIGGERS DEFINITIONS
-- =====================================================================

-- 3.1 is_admin helper function
CREATE OR REPLACE FUNCTION public.is_admin(user_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    is_admin_user BOOLEAN;
BEGIN
    SELECT is_admin INTO is_admin_user
    FROM public.users
    WHERE id = user_id AND deleted_at IS NULL;
    
    RETURN COALESCE(is_admin_user, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 3.2 update_updated_at helper function
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3.3 Triggers Assignment
CREATE TRIGGER set_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER set_user_preferences_updated_at BEFORE UPDATE ON public.user_preferences FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER set_subjects_updated_at BEFORE UPDATE ON public.subjects FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER set_chat_sessions_updated_at BEFORE UPDATE ON public.chat_sessions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER set_ai_memory_updated_at BEFORE UPDATE ON public.ai_memory FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER set_revision_plans_updated_at BEFORE UPDATE ON public.revision_plans FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER set_user_api_keys_updated_at BEFORE UPDATE ON public.user_api_keys FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
CREATE TRIGGER set_admin_settings_updated_at BEFORE UPDATE ON public.admin_settings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =====================================================================
-- 4. DATABASE INDEXES DEFINITIONS
-- =====================================================================
-- Foreign Keys
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON public.audit_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_subjects_owner_id ON public.subjects (owner_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_owner_id ON public.uploaded_files (owner_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_subject_id ON public.uploaded_files (subject_id);
CREATE INDEX IF NOT EXISTS idx_study_library_owner_id ON public.study_library (owner_id);
CREATE INDEX IF NOT EXISTS idx_study_library_subject_id ON public.study_library (subject_id);
CREATE INDEX IF NOT EXISTS idx_study_library_file_id ON public.study_library (uploaded_file_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_owner_id ON public.chat_sessions (owner_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_subject_id ON public.chat_sessions (subject_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON public.chat_messages (session_id);
CREATE INDEX IF NOT EXISTS idx_ai_memory_owner_id ON public.ai_memory (owner_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_owner_id ON public.flashcards (owner_id);
CREATE INDEX IF NOT EXISTS idx_flashcards_subject_id ON public.flashcards (subject_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_owner_id ON public.quizzes (owner_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_subject_id ON public.quizzes (subject_id);
CREATE INDEX IF NOT EXISTS idx_revision_plans_owner_id ON public.revision_plans (owner_id);
CREATE INDEX IF NOT EXISTS idx_revision_plans_subject_id ON public.revision_plans (subject_id);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_owner_id ON public.user_api_keys (owner_id);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_file_id ON public.document_embeddings (uploaded_file_id);

-- Soft Deletes
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON public.users (deleted_at) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_subjects_deleted_at ON public.subjects (deleted_at) WHERE deleted_at IS NULL;

-- Advanced Indexes
CREATE INDEX IF NOT EXISTS idx_study_library_tags ON public.study_library USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector ON public.document_embeddings USING hnsw (embedding_vector vector_cosine_ops);

-- =====================================================================
-- 5. ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================================
-- users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_users ON public.users FOR SELECT TO authenticated USING (id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_users ON public.users FOR INSERT TO authenticated, anon WITH CHECK (true);
CREATE POLICY update_users ON public.users FOR UPDATE TO authenticated USING (id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_users ON public.users FOR DELETE TO authenticated USING (public.is_admin(auth.uid()));

-- user_preferences
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_user_preferences ON public.user_preferences FOR SELECT TO authenticated USING (id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_user_preferences ON public.user_preferences FOR INSERT TO authenticated WITH CHECK (id = auth.uid());
CREATE POLICY update_user_preferences ON public.user_preferences FOR UPDATE TO authenticated USING (id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_user_preferences ON public.user_preferences FOR DELETE TO authenticated USING (id = auth.uid() OR public.is_admin(auth.uid()));

-- audit_logs
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_audit_logs ON public.audit_logs FOR SELECT TO authenticated USING (user_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_audit_logs ON public.audit_logs FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY update_delete_audit_logs ON public.audit_logs FOR ALL TO authenticated USING (public.is_admin(auth.uid()));

-- subjects
ALTER TABLE public.subjects ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_subjects ON public.subjects FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_subjects ON public.subjects FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_subjects ON public.subjects FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_subjects ON public.subjects FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- uploaded_files
ALTER TABLE public.uploaded_files ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_uploaded_files ON public.uploaded_files FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_uploaded_files ON public.uploaded_files FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_uploaded_files ON public.uploaded_files FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_uploaded_files ON public.uploaded_files FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- study_library
ALTER TABLE public.study_library ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_study_library ON public.study_library FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_study_library ON public.study_library FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_study_library ON public.study_library FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_study_library ON public.study_library FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- chat_sessions
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_chat_sessions ON public.chat_sessions FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_chat_sessions ON public.chat_sessions FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_chat_sessions ON public.chat_sessions FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_chat_sessions ON public.chat_sessions FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- chat_messages
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_chat_messages ON public.chat_messages FOR SELECT TO authenticated USING (EXISTS (SELECT 1 FROM public.chat_sessions s WHERE s.id = session_id AND (s.owner_id = auth.uid() OR public.is_admin(auth.uid()))));
CREATE POLICY insert_chat_messages ON public.chat_messages FOR INSERT TO authenticated WITH CHECK (EXISTS (SELECT 1 FROM public.chat_sessions s WHERE s.id = session_id AND s.owner_id = auth.uid()));
CREATE POLICY delete_chat_messages ON public.chat_messages FOR DELETE TO authenticated USING (EXISTS (SELECT 1 FROM public.chat_sessions s WHERE s.id = session_id AND (s.owner_id = auth.uid() OR public.is_admin(auth.uid()))));

-- ai_memory
ALTER TABLE public.ai_memory ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_ai_memory ON public.ai_memory FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_ai_memory ON public.ai_memory FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_ai_memory ON public.ai_memory FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_ai_memory ON public.ai_memory FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- flashcards
ALTER TABLE public.flashcards ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_flashcards ON public.flashcards FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_flashcards ON public.flashcards FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_flashcards ON public.flashcards FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_flashcards ON public.flashcards FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- quizzes
ALTER TABLE public.quizzes ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_quizzes ON public.quizzes FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_quizzes ON public.quizzes FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_quizzes ON public.quizzes FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_quizzes ON public.quizzes FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- revision_plans
ALTER TABLE public.revision_plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_revision_plans ON public.revision_plans FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_revision_plans ON public.revision_plans FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_revision_plans ON public.revision_plans FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_revision_plans ON public.revision_plans FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- user_api_keys
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_user_api_keys ON public.user_api_keys FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_user_api_keys ON public.user_api_keys FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_user_api_keys ON public.user_api_keys FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_user_api_keys ON public.user_api_keys FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- admin_settings
ALTER TABLE public.admin_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_admin_settings ON public.admin_settings FOR SELECT TO authenticated USING (true);
CREATE POLICY write_admin_settings ON public.admin_settings FOR ALL TO authenticated USING (public.is_admin(auth.uid())) WITH CHECK (public.is_admin(auth.uid()));

-- document_embeddings
ALTER TABLE public.document_embeddings ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_document_embeddings ON public.document_embeddings FOR SELECT TO authenticated USING (EXISTS (SELECT 1 FROM public.uploaded_files f WHERE f.id = uploaded_file_id AND (f.owner_id = auth.uid() OR public.is_admin(auth.uid()))));
CREATE POLICY write_document_embeddings ON public.document_embeddings FOR ALL TO authenticated USING (EXISTS (SELECT 1 FROM public.uploaded_files f WHERE f.id = uploaded_file_id AND (f.owner_id = auth.uid() OR public.is_admin(auth.uid()))));

-- =====================================================================
-- 6. STORAGE BUCKETS & STORAGE POLICIES DEFINITIONS
-- =====================================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    ('user-uploads', 'user-uploads', false, 104857600, ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'text/plain', 'text/markdown', 'text/csv', 'application/json', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']),
    ('extracted-images', 'extracted-images', false, 10485760, ARRAY['image/png', 'image/jpeg', 'image/webp']),
    ('profile-pictures', 'profile-pictures', true, 5242880, ARRAY['image/png', 'image/jpeg', 'image/webp']),
    ('voice-recordings', 'voice-recordings', false, 52428800, ARRAY['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm']),
    ('exports', 'exports', false, 20971520, ARRAY['application/pdf', 'text/markdown', 'application/json', 'text/csv']),
    ('temporary-files', 'temporary-files', false, 104857600, NULL)
ON CONFLICT (id) DO UPDATE 
SET public = EXCLUDED.public, file_size_limit = EXCLUDED.file_size_limit, allowed_mime_types = EXCLUDED.allowed_mime_types;

-- profile-pictures policies
CREATE POLICY "Allow public read access to profile pictures" ON storage.objects FOR SELECT USING (bucket_id = 'profile-pictures');
CREATE POLICY "Allow owners to upload profile pictures" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'profile-pictures' AND (storage.foldername(name))[1] = auth.uid()::text);
CREATE POLICY "Allow owners to update profile pictures" ON storage.objects FOR UPDATE USING (bucket_id = 'profile-pictures' AND (storage.foldername(name))[1] = auth.uid()::text);
CREATE POLICY "Allow owners to delete profile pictures" ON storage.objects FOR DELETE USING (bucket_id = 'profile-pictures' AND (storage.foldername(name))[1] = auth.uid()::text);

-- private buckets policies
CREATE POLICY "Allow owner select on private buckets" ON storage.objects FOR SELECT TO authenticated USING (bucket_id IN ('user-uploads', 'extracted-images', 'voice-recordings', 'exports', 'temporary-files') AND ((storage.foldername(name))[1] = auth.uid()::text OR public.is_admin(auth.uid())));
CREATE POLICY "Allow owner insert on private buckets" ON storage.objects FOR INSERT TO authenticated WITH CHECK (bucket_id IN ('user-uploads', 'extracted-images', 'voice-recordings', 'exports', 'temporary-files') AND (storage.foldername(name))[1] = auth.uid()::text);
CREATE POLICY "Allow owner update on private buckets" ON storage.objects FOR UPDATE TO authenticated USING (bucket_id IN ('user-uploads', 'extracted-images', 'voice-recordings', 'exports', 'temporary-files') AND (storage.foldername(name))[1] = auth.uid()::text);
CREATE POLICY "Allow owner delete on private buckets" ON storage.objects FOR DELETE TO authenticated USING (bucket_id IN ('user-uploads', 'extracted-images', 'voice-recordings', 'exports', 'temporary-files') AND ((storage.foldername(name))[1] = auth.uid()::text OR public.is_admin(auth.uid())));

-- =====================================================================
-- 7. REMEMBER SESSIONS SCHEMA, INDEXES, AND RLS POLICIES
-- =====================================================================
CREATE TABLE IF NOT EXISTS public.remember_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.remember_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_remember_sessions ON public.remember_sessions FOR SELECT TO authenticated USING (user_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_remember_sessions ON public.remember_sessions FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY update_remember_sessions ON public.remember_sessions FOR UPDATE TO authenticated USING (user_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (user_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_remember_sessions ON public.remember_sessions FOR DELETE TO authenticated USING (user_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE INDEX IF NOT EXISTS idx_remember_sessions_user_id ON public.remember_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_remember_sessions_token_hash ON public.remember_sessions (token_hash);
