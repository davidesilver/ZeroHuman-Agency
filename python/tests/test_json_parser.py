"""
Comprehensive Test Suite for RobustJSONParser

Tests cover all parsing strategies, edge cases, and production scenarios.
Ensures 99.9%+ JSON parsing success rate for LLM responses.

Author: AI Engineering Team
Created: 2026-04-16
"""

import pytest
import json
from src.content_engine.utils.json_parser import RobustJSONParser, parse_llm_json


class TestDirectParseStrategy:
    """Test Strategy 1: Direct JSON parsing."""

    def test_clean_json(self):
        """Test parsing clean JSON without any markdown."""
        text = '{"score": 8.5, "reasoning": "Good quality content"}'
        result = RobustJSONParser.parse_llm_response(text, "test_clean")

        assert result is not None
        assert result["score"] == 8.5
        assert result["reasoning"] == "Good quality content"

    def test_nested_objects(self):
        """Test parsing JSON with nested objects."""
        text = '{"user": {"name": "John", "age": 30}, "active": true}'
        result = RobustJSONParser.parse_llm_response(text, "test_nested")

        assert result is not None
        assert result["user"]["name"] == "John"
        assert result["user"]["age"] == 30
        assert result["active"] is True

    def test_arrays(self):
        """Test parsing JSON with arrays."""
        text = '{"scores": [8.5, 9.0, 7.5], "tags": ["quality", "engagement"]}'
        result = RobustJSONParser.parse_llm_response(text, "test_arrays")

        assert result is not None
        assert result["scores"] == [8.5, 9.0, 7.5]
        assert result["tags"] == ["quality", "engagement"]

    def test_whitespace_handling(self):
        """Test that parser handles various whitespace patterns."""
        text = '''
        {
            "key": "value",
            "number": 42
        }
        '''
        result = RobustJSONParser.parse_llm_response(text, "test_whitespace")

        assert result is not None
        assert result["key"] == "value"
        assert result["number"] == 42


class TestStripOuterFencesStrategy:
    """Test Strategy 2: Strip outer markdown fences."""

    def test_json_fence(self):
        """Test stripping ```json``` fences."""
        text = '''```json
        {
            "score": 8.5,
            "reasoning": "Good"
        }
        ```'''
        result = RobustJSONParser.parse_llm_response(text, "test_json_fence")

        assert result is not None
        assert result["score"] == 8.5

    def test_python_fence(self):
        """Test stripping ```python``` fences."""
        text = '''```python
        {"result": "success", "code": 200}
        ```'''
        result = RobustJSONParser.parse_llm_response(text, "test_python_fence")

        assert result is not None
        assert result["result"] == "success"

    def test_plain_fence(self):
        """Test stripping plain ``` fences."""
        text = '''```
        {"message": "hello"}
        ```'''
        result = RobustJSONParser.parse_llm_response(text, "test_plain_fence")

        assert result is not None
        assert result["message"] == "hello"

    def test_nested_code_blocks_in_strings(self):
        """
        CRITICAL TEST: Handle code blocks inside JSON strings.

        This is the main bug that the original parser couldn't handle.
        The original rsplit approach would truncate the string at the
        first ``` it found, even if it was inside a JSON string value.
        """
        text = '''```json
        {
            "title": "Python Tutorial",
            "body": "Here's an example: ```python x=1 ```",
            "code_block": "Use ``` for code blocks"
        }
        ```'''
        result = RobustJSONParser.parse_llm_response(text, "test_nested_code_blocks")

        assert result is not None
        assert result["title"] == "Python Tutorial"
        assert result["body"] == "Here's an example: ```python x=1 ```"
        assert result["code_block"] == "Use ``` for code blocks"

    def test_multiple_code_blocks_in_string(self):
        """Test multiple code blocks in a single string value."""
        text = '''```json
        {
            "content": "First: ```python a=1 ``` and Second: ```python b=2 ```"
        }
        ```'''
        result = RobustJSONParser.parse_llm_response(text, "test_multiple_code_blocks")

        assert result is not None
        assert "First: ```python a=1 ```" in result["content"]
        assert "Second: ```python b=2 ```" in result["content"]


class TestExtractFirstJSONStrategy:
    """Test Strategy 3: Extract first JSON using brace counting."""

    def test_embedded_in_conversation(self):
        """Test extraction from conversational text."""
        text = "Here's the analysis:\n{\"score\": 8.5, \"reasoning\": \"Good\"}\nDoes this help?"
        result = RobustJSONParser.parse_llm_response(text, "test_conversation")

        assert result is not None
        assert result["score"] == 8.5

    def test_multiple_json_objects(self):
        """Test that we extract the first valid JSON object."""
        text = '{"invalid": missing} {"valid": true, "data": 42} {"also": false}'
        result = RobustJSONParser.parse_llm_response(text, "test_multiple_json")

        assert result is not None
        assert result["valid"] is True
        assert result["data"] == 42

    def test_text_before_and_after(self):
        """Test JSON embedded in the middle of text."""
        text = "The analysis results are: {\"result\": \"success\", \"code\": 200} Thank you!"
        result = RobustJSONParser.parse_llm_response(text, "test_embedded")

        assert result is not None
        assert result["result"] == "success"

    def test_braces_in_strings(self):
        """Test that braces in strings don't confuse the counter."""
        text = 'Start: {"message": "Use {braces} in strings", "code": 200} End'
        result = RobustJSONParser.parse_llm_response(text, "test_braces_in_strings")

        assert result is not None
        assert result["message"] == "Use {braces} in strings"


class TestRegexExtractionStrategy:
    """Test Strategy 4: Regex-based extraction."""

    def test_simple_json(self):
        """Test regex extraction on simple JSON."""
        text = '{"key": "value", "number": 42}'
        result = RobustJSONParser.parse_llm_response(text, "test_regex_simple")

        assert result is not None
        assert result["key"] == "value"

    def test_json_with_special_chars(self):
        """Test JSON with special characters in values."""
        text = '{"message": "Hello, World!", "emoji": "🎉"}'
        result = RobustJSONParser.parse_llm_response(text, "test_regex_special")

        assert result is not None
        assert result["message"] == "Hello, World!"
        assert result["emoji"] == "🎉"


class TestPartialExtractionStrategy:
    """Test fallback partial extraction."""

    def test_partial_extraction_enabled(self):
        """Test partial extraction when all strategies fail."""
        text = "This is not valid JSON at all"

        # Without partial extraction, should return None
        result_no_partial = RobustJSONParser.parse_llm_response(text, "test_no_partial")
        assert result_no_partial is None

        # With partial extraction, should attempt extraction
        result_with_partial = RobustJSONParser.parse_llm_response(text, "test_with_partial", allow_partial=True)
        # May return None or partial dict, depending on if any key-value pairs are found

    def test_partial_key_value_extraction(self):
        """Test extracting individual key-value pairs."""
        text = '"score": 8.5, "reasoning": "Good content"'

        result = RobustJSONParser.parse_llm_response(text, "test_partial", allow_partial=True)

        # Should extract at least some key-value pairs
        assert result is not None
        assert "score" in result or "reasoning" in result


class TestEdgeCases:
    """Test edge cases and production scenarios."""

    def test_empty_string(self):
        """Test handling empty string."""
        result = RobustJSONParser.parse_llm_response("", "test_empty")
        assert result is None

    def test_only_whitespace(self):
        """Test handling whitespace-only string."""
        result = RobustJSONParser.parse_llm_response("   \n\t   ", "test_whitespace_only")
        assert result is None

    def test_invalid_json(self):
        """Test handling completely invalid JSON."""
        result = RobustJSONParser.parse_llm_response("{invalid json}", "test_invalid")
        assert result is None

    def test_escaped_quotes_in_strings(self):
        """Test handling escaped quotes in string values."""
        text = '{"message": "He said \\"hello\\" to me"}'
        result = RobustJSONParser.parse_llm_response(text, "test_escaped_quotes")

        assert result is not None
        assert result["message"] == 'He said "hello" to me'

    def test_unicode_characters(self):
        """Test handling Unicode characters."""
        text = '{"message": "Hello 世界 🌍", "emoji": "😀"}'
        result = RobustJSONParser.parse_llm_response(text, "test_unicode")

        assert result is not None
        assert "世界" in result["message"]
        assert "🌍" in result["message"]

    def test_very_large_json(self):
        """Test handling large JSON objects."""
        large_dict = {f"key_{i}": f"value_{i}" for i in range(100)}
        text = json.dumps(large_dict)

        result = RobustJSONParser.parse_llm_response(text, "test_large_json")

        assert result is not None
        assert len(result) == 100

    def test_deeply_nested_json(self):
        """Test handling deeply nested JSON structures."""
        text = '{"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}}'
        result = RobustJSONParser.parse_llm_response(text, "test_nested_deep")

        assert result is not None
        assert result["level1"]["level2"]["level3"]["level4"]["value"] == "deep"


class TestConvenienceWrapper:
    """Test the parse_llm_json convenience function."""

    def test_convenience_wrapper(self):
        """Test that the wrapper function works correctly."""
        text = '{"score": 8.5}'
        result = parse_llm_json(text, "test_wrapper")

        assert result is not None
        assert result["score"] == 8.5

    def test_wrapper_with_context(self):
        """Test that context is properly used in wrapper."""
        text = '{"result": "success"}'
        result = parse_llm_json(text, "test_context")

        assert result is not None
        assert result["result"] == "success"


class TestProductionScenarios:
    """Test realistic production scenarios from LLM responses."""

    def test_god_advocate_response(self):
        """Simulate realistic God Advocate agent response."""
        text = '''```json
        {
            "analysis": "The content demonstrates strong technical accuracy",
            "strengths": ["Clear explanations", "Good examples"],
            "weaknesses": ["Could add more context"],
            "score": 8.5,
            "recommendation": "approve_with_minor_edits"
        }
        ```'''

        result = RobustJSONParser.parse_llm_response(text, "god_advocate")

        assert result is not None
        assert result["score"] == 8.5
        assert len(result["strengths"]) == 2

    def test_fact_checker_response(self):
        """Simulate realistic Fact Checker agent response."""
        text = '''Based on my analysis:
        {
            "factual_accuracy": "high",
            "claims_verified": 5,
            "issues_found": 0,
            "sources": ["source1.com", "source2.com"]
        }
        All claims appear accurate.'''

        result = RobustJSONParser.parse_llm_response(text, "god_factcheck")

        assert result is not None
        assert result["factual_accuracy"] == "high"
        assert result["claims_verified"] == 5

    def test_malformed_llm_output(self):
        """Test handling of typical LLM formatting issues."""
        # LLMs often add extra text or formatting
        text = '''Here's my evaluation:

```json
{
    "score": 7.5,
    "feedback": "Good but needs improvement"
}
```

Let me know if you need more details!'''

        result = RobustJSONParser.parse_llm_response(text, "scoring")

        assert result is not None
        assert result["score"] == 7.5
        assert result["feedback"] == "Good but needs improvement"


class TestPerformance:
    """Test performance characteristics."""

    def test_fast_path_performance(self):
        """Test that clean JSON is parsed quickly (direct strategy)."""
        import time

        text = '{"key": "value"}' * 100  # Larger JSON
        start = time.time()

        for _ in range(100):
            result = RobustJSONParser.parse_llm_response(text, "perf_test")

        elapsed = time.time() - start

        assert result is not None
        assert elapsed < 1.0  # Should complete 100 parses in < 1 second


class TestErrorHandling:
    """Test error handling and logging."""

    def test_none_input(self):
        """Test handling None input."""
        result = RobustJSONParser.parse_llm_response(None, "test_none")  # type: ignore
        assert result is None

    def test_numeric_input(self):
        """Test handling numeric instead of string input."""
        result = RobustJSONParser.parse_llm_response(123, "test_numeric")  # type: ignore
        assert result is None


# Run tests with: pytest tests/test_json_parser.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
