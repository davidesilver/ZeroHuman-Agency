-- Migration 021: runtime contract stabilization
--
-- Purpose:
-- 1. Re-introduce users.brand_id as an explicit deprecated compatibility column
--    so the repository can bootstrap cleanly after migration 020.
-- 2. Backfill users.brand_id from the oldest brand_members membership.
-- 3. Recreate create_brand_with_owner() against the stabilized schema.
--
-- Notes:
-- - brand_members remains the source of truth for runtime membership.
-- - users.brand_id is compatibility-only and should not be used by new code.

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS brand_id uuid REFERENCES public.brands(id) ON DELETE SET NULL;

COMMENT ON COLUMN public.users.brand_id IS
  '[DEPRECATED] Compatibility column only. Runtime membership lives in public.brand_members.';

WITH ranked_memberships AS (
  SELECT
    bm.user_id,
    bm.brand_id,
    ROW_NUMBER() OVER (PARTITION BY bm.user_id ORDER BY bm.created_at, bm.brand_id) AS rn
  FROM public.brand_members bm
)
UPDATE public.users u
SET brand_id = rm.brand_id
FROM ranked_memberships rm
WHERE u.id = rm.user_id
  AND rm.rn = 1
  AND u.brand_id IS NULL;

CREATE OR REPLACE FUNCTION public.create_brand_with_owner(
  p_name   text,
  p_slug   text,
  p_topics text[] DEFAULT '{}'
)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_brand_id  uuid;
  v_user_id   uuid := auth.uid();
  v_email     text;
  v_role      text := 'owner';
BEGIN
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  IF p_name IS NULL OR trim(p_name) = '' THEN
    RAISE EXCEPTION 'name is required';
  END IF;
  IF p_slug IS NULL OR trim(p_slug) = '' THEN
    RAISE EXCEPTION 'slug is required';
  END IF;

  IF EXISTS (SELECT 1 FROM public.brands WHERE slug = p_slug) THEN
    RAISE EXCEPTION 'slug_taken';
  END IF;

  SELECT email INTO v_email FROM auth.users WHERE id = v_user_id;

  INSERT INTO public.brands (name, slug, topics)
  VALUES (trim(p_name), p_slug, COALESCE(p_topics, '{}'))
  RETURNING id INTO v_brand_id;

  INSERT INTO public.brand_members (user_id, brand_id, role)
  VALUES (v_user_id, v_brand_id, v_role)
  ON CONFLICT (user_id, brand_id) DO NOTHING;

  INSERT INTO public.users (id, brand_id, role, email)
  VALUES (v_user_id, v_brand_id, v_role::user_role, v_email)
  ON CONFLICT (id) DO UPDATE
  SET
    email = EXCLUDED.email,
    role = COALESCE(public.users.role, EXCLUDED.role),
    brand_id = COALESCE(public.users.brand_id, EXCLUDED.brand_id);

  RETURN json_build_object(
    'id',   v_brand_id,
    'name', trim(p_name),
    'slug', p_slug
  );
END;
$$;

REVOKE ALL ON FUNCTION public.create_brand_with_owner(text, text, text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.create_brand_with_owner(text, text, text[]) TO authenticated;

COMMENT ON FUNCTION public.create_brand_with_owner IS
  'Creates a brand and links the caller as owner in brand_members. Also maintains
   public.users.brand_id as a deprecated compatibility pointer to the oldest
   known brand for that user.';
