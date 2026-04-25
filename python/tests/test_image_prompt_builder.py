from content_engine.services.image_prompt_builder import build_prompt


def test_default_template_includes_style_and_palette():
    p = build_prompt(
        draft_title="5 systems to ship faster",
        draft_body="Most teams overbuild. Start with one dashboard.",
        brand_name="EmptyBox", palette_hex=["#111111","#2e7d32"],
        style_preset="editorial-minimal", prompt_template=None,
    )
    assert "5 systems to ship faster" in p
    assert "editorial photography" in p
    assert "#111111" in p
    assert "no text, no logos" in p


def test_custom_prompt_template_interpolates():
    p = build_prompt(
        draft_title="T", draft_body="", brand_name="B",
        palette_hex=[], style_preset="editorial-minimal",
        prompt_template="{brand} :: {subject} :: {style}",
    )
    assert p.startswith("B :: T ::")


def test_unknown_style_falls_back_to_default():
    p = build_prompt(
        draft_title="X", draft_body="", brand_name="B",
        palette_hex=[], style_preset="does-not-exist", prompt_template=None,
    )
    assert "editorial photography" in p
