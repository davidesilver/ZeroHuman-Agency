"""Brand Discovery — auto-extract brand voice from website URLs and social profiles."""

from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import urlparse

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..auth_middleware import _get_brand_id
from ..utils.llm_client import call_llm

logger = logging.getLogger("content_engine.brand_discovery")

router = APIRouter(prefix="/api/brand-discovery", tags=["brand-discovery"])

_MAX_URLS = 10
_MAX_TEXT_CHARS = 12_000
_PER_URL_CHARS = 3_000


class DiscoveryRequest(BaseModel):
    urls: list[str] = []
    social_profiles: list[str] = []


class DiscoveredFact(BaseModel):
    kind: str          # tone_rule | principle | gold_example | discard_example
    statement: str
    confidence: float  # 0.0 – 1.0
    source_url: str = ""


class DiscoveryResponse(BaseModel):
    facts: list[DiscoveredFact]
    suggested_topics: list[str]
    scrape_errors: list[str]


_DISCOVERY_PROMPT = """You are an expert brand voice analyst. You have been given scraped text from a brand's website and/or social media profiles.

Your task is to extract the brand's voice and identity into structured data.

Return a JSON object with this exact structure:
{
  "tone_rules": [
    {"statement": "...", "confidence": 0.9}
  ],
  "principles": [
    {"statement": "...", "confidence": 0.85}
  ],
  "gold_examples": [
    {"statement": "...", "confidence": 0.8}
  ],
  "discard_examples": [
    {"statement": "...", "confidence": 0.75}
  ],
  "suggested_topics": ["topic1", "topic2", "topic3"]
}

Rules:
- tone_rules: 3-5 rules about writing style, voice, and tone (e.g., "Use direct, active voice", "Avoid corporate jargon")
- principles: 3-5 non-negotiable brand values or positioning statements
- gold_examples: 2-4 short quotes or paraphrases of content that exemplifies the brand voice AT ITS BEST (actual phrases/sentences from the scraped text)
- discard_examples: 2-3 examples of what this brand should NEVER sound like (opposite of their voice)
- suggested_topics: 3-6 content research topics relevant to this brand
- confidence: how confident you are in each item (1.0 = very confident, 0.5 = inferred)
- Keep statements concise: tone_rules and principles max 120 chars, examples max 280 chars

SCRAPED CONTENT:
{content}
"""


async def _scrape_url(url: str) -> tuple[str, str | None]:
    """Scrape a URL with trafilatura. Returns (text, error)."""
    if not _is_safe_url(url):
        return "", f"Unsafe URL blocked: {url}"
    try:
        import trafilatura

        def _extract():
            downloaded = trafilatura.fetch_url(url, no_ssl=False)
            if not downloaded:
                return None
            return trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )

        text = await asyncio.get_event_loop().run_in_executor(None, _extract)
        if not text:
            return "", f"No text extracted from {url}"
        return text[:_PER_URL_CHARS], None
    except Exception as e:
        return "", f"Scraping failed for {url}: {e}"


def _is_safe_url(url: str) -> bool:
    """Validate URL against SSRF (private/loopback/link-local/reserved IPs).

    Resolves the hostname and checks every returned address. Hard-blocks
    cloud metadata hosts. Note: DNS rebinding between this check and the
    actual fetch is still possible; for stronger guarantees use a pinned-IP
    transport, but trafilatura.fetch_url does not expose a resolver hook.
    """
    from ..utils.url_safety import UnsafeURLError, assert_safe_public_url

    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        # Hard-block cloud metadata (some may not be in is_link_local checks)
        metadata_hosts = {
            "metadata.google.internal",
            "metadata",
            "169.254.169.254",
            "fd00:ec2::254",
        }
        if host in metadata_hosts:
            return False
        assert_safe_public_url(url, allow_http=True)
        return True
    except UnsafeURLError:
        return False
    except Exception:
        return False


@router.post("", response_model=DiscoveryResponse)
async def discover_brand(body: DiscoveryRequest, request: Request):
    """Analyze website URLs and social profiles to extract brand voice.

    Scrapes up to 10 URLs with trafilatura, feeds the text to the configured
    LLM, and returns structured brand identity facts ready for review.
    """
    brand_id = _get_brand_id(request)

    all_urls = (body.urls + body.social_profiles)[:_MAX_URLS]
    if not all_urls:
        return DiscoveryResponse(facts=[], suggested_topics=[], scrape_errors=["No URLs provided"])

    # Scrape all URLs in parallel
    scrape_results = await asyncio.gather(
        *(_scrape_url(url) for url in all_urls),
        return_exceptions=True,
    )

    scraped_texts: list[str] = []
    scrape_errors: list[str] = []
    for url, result in zip(all_urls, scrape_results):
        if isinstance(result, Exception):
            scrape_errors.append(f"{url}: {result}")
            continue
        text, error = result
        if error:
            scrape_errors.append(error)
        if text:
            scraped_texts.append(f"--- Source: {url} ---\n{text}")

    if not scraped_texts:
        return DiscoveryResponse(
            facts=[],
            suggested_topics=[],
            scrape_errors=scrape_errors or ["Could not extract text from any URL"],
        )

    combined_text = "\n\n".join(scraped_texts)[:_MAX_TEXT_CHARS]
    prompt = _DISCOVERY_PROMPT.format(content=combined_text)

    llm_response = await call_llm(
        prompt=prompt,
        brand_id=brand_id,
        context="brand_discovery",
        action="discover_brand_voice",
        task_type="reasoning",
        temperature=0.3,
    )

    # Parse JSON response
    raw = llm_response.content.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Brand discovery LLM returned invalid JSON: %s", raw[:200])
        return DiscoveryResponse(
            facts=[],
            suggested_topics=[],
            scrape_errors=scrape_errors + ["LLM returned invalid JSON — try again"],
        )

    facts: list[DiscoveredFact] = []

    kind_map = {
        "tone_rules": "tone_rule",
        "principles": "principle",
        "gold_examples": "gold_example",
        "discard_examples": "discard_example",
    }
    for key, kind in kind_map.items():
        for item in data.get(key, []):
            if isinstance(item, dict) and item.get("statement"):
                facts.append(DiscoveredFact(
                    kind=kind,
                    statement=item["statement"],
                    confidence=float(item.get("confidence", 0.75)),
                ))

    suggested_topics = [t for t in data.get("suggested_topics", []) if isinstance(t, str)]

    logger.info(
        "Brand discovery complete for brand %s: %d facts extracted from %d URLs",
        brand_id, len(facts), len(scraped_texts),
    )

    return DiscoveryResponse(
        facts=facts,
        suggested_topics=suggested_topics,
        scrape_errors=scrape_errors,
    )
