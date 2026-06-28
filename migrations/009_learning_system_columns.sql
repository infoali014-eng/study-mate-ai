-- Migration: 009_Learning_System_Columns
-- Created: 2026-06-28
-- Description: Expand learning schemas for Phase 4D, including spaced repetition, quizzes, planners, pomodoro timers, achievements, and user learning profiles.

-- 1. Alter flashcards for SM-2
ALTER TABLE public.flashcards
ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}',
ADD COLUMN IF NOT EXISTS review_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS correct_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS incorrect_count INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_review TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS next_review TIMESTAMPTZ DEFAULT now(),
ADD COLUMN IF NOT EXISTS easiness_factor NUMERIC(4, 2) DEFAULT 2.50,
ADD COLUMN IF NOT EXISTS interval INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS repetition INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS topic TEXT,
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'New' CHECK (status IN ('New', 'Learned', 'Weak')),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

-- 2. Alter quizzes for permanent attempts
ALTER TABLE public.quizzes
ADD COLUMN IF NOT EXISTS quiz_type TEXT DEFAULT 'MCQ',
ADD COLUMN IF NOT EXISTS difficulty TEXT DEFAULT 'Medium',
ADD COLUMN IF NOT EXISTS question_count INT DEFAULT 5,
ADD COLUMN IF NOT EXISTS percentage NUMERIC(5, 2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS time_taken INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS attempt_number INT DEFAULT 1,
ADD COLUMN IF NOT EXISTS weak_topics JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS wrong_answers JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS correct_answers JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS topic TEXT,
ADD COLUMN IF NOT EXISTS total_questions INT DEFAULT 0;

-- 3. Alter revision_plans for planning tasks
ALTER TABLE public.revision_plans
ADD COLUMN IF NOT EXISTS title TEXT DEFAULT 'Revision Task',
ADD COLUMN IF NOT EXISTS description TEXT,
ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
ADD COLUMN IF NOT EXISTS planned_date DATE DEFAULT CURRENT_DATE,
ADD COLUMN IF NOT EXISTS completed_date DATE,
ADD COLUMN IF NOT EXISTS estimated_duration INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS actual_duration INT DEFAULT 0,
ADD COLUMN IF NOT EXISTS completion_percentage NUMERIC(5, 2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'In Progress', 'Completed', 'Overdue')),
ADD COLUMN IF NOT EXISTS recommendations TEXT,
ADD COLUMN IF NOT EXISTS exam_date DATE,
ADD COLUMN IF NOT EXISTS preparation_level INT DEFAULT 5,
ADD COLUMN IF NOT EXISTS confidence_level INT DEFAULT 5,
ADD COLUMN IF NOT EXISTS plan_text TEXT,
ADD COLUMN IF NOT EXISTS weak_topics TEXT;

-- 4. Create study_sessions (Pomodoro timer sessions)
CREATE TABLE IF NOT EXISTS public.study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
    duration_minutes INT NOT NULL DEFAULT 25,
    session_type TEXT NOT NULL DEFAULT 'Focus',
    notes TEXT,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable RLS for study_sessions
ALTER TABLE public.study_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_study_sessions ON public.study_sessions FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_study_sessions ON public.study_sessions FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_study_sessions ON public.study_sessions FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_study_sessions ON public.study_sessions FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- 5. Create weak_topics (Detailed weaknesses tracker)
CREATE TABLE IF NOT EXISTS public.weak_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES public.subjects(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    weakness_score INT NOT NULL DEFAULT 1,
    attempts INT NOT NULL DEFAULT 0,
    correct INT NOT NULL DEFAULT 0,
    incorrect INT NOT NULL DEFAULT 0,
    last_seen TIMESTAMPTZ DEFAULT now(),
    trend TEXT DEFAULT 'Stable' CHECK (trend IN ('Stable', 'Improving', 'Declining')),
    source TEXT DEFAULT 'General',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT unique_user_subject_topic UNIQUE (owner_id, subject_id, topic)
);

-- Enable RLS for weak_topics
ALTER TABLE public.weak_topics ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_weak_topics ON public.weak_topics FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_weak_topics ON public.weak_topics FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_weak_topics ON public.weak_topics FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_weak_topics ON public.weak_topics FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- 6. Create learning_profiles (Analytics cache)
CREATE TABLE IF NOT EXISTS public.learning_profiles (
    owner_id UUID PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    overall_accuracy NUMERIC(5, 2) DEFAULT 0.00,
    retention_score NUMERIC(5, 2) DEFAULT 0.00,
    learning_speed TEXT DEFAULT 'Steady',
    preferred_session_length INT DEFAULT 25,
    strongest_subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
    weakest_subject_id UUID REFERENCES public.subjects(id) ON DELETE SET NULL,
    current_streak INT DEFAULT 0,
    longest_streak INT DEFAULT 0,
    last_active TIMESTAMPTZ,
    study_level TEXT DEFAULT 'Beginner',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable RLS for learning_profiles
ALTER TABLE public.learning_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_learning_profiles ON public.learning_profiles FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_learning_profiles ON public.learning_profiles FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_learning_profiles ON public.learning_profiles FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_learning_profiles ON public.learning_profiles FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- 7. Create ai_recommendations (Versioned AI recommendations)
CREATE TABLE IF NOT EXISTS public.ai_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    recommendation TEXT NOT NULL,
    reason TEXT,
    priority TEXT DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High')),
    confidence NUMERIC(3, 2) DEFAULT 1.00,
    status TEXT DEFAULT 'Pending' CHECK (status IN ('Pending', 'Dismissed', 'Completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable RLS for ai_recommendations
ALTER TABLE public.ai_recommendations ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_ai_recommendations ON public.ai_recommendations FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_ai_recommendations ON public.ai_recommendations FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_ai_recommendations ON public.ai_recommendations FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_ai_recommendations ON public.ai_recommendations FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));

-- 8. Create user_achievements (Unlocked engagement awards)
CREATE TABLE IF NOT EXISTS public.user_achievements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    achievement_type TEXT NOT NULL,
    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT unique_user_achievement UNIQUE (owner_id, achievement_type)
);

-- Enable RLS for user_achievements
ALTER TABLE public.user_achievements ENABLE ROW LEVEL SECURITY;
CREATE POLICY select_user_achievements ON public.user_achievements FOR SELECT TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY insert_user_achievements ON public.user_achievements FOR INSERT TO authenticated WITH CHECK (owner_id = auth.uid());
CREATE POLICY update_user_achievements ON public.user_achievements FOR UPDATE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid())) WITH CHECK (owner_id = auth.uid() OR public.is_admin(auth.uid()));
CREATE POLICY delete_user_achievements ON public.user_achievements FOR DELETE TO authenticated USING (owner_id = auth.uid() OR public.is_admin(auth.uid()));
