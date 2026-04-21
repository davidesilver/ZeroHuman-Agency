-- ============================================================================
-- Migration 015: Brand self-service onboarding
--
-- Problem: the `brands` table has RLS enabled with no INSERT policy, and the
-- `users` profile table has a circular INSERT policy (requires brand_id to
-- already exist). New users can therefore never create a brand through the UI.
--
-- Solution: a SECURITY DEFINER RPC function that runs as the postgres role
-- (bypasses RLS) and atomically:
--   1. Creates the brand row
--   2. Creates the public.users profile row linking the caller as 'owner'
--
-- The API route calls this via supabase.rpc('create_brand_with_owner', ...).
-- Direct INSERT on brands from authenticated clients remains denied (no INSERT
-- policy added), keeping all brand creation flowing through this function.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.create_brand_with_owner(
  p_name   text,
  p_slug   text,
  p_topics text[] DEFAULT '{}'
)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER          -- runs as postgres, bypasses RLS
SET search_path = public  -- prevent search_path injection
AS $$
DECLARE
  v_brand_id  uuid;
  v_user_id   uuid := auth.uid();
  v_email     text;
BEGIN
  -- Require an authenticated caller
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Not authenticated';
  END IF;

  -- Validate inputs
  IF p_name IS NULL OR trim(p_name) = '' THEN
    RAISE EXCEPTION 'name is required';
  END IF;
  IF p_slug IS NULL OR trim(p_slug) = '' THEN
    RAISE EXCEPTION 'slug is required';
  END IF;

  -- Check slug uniqueness (gives a cleaner error than the UNIQUE constraint)
  IF EXISTS (SELECT 1 FROM public.brands WHERE slug = p_slug) THEN
    RAISE EXCEPTION 'slug_taken';
  END IF;

  -- Check if this user already has a brand (one brand per user for now)
  IF EXISTS (SELECT 1 FROM public.users WHERE id = v_user_id) THEN
    RAISE EXCEPTION 'user_already_has_brand';
  END IF;

  -- Resolve caller email from auth.users
  SELECT email INTO v_email FROM auth.users WHERE id = v_user_id;

  -- 1. Create the brand
  INSERT INTO public.brands (name, slug, topics)
  VALUES (trim(p_name), p_slug, COALESCE(p_topics, '{}'))
  RETURNING id INTO v_brand_id;

  -- 2. Link caller as owner
  INSERT INTO public.users (id, brand_id, role, email)
  VALUES (v_user_id, v_brand_id, 'owner', v_email);

  RETURN json_build_object(
    'id',   v_brand_id,
    'name', trim(p_name),
    'slug', p_slug
  );
END;
$$;

-- Grant execute to authenticated role (RLS still applies to underlying tables;
-- the function itself is the only authorized entry point for brand creation).
REVOKE ALL ON FUNCTION public.create_brand_with_owner(text, text, text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.create_brand_with_owner(text, text, text[]) TO authenticated;

COMMENT ON FUNCTION public.create_brand_with_owner IS
  'Atomically creates a brand and links the calling authenticated user as owner. '
  'SECURITY DEFINER to bypass RLS bootstrap chicken-and-egg on first setup.';
