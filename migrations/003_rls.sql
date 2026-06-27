-- Migration: 003_RLS
-- Created: 2026-06-27
-- Description: Enable Row Level Security (RLS) on all tables and create secure policies.

-- =====================================================================
-- 1. USERS TABLE
-- =====================================================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_users ON public.users
    FOR SELECT TO authenticated
    USING (id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_users ON public.users
    FOR INSERT TO authenticated, anon
    WITH CHECK (true);

CREATE POLICY update_users ON public.users
    FOR UPDATE TO authenticated
    USING (id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_users ON public.users
    FOR DELETE TO authenticated
    USING (public.is_admin(auth.uid()));

-- =====================================================================
-- 2. USER PREFERENCES TABLE
-- =====================================================================
ALTER TABLE public.user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_user_preferences ON public.user_preferences
    FOR SELECT TO authenticated
    USING (id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_user_preferences ON public.user_preferences
    FOR INSERT TO authenticated
    WITH CHECK (id = auth.uid());

CREATE POLICY update_user_preferences ON public.user_preferences
    FOR UPDATE TO authenticated
    USING (id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_user_preferences ON public.user_preferences
    FOR DELETE TO authenticated
    USING (id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 3. AUDIT LOGS TABLE
-- =====================================================================
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_audit_logs ON public.audit_logs
    FOR SELECT TO authenticated
    USING (user_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_audit_logs ON public.audit_logs
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

-- Audit logs should never be updated or deleted by normal operations
CREATE POLICY update_delete_audit_logs ON public.audit_logs
    FOR ALL TO authenticated
    USING (public.is_admin(auth.uid()));

-- =====================================================================
-- 4. SUBJECTS TABLE
-- =====================================================================
ALTER TABLE public.subjects ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_subjects ON public.subjects
    FOR SELECT TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_subjects ON public.subjects
    FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY update_subjects ON public.subjects
    FOR UPDATE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_subjects ON public.subjects
    FOR DELETE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 5. UPLOADED FILES TABLE
-- =====================================================================
ALTER TABLE public.uploaded_files ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_uploaded_files ON public.uploaded_files
    FOR SELECT TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_uploaded_files ON public.uploaded_files
    FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY update_uploaded_files ON public.uploaded_files
    FOR UPDATE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_uploaded_files ON public.uploaded_files
    FOR DELETE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 6. STUDY LIBRARY TABLE
-- =====================================================================
ALTER TABLE public.study_library ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_study_library ON public.study_library
    FOR SELECT TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_study_library ON public.study_library
    FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY update_study_library ON public.study_library
    FOR UPDATE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_study_library ON public.study_library
    FOR DELETE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 7. CHAT SESSIONS TABLE
-- =====================================================================
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_chat_sessions ON public.chat_sessions
    FOR SELECT TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_chat_sessions ON public.chat_sessions
    FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY update_chat_sessions ON public.chat_sessions
    FOR UPDATE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_chat_sessions ON public.chat_sessions
    FOR DELETE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 8. CHAT MESSAGES TABLE (Relational Check via Chat Sessions)
-- =====================================================================
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_chat_messages ON public.chat_messages
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.chat_sessions s
            WHERE s.id = session_id AND (s.owner_id = auth.uid() OR public.is_admin(auth.uid()))
        )
    );

CREATE POLICY insert_chat_messages ON public.chat_messages
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.chat_sessions s
            WHERE s.id = session_id AND s.owner_id = auth.uid()
        )
    );

CREATE POLICY delete_chat_messages ON public.chat_messages
    FOR DELETE TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.chat_sessions s
            WHERE s.id = session_id AND (s.owner_id = auth.uid() OR public.is_admin(auth.uid()))
        )
    );

-- =====================================================================
-- 9. AI MEMORY TABLE
-- =====================================================================
ALTER TABLE public.ai_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_ai_memory ON public.ai_memory
    FOR SELECT TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_ai_memory ON public.ai_memory
    FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY update_ai_memory ON public.ai_memory
    FOR UPDATE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_ai_memory ON public.ai_memory
    FOR DELETE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 10. FLASHCARDS TABLE
-- =====================================================================
ALTER TABLE public.flashcards ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_flashcards ON public.flashcards
    FOR SELECT TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_flashcards ON public.flashcards
    FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY update_flashcards ON public.flashcards
    FOR UPDATE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_flashcards ON public.flashcards
    FOR DELETE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 11. QUIZZES TABLE
-- =====================================================================
ALTER TABLE public.quizzes ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_quizzes ON public.quizzes
    FOR SELECT TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_quizzes ON public.quizzes
    FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY update_quizzes ON public.quizzes
    FOR UPDATE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_quizzes ON public.quizzes
    FOR DELETE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 12. REVISION PLANS TABLE
-- =====================================================================
ALTER TABLE public.revision_plans ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_revision_plans ON public.revision_plans
    FOR SELECT TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_revision_plans ON public.revision_plans
    FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY update_revision_plans ON public.revision_plans
    FOR UPDATE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_revision_plans ON public.revision_plans
    FOR DELETE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 13. USER API KEYS TABLE
-- =====================================================================
ALTER TABLE public.user_api_keys ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_user_api_keys ON public.user_api_keys
    FOR SELECT TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_user_api_keys ON public.user_api_keys
    FOR INSERT TO authenticated
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY update_user_api_keys ON public.user_api_keys
    FOR UPDATE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_user_api_keys ON public.user_api_keys
    FOR DELETE TO authenticated
    USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- =====================================================================
-- 14. ADMIN SETTINGS TABLE
-- =====================================================================
ALTER TABLE public.admin_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_admin_settings ON public.admin_settings
    FOR SELECT TO authenticated
    USING (true); -- authenticated users can select settings

CREATE POLICY write_admin_settings ON public.admin_settings
    FOR ALL TO authenticated
    USING (public.is_admin(auth.uid()))
    WITH CHECK (public.is_admin(auth.uid()));

-- =====================================================================
-- 15. DOCUMENT EMBEDDINGS TABLE (Relational Check via Uploaded Files)
-- =====================================================================
ALTER TABLE public.document_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_document_embeddings ON public.document_embeddings
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.uploaded_files f
            WHERE f.id = uploaded_file_id AND (f.owner_id = auth.uid() OR public.is_admin(auth.uid()))
        )
    );

CREATE POLICY write_document_embeddings ON public.document_embeddings
    FOR ALL TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.uploaded_files f
            WHERE f.id = uploaded_file_id AND (f.owner_id = auth.uid() OR public.is_admin(auth.uid()))
        )
    );
