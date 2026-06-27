-- Migration: 004_Functions
-- Created: 2026-06-27
-- Description: Define helper functions and automatic triggers for updated_at tracking.

-- =====================================================================
-- 1. SECURITY DEFINER FUNCTION FOR ADMIN CHECK (avoids RLS recursion)
-- =====================================================================
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

-- =====================================================================
-- 2. REUSABLE TRIGGER FUNCTION FOR UPDATING UPDATED_AT TIMESTAMP
-- =====================================================================
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =====================================================================
-- 3. TRIGGERS ASSIGNMENTS
-- =====================================================================
-- users
CREATE TRIGGER set_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- user_preferences
CREATE TRIGGER set_user_preferences_updated_at
    BEFORE UPDATE ON public.user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- subjects
CREATE TRIGGER set_subjects_updated_at
    BEFORE UPDATE ON public.subjects
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- chat_sessions
CREATE TRIGGER set_chat_sessions_updated_at
    BEFORE UPDATE ON public.chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- ai_memory
CREATE TRIGGER set_ai_memory_updated_at
    BEFORE UPDATE ON public.ai_memory
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- revision_plans
CREATE TRIGGER set_revision_plans_updated_at
    BEFORE UPDATE ON public.revision_plans
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- user_api_keys
CREATE TRIGGER set_user_api_keys_updated_at
    BEFORE UPDATE ON public.user_api_keys
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- admin_settings
CREATE TRIGGER set_admin_settings_updated_at
    BEFORE UPDATE ON public.admin_settings
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();
