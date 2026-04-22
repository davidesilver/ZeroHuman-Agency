"""8-point fact verifier — MVP implements 5 of 8 checks.

Before a candidate fact is written to memory_semantic it must pass
this verifier.  Each check returns a (passed, reason) tuple.
The verifier returns a VerificationResult that callers can inspect.

Implemented checks (5/8 MVP):
  1. entity_present  — statement names at least one real-world entity
  2. object_clarity  — subject of the statement is clear and unambiguous
  3. completeness    — statement is a full sentence (not a fragment)
  4. relational      — fact expresses a relationship or attribute, not noise
  5. inference_safe  — statement avoids unverifiable superlatives / absolutes

Deferred to P3 full-pass:
  6. location_context
  7. temporal_context
  8. org_consistency (cross-memory conflict check)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import NamedTuple


class CheckResult(NamedTuple):
    name: str
    passed: bool
    reason: str


@dataclass
class VerificationResult:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def score(self) -> float:
        """Fraction of checks passed (0.0–1.0)."""
        if not self.checks:
            return 0.0
        return sum(1 for c in self.checks if c.passed) / len(self.checks)

    @property
    def failures(self) -> list[str]:
        return [c.name for c in self.checks if not c.passed]

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        detail = "; ".join(
            f"{c.name}={'OK' if c.passed else 'FAIL: ' + c.reason}"
            for c in self.checks
        )
        return f"[{status}] {detail}"


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

_MIN_WORDS = 5
_MAX_WORDS = 120

_NOISE_PATTERNS = re.compile(
    r"^\s*(the|a|an|this|that|these|those|it|he|she|they)\s*$",
    re.IGNORECASE,
)

_ABSOLUTE_PATTERNS = re.compile(
    r"\b(always|never|everyone|nobody|the best|the worst|the only|"
    r"the most|the least|impossible|guaranteed|100%|0%)\b",
    re.IGNORECASE,
)

# Very rough heuristic: a proper entity usually starts with a capital letter
# or is a well-known common noun (brand, product, service…)
_ENTITY_HINT = re.compile(r"[A-Z][a-z]{1,}", re.UNICODE)


def _check_entity_present(statement: str) -> CheckResult:
    """At least one capitalised token suggests a named entity is referenced."""
    has_entity = bool(_ENTITY_HINT.search(statement))
    return CheckResult(
        "entity_present",
        has_entity,
        "" if has_entity else "No capitalised entity token found",
    )


def _check_object_clarity(statement: str) -> CheckResult:
    """Statement must not be a single-token fragment."""
    words = statement.strip().split()
    passed = len(words) >= _MIN_WORDS and not _NOISE_PATTERNS.fullmatch(statement.strip())
    return CheckResult(
        "object_clarity",
        passed,
        "" if passed else f"Too short ({len(words)} words) or purely a pronoun/article",
    )


def _check_completeness(statement: str) -> CheckResult:
    """Statement should end with sentence-terminating punctuation."""
    stripped = statement.strip()
    ends_sentence = stripped.endswith((".", "!", "?", '"', "'"))
    # Also reject overly long statements
    word_count = len(stripped.split())
    not_too_long = word_count <= _MAX_WORDS
    passed = ends_sentence and not_too_long
    return CheckResult(
        "completeness",
        passed,
        "" if passed else (
            "Does not end with punctuation" if not ends_sentence
            else f"Too long ({word_count} words, max {_MAX_WORDS})"
        ),
    )


def _check_relational(statement: str) -> CheckResult:
    """Statement should express an attribute or relationship (contains a verb)."""
    # Simple heuristic: check for common copula / linking verbs
    verb_pattern = re.compile(
        r"\b(is|are|was|were|has|have|had|does|do|did|will|can|should|"
        r"uses|builds|creates|focuses|targets|avoids|prefers|values|believes|"
        r"communicates|writes|speaks|aims|represents|stands for)\b",
        re.IGNORECASE,
    )
    passed = bool(verb_pattern.search(statement))
    return CheckResult(
        "relational",
        passed,
        "" if passed else "No clear relational verb found — may be a fragment",
    )


def _check_inference_safe(statement: str) -> CheckResult:
    """Flag unverifiable absolutes that erode memory reliability."""
    match = _ABSOLUTE_PATTERNS.search(statement)
    passed = match is None
    return CheckResult(
        "inference_safe",
        passed,
        "" if passed else f"Contains potentially unverifiable absolute: '{match.group()}'"  # type: ignore[union-attr]
        if match else "",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify(statement: str) -> VerificationResult:
    """Run all 5 MVP checks against a candidate statement.

    Returns a VerificationResult.  Call result.passed to decide whether
    the fact is safe to write to memory_semantic.
    """
    result = VerificationResult()
    result.checks.append(_check_entity_present(statement))
    result.checks.append(_check_object_clarity(statement))
    result.checks.append(_check_completeness(statement))
    result.checks.append(_check_relational(statement))
    result.checks.append(_check_inference_safe(statement))
    return result
