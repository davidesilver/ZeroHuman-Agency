"""Deterministic image prompt construction.

Given a draft + brand row + palette, produce a prompt string. Pure function —
no DB access, no LLM calls — so it's trivially testable and cheap to iterate.

Order matters for most image models: subject first, style second, constraints last.
"""
from __future__ import annotations

STYLE_PRESETS = {
    "editorial-minimal":
        "clean editorial photography, flat composition, high-key lighting, "
        "generous negative space, muted background",
    "tech-futuristic":
        "futuristic 3D render, soft gradients, subtle neon accents, glass materials, "
        "photorealistic lighting",
    "warm-human":
        "candid documentary photography, natural window light, warm color grade, "
        "real-world textures, shallow depth of field",
    "illustration-flat":
        "flat vector illustration, two-tone, geometric shapes, no gradients, "
        "corporate editorial style",
}


def build_prompt(
    *,
    draft_title: str,
    draft_body: str,
    brand_name: str,
    palette_hex: list[str],
    style_preset: str,
    prompt_template: str | None,
) -> str:
    """Build the full prompt. If `prompt_template` is set on the brand,
    use it with named placeholders; otherwise fall back to the default layout."""
    subject = _extract_subject(draft_title, draft_body)
    style = STYLE_PRESETS.get(style_preset, STYLE_PRESETS["editorial-minimal"])
    palette_clause = (
        f"palette: {', '.join(palette_hex[:5])}" if palette_hex else ""
    )

    if prompt_template:
        return prompt_template.format(
            subject=subject, style=style, palette=palette_clause, brand=brand_name,
        ).strip()

    parts = [
        subject,
        style,
        palette_clause,
        "no text, no logos, no watermarks",   # leave text/logos to post-processing
        "aspect ratio as specified",
    ]
    return ". ".join(p for p in parts if p)


def _extract_subject(title: str, body: str, max_chars: int = 200) -> str:
    """Extract a concise visual subject from title + first body sentence.
    Heuristic: take title + first sentence of body, cap at max_chars.
    Deliberate: no LLM — prompt builder must be pure and testable.
    """
    first_sentence = body.strip().split(".")[0].strip() if body else ""
    base = f"{title.strip()} — {first_sentence}" if first_sentence else title.strip()
    return base[:max_chars]
