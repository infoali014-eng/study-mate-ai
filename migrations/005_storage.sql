-- Migration: 005_Storage
-- Created: 2026-06-27
-- Description: Create Supabase Storage buckets and configure security RLS policies.

-- =====================================================================
-- 1. CREATE STORAGE BUCKETS
-- =====================================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    ('user-uploads', 'user-uploads', false, 104857600, ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'text/plain', 'text/markdown', 'text/csv', 'application/json', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']), -- 100MB
    ('extracted-images', 'extracted-images', false, 10485760, ARRAY['image/png', 'image/jpeg', 'image/webp']), -- 10MB
    ('profile-pictures', 'profile-pictures', true, 5242880, ARRAY['image/png', 'image/jpeg', 'image/webp']), -- 5MB (public bucket)
    ('voice-recordings', 'voice-recordings', false, 52428800, ARRAY['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/webm']), -- 50MB
    ('exports', 'exports', false, 20971520, ARRAY['application/pdf', 'text/markdown', 'application/json', 'text/csv']), -- 20MB
    ('temporary-files', 'temporary-files', false, 104857600, NULL) -- 100MB
ON CONFLICT (id) DO UPDATE 
SET public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

-- =====================================================================
-- 2. CREATE STORAGE RLS POLICIES
-- =====================================================================
-- Note: Row Level Security is already enabled by default on storage.objects.

-- 2.1 Profile Pictures (Public Read, Owner Write)
CREATE POLICY "Allow public read access to profile pictures"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'profile-pictures');

CREATE POLICY "Allow owners to upload profile pictures"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'profile-pictures' AND 
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Allow owners to update profile pictures"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'profile-pictures' AND 
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Allow owners to delete profile pictures"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'profile-pictures' AND 
        (storage.foldername(name))[1] = auth.uid()::text
    );

-- 2.2 Owner-Isolated Private Buckets (user-uploads, extracted-images, voice-recordings, exports, temporary-files)
CREATE POLICY "Allow owner select on private buckets"
    ON storage.objects FOR SELECT
    TO authenticated
    USING (
        bucket_id IN ('user-uploads', 'extracted-images', 'voice-recordings', 'exports', 'temporary-files') AND 
        ((storage.foldername(name))[1] = auth.uid()::text OR public.is_admin(auth.uid()))
    );

CREATE POLICY "Allow owner insert on private buckets"
    ON storage.objects FOR INSERT
    TO authenticated
    WITH CHECK (
        bucket_id IN ('user-uploads', 'extracted-images', 'voice-recordings', 'exports', 'temporary-files') AND 
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Allow owner update on private buckets"
    ON storage.objects FOR UPDATE
    TO authenticated
    USING (
        bucket_id IN ('user-uploads', 'extracted-images', 'voice-recordings', 'exports', 'temporary-files') AND 
        (storage.foldername(name))[1] = auth.uid()::text
    );

CREATE POLICY "Allow owner delete on private buckets"
    ON storage.objects FOR DELETE
    TO authenticated
    USING (
        bucket_id IN ('user-uploads', 'extracted-images', 'voice-recordings', 'exports', 'temporary-files') AND 
        ((storage.foldername(name))[1] = auth.uid()::text OR public.is_admin(auth.uid()))
    );
