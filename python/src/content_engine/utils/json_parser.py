"""
Robust JSON Parser for LLM Responses

This module provides a resilient JSON parser specifically designed to handle
the unpredictable output patterns of Large Language Models. It implements
multiple fallback strategies to successfully parse JSON even when LLMs
include code blocks, conversational text, or malformed structures.

Critical for production reliability: prevents system crashes when LLMs
generate valid JSON with code blocks in string fields.

Author: AI Engineering Team
Created: 2026-04-16
"""

import re
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class RobustJSONParser:
    """
    Robust JSON parser with multiple fallback strategies for LLM responses.

    Implements 4 parsing strategies in order of preference:
    1. Direct parse (fastest, for clean JSON)
    2. Strip outer markdown fences (handles ```json``` wrappers)
    3. Extract first JSON object using brace counting (handles conversational text)
    4. Regex-based extraction (handles malformed JSON)

    If all strategies fail, attempts partial extraction as last resort.
    """

    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 30

    @staticmethod
    def parse_llm_response(
        text: str,
        context: str = "unknown",
        allow_partial: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM response with multiple fallback strategies.

        This is the primary interface for parsing LLM-generated JSON.
        It attempts multiple strategies in order, returning the first
        successful result.

        Args:
            text: Raw LLM response text that should contain JSON
            context: Context identifier for error logging (e.g., "god_advocate", "writer")
            allow_partial: If True, attempt to extract partial JSON on complete failure

        Returns:
            Parsed JSON dictionary or None if all strategies fail

        Example:
            >>> response = "```json\\n{\\\"score\\\": 8.5}\\n```"
            >>> result = RobustJSONParser.parse_llm_response(response, "scoring")
            >>> assert result["score"] == 8.5
        """
        strategies = [
            RobustJSONParser._try_direct_parse,
            RobustJSONParser._try_strip_outer_fences,
            RobustJSONParser._try_extract_first_json,
            RobustJSONParser._try_regex_extraction,
        ]

        for i, strategy in enumerate(strategies, 1):
            try:
                result = strategy(text)
                if result:
                    logger.info(f"JSON parse success using strategy {i}/{len(strategies)} for context: {context}")
                    return result
            except Exception as e:
                logger.warning(f"Strategy {i}/{len(strategies)} failed for context {context}: {str(e)}")
                continue

        # All strategies failed
        logger.error(f"All JSON parsing strategies failed for context: {context}")
        if allow_partial:
            logger.warning(f"Attempting partial extraction for context: {context}")
            return RobustJSONParser._try_partial_extraction(text)
        return None

    @staticmethod
    def _try_direct_parse(text: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 1: Direct JSON parse (fastest path).

        This is the optimal path for clean JSON responses from LLMs.
        It should succeed for well-formatted JSON without any markdown
        or conversational wrappers.

        Args:
            text: Text to parse as JSON

        Returns:
            Parsed dictionary or None if parsing fails
        """
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_strip_outer_fences(text: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 2: Strip outer markdown fences only.

        Unlike the naive rsplit approach, this only removes the outermost
        markdown code fences (```json, ```python, ```) while preserving
        any code blocks that might be inside JSON string fields.

        Critical improvement: Handles nested code blocks like:
        {"body": "Example: ```python x=1 ```"}

        Args:
            text: Text with markdown fences to strip

        Returns:
            Parsed dictionary or None if parsing fails
        """
        text = text.strip()

        # Remove ```json, ```python, or ``` opening fences
        if text.startswith('```'):
            # Find first newline after opening fence
            first_newline = text.find('\n')
            if first_newline != -1:
                text = text[first_newline + 1:]

        # Remove closing ``` (only the last one)
        if text.endswith('```'):
            last_fence = text.rfind('```')
            if last_fence != -1:
                text = text[:last_fence]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _try_extract_first_json(object: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 3: Extract first complete JSON object using brace counting.

        This handles cases where JSON is embedded in conversational text,
        such as: "Here's the analysis: {\"score\": 8.5} Does this help?"

        Uses brace counting to find the first complete JSON object,
        properly handling nested braces and string literals.

        Args:
            text: Text containing embedded JSON

        Returns:
            Parsed dictionary or None if no valid JSON found
        """
        text = text.strip()

        brace_depth = 0
        start_idx = -1
        in_string = False
        escape_next = False

        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue

            if char == '\\':
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            # Only count braces outside of strings
            if in_string:
                continue

            if char == '{' and brace_depth == 0:
                start_idx = i

            if char == '{':
                brace_depth += 1
            elif char == '}':
                brace_depth -= 1
                if brace_depth == 0 and start_idx != -1:
                    # Found complete JSON object
                    json_text = text[start_idx:i+1]
                    try:
                        return json.loads(json_text)
                    except json.JSONDecodeError:
                        # Found braces but invalid JSON, continue searching
                        continue

        return None

    @staticmethod
    def _try_regex_extraction(text: str) -> Optional[Dict[str, Any]]:
        """
        Strategy 4: Regex-based extraction of JSON patterns.

        More permissive than brace counting, can capture some malformed
        JSON patterns. Uses a recursive regex pattern to match
        JSON objects with nested structures.

        This is a fallback strategy for edge cases that don't match
        the previous strategies.

        Args:
            text: Text to search for JSON patterns

        Returns:
            Parsed dictionary or None if no valid JSON found
        """
        # Pattern to match JSON objects (with some flexibility for nesting)
        # This is a simplified pattern that works for most common cases
        json_pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'

        matches = re.findall(json_pattern, text, re.DOTALL)

        # Try each match, longest first (more likely to be complete)
        matches.sort(key=len, reverse=True)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None

    @staticmethod
    def _try_partial_extraction(text: str) -> Optional[Dict[str, Any]]:
        """
        Fallback: Extract whatever key-value pairs we can.

        This is the last resort strategy when all JSON parsing fails.
        It attempts to extract individual key-value pairs using regex,
        which is better than complete failure but may miss nested structures.

        Only used when allow_partial=True in parse_llm_response.

        Args:
            text: Text to extract partial JSON from

        Returns:
            Partial dictionary with extracted key-value pairs or None
        """
        result = {}

        # Simple pattern for key: value pairs
        # Matches: "key": "value" or "key": number or "key": true/false/null
        pattern = r'"([^"]+)"\s*:\s*("([^"\\]|\\.)*"|[\d.]+|true|false|null|\{[^}]*\})'

        matches = re.findall(pattern, text)

        for key, value, _ in matches:
            try:
                # Try to parse the value as JSON
                parsed_value = json.loads(value)
                result[key] = parsed_value
            except:
                # Keep as string if parsing fails (remove surrounding quotes)
                result[key] = value.strip('"')

        return result if result else None


def parse_llm_json(text: str, context: str = "unknown") -> Optional[Dict[str, Any]]:
    """
    Convenience wrapper for RobustJSONParser.parse_llm_response.

    This is the recommended interface for most use cases. It provides
    a simple function call that internally uses the robust parser
    with sensible defaults.

    Args:
        text: Raw LLM response text
        context: Context identifier for logging

    Returns:
        Parsed JSON dictionary or None

    Example:
        >>> result = parse_llm_json('{"score": 8.5}', "scoring")
        >>> assert result["score"] == 8.5
    """
    return RobustJSONParser.parse_llm_response(text, context)


# Export key functions and classes
__all__ = [
    'RobustJSONParser',
    'parse_llm_json',
]
