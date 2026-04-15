"""Content Engine Agents Package.

This package contains all AI agents used in the content pipeline:
- Writer: Generates content from research
- Editor: Reviews and improves drafts
- Adapter: Adapts content for different platforms
- Humanizer: Removes AI patterns and applies brand voice (NEW!)
- GOD System: 4-agent review pipeline (Advocate, Fact-Checker, Creative, Synthesis)
"""

from .writer import generate_draft
from .editor import edit_draft
from .adapter import adapt_for_platforms
from .humanizer import humanize_draft
from .god_system import run_god_mode

__all__ = [
    "generate_draft",
    "edit_draft",
    "adapt_for_platforms",
    "humanize_draft",
    "run_god_mode",
]
