-- Migration: 008_Chat_Persistence_Columns
-- Created: 2026-06-28
-- Description: Expand chat_sessions, chat_messages, and ai_memory schemas for Phase 4C persistence, soft deletes, cost tracking, and detailed memory profiles.

-- 1. Alter chat_sessions for soft deletion, summaries, and tags
ALTER TABLE public.chat_sessions
ADD COLUMN IF NOT EXISTS last_message TEXT,
ADD COLUMN IF NOT EXISTS message_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS model_used TEXT,
ADD COLUMN IF NOT EXISTS archived BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS pinned BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS favorite BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS folder TEXT,
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS conversation_summary TEXT,
ADD COLUMN IF NOT EXISTS summary_version TEXT DEFAULT '1.0',
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

-- 2. Alter chat_messages for exact page parameters, token counts, cost, and response latency metadata
ALTER TABLE public.chat_messages
ADD COLUMN IF NOT EXISTS chat_id UUID REFERENCES public.chat_sessions(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS content TEXT,
ADD COLUMN IF NOT EXISTS images JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS documents JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS estimated_cost NUMERIC(8, 6) DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS response_metadata JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS message_index INT,
ADD COLUMN IF NOT EXISTS context_json JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS metadata_json JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS sources_json JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS warning TEXT DEFAULT '',
ADD COLUMN IF NOT EXISTS source_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS suggestions_json JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS response_time NUMERIC;

-- 3. Alter ai_memory for relevance scoring, type taxonomy, and decay tracking
ALTER TABLE public.ai_memory
ADD COLUMN IF NOT EXISTS confidence NUMERIC(3, 2) DEFAULT 1.00,
ADD COLUMN IF NOT EXISTS last_used TIMESTAMPTZ DEFAULT now(),
ADD COLUMN IF NOT EXISTS times_referenced INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS memory_type TEXT DEFAULT 'general_fact';
