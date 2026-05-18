"""Content Engine Agents Package.

This package contains all AI agents used in the content pipeline:
- Writer: Generates content from research
- Editor: Reviews and improves drafts
- Adapter: Adapts content for different platforms
- Humanizer: Removes AI patterns and applies brand voice (NEW!)
- GOD System: 4-agent review pipeline (Advocate, Fact-Checker, Creative, Synthesis)
"""

from .adapter import adapt_content
from .editor import edit_draft
from .god_system import run_god_mode
from .humanizer import humanize_draft
from .writer import generate_draft

__all__ = [
    "generate_draft",
    "edit_draft",
    "adapt_content",
    "humanize_draft",
    "run_god_mode",
]
