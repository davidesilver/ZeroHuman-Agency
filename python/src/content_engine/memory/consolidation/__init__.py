"""Consolidation sub-package."""
from .extractor import extract_facts_from_text
from .verifier import VerificationResult, verify
from .worker import ConsolidationReport, run_consolidation

__all__ = [
    "run_consolidation",
    "ConsolidationReport",
    "verify",
    "VerificationResult",
    "extract_facts_from_text",
]
