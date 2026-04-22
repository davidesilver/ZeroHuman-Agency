"""Consolidation sub-package."""
from .worker import run_consolidation, ConsolidationReport
from .verifier import verify, VerificationResult
from .extractor import extract_facts_from_text

__all__ = [
    "run_consolidation",
    "ConsolidationReport",
    "verify",
    "VerificationResult",
    "extract_facts_from_text",
]
