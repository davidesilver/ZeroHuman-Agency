-- Migration 022: add missing brands DELETE RLS policy
--
-- Root cause: migration 017 defines brands_select + brands_update but omits
-- brands_delete. With RLS enabled, no DELETE policy = deny-all by default.
-- The server-side `supabase.from('brands').delete()` call in
-- src/app/api/brands/[id]/route.ts would return 0 rows affected and no error,
-- causing the UI to believe the delete succeeded while the row persisted.
--
-- Fix: allow brand owners to delete a brand they own.

DROP POLICY IF EXISTS "brands_delete" ON public.brands;
CREATE POLICY "brands_delete" ON public.brands
  FOR DELETE USING (
    user_has_brand(id) AND auth_user_role() = 'owner'
  );
