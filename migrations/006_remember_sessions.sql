-- Migration: 006_Remember_Sessions
-- Created: 2026-06-27
-- Description: Create remember_sessions table for cookie-based persistent sessions in Supabase.

-- 1. Create table
CREATE TABLE IF NOT EXISTS public.remember_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. Enable RLS
ALTER TABLE public.remember_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY select_remember_sessions ON public.remember_sessions
    FOR SELECT TO authenticated
    USING (user_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY insert_remember_sessions ON public.remember_sessions
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY update_remember_sessions ON public.remember_sessions
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid() OR public.is_admin(auth.uid()))
    WITH CHECK (user_id = auth.uid() OR public.is_admin(auth.uid()));

CREATE POLICY delete_remember_sessions ON public.remember_sessions
    FOR DELETE TO authenticated
    USING (user_id = auth.uid() OR public.is_admin(auth.uid()));

-- 3. Create indexes
CREATE INDEX IF NOT EXISTS idx_remember_sessions_user_id ON public.remember_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_remember_sessions_token_hash ON public.remember_sessions (token_hash);
