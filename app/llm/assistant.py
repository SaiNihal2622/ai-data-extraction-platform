"""
LLM-Assisted Data Production Module
--------------------------------------
Uses OpenRouter API to assist with AI training data quality:
pattern detection, text cleaning, data normalization,
quality scoring, and dataset summarization.
"""

import os
import json
import logging
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMAssistant:
    """
    AI-powered assistant for data production workflows.

    Connects to OpenRouter API (OpenAI-compatible) or falls back gracefully.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")
        self._client = None

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key != "your_openrouter_api_key_here")

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://openrouter.ai/api/v1",
                )
            except ImportError:
                logger.warning("openai package not installed — LLM features disabled")
                return None
        return self._client

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        if not self.is_available:
            logger.info("LLM not configured — skipping AI assistance")
            return None

        client = self._get_client()
        if not client:
            return None

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None

    def _parse_json_response(self, result: str) -> Optional[dict | list]:
        """Extract JSON from LLM response, handling markdown code blocks."""
        if not result:
            return None
        try:
            text = result
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError):
            return None

    # ── Core Features ────────────────────────────────────

    def detect_patterns(self, html_snippet: str) -> Optional[dict]:
        """Analyze HTML to detect repeating data patterns."""
        system = (
            "You are an expert web scraping engineer. Analyze the given HTML "
            "and identify repeating data patterns (lists, cards, tables, etc.). "
            "Return your analysis as JSON with keys: "
            "'patterns' (list of {type, selector, description}), "
            "'data_type' (what kind of data this appears to be), "
            "'recommended_approach' (scraping strategy)."
        )
        user = f"Analyze this HTML for data patterns:\n\n```html\n{html_snippet[:3000]}\n```"
        result = self._call_llm(system, user)
        parsed = self._parse_json_response(result)
        return parsed if parsed else ({"raw_analysis": result} if result else None)

    def suggest_selectors(self, html_snippet: str, data_description: str) -> Optional[list[dict]]:
        """Suggest CSS selectors for extracting specific data."""
        system = (
            "You are an expert at CSS selectors and web scraping. "
            "Given HTML and a description of what data to extract, "
            "suggest the best CSS selectors. Return as JSON array: "
            "[{selector, field_name, description}]"
        )
        user = (
            f"I want to extract: {data_description}\n\n"
            f"From this HTML:\n```html\n{html_snippet[:3000]}\n```"
        )
        result = self._call_llm(system, user)
        parsed = self._parse_json_response(result)
        return parsed if isinstance(parsed, list) else ([{"raw_suggestion": result}] if result else None)

    def summarize_data(self, data_sample: list[dict]) -> Optional[str]:
        """Generate a human-readable summary of extracted data."""
        system = (
            "You are a data analyst specializing in AI training datasets. "
            "Summarize the given dataset sample. Describe: what the data contains, "
            "key fields, data quality, patterns, and suitability for AI training. "
            "Keep it concise (3-5 sentences)."
        )
        user = f"Dataset sample (first records):\n\n{json.dumps(data_sample[:10], indent=2, default=str)}"
        return self._call_llm(system, user)

    # ── New AI Data Production Features ──────────────────

    def clean_text_batch(self, records: list[dict], text_fields: list[str] | None = None) -> list[dict]:
        """
        Use LLM to clean and normalize messy text in extracted records.

        Args:
            records: List of data records.
            text_fields: Specific text fields to clean (auto-detects if None).

        Returns:
            Cleaned records.
        """
        if not records or not self.is_available:
            return records

        # Auto-detect text fields
        if not text_fields:
            text_fields = [k for k in records[0].keys()
                          if isinstance(records[0].get(k), str)
                          and k.lower() in ("title", "name", "description", "content", "text", "summary")]

        if not text_fields:
            return records

        # Process in batches of 5 for API efficiency
        sample = records[:5]
        system = (
            "You are a data cleaning specialist. Clean the following text fields "
            "by removing HTML artifacts, fixing encoding issues, normalizing whitespace, "
            "fixing truncated sentences, and ensuring readable text. "
            "Return the cleaned records as a JSON array with the same structure."
        )
        user = (
            f"Clean these text fields {text_fields} in these records:\n\n"
            f"{json.dumps(sample, indent=2, default=str)}"
        )

        result = self._call_llm(system, user)
        parsed = self._parse_json_response(result)

        if isinstance(parsed, list) and len(parsed) == len(sample):
            # Apply cleaned values back
            for i, cleaned in enumerate(parsed):
                if i < len(records):
                    for field in text_fields:
                        if field in cleaned:
                            records[i][field] = cleaned[field]

        return records

    def normalize_data(self, records: list[dict]) -> list[dict]:
        """
        Use AI to normalize inconsistent field values.

        Fixes: mixed date formats, inconsistent casing,
        varying units, abbreviation expansion.
        """
        if not records or not self.is_available:
            return records

        sample = records[:5]
        system = (
            "You are a data normalization specialist. Normalize these records by: "
            "1) Standardizing date formats to ISO 8601, 2) Fixing inconsistent casing, "
            "3) Expanding abbreviations, 4) Standardizing number formats. "
            "Return as a JSON array with the same keys."
        )
        user = f"Normalize these records:\n\n{json.dumps(sample, indent=2, default=str)}"

        result = self._call_llm(system, user)
        parsed = self._parse_json_response(result)

        if isinstance(parsed, list) and len(parsed) == len(sample):
            for i, normalized in enumerate(parsed):
                if i < len(records):
                    records[i].update(normalized)

        return records

    def quality_score(self, data_sample: list[dict]) -> Optional[dict]:
        """
        Return a data quality score (1-10) with justification.

        Returns:
            {"score": 8, "justification": "...", "issues": [...], "suggestions": [...]}
        """
        if not self.is_available:
            return None

        system = (
            "You are a data quality engineer evaluating datasets for AI training. "
            "Rate this dataset from 1-10 for AI training suitability. Consider: "
            "completeness, consistency, accuracy indicators, and structural quality. "
            "Return JSON: {score: number, justification: string, "
            "issues: [string], suggestions: [string]}"
        )
        user = f"Rate this dataset for AI training:\n\n{json.dumps(data_sample[:10], indent=2, default=str)}"

        result = self._call_llm(system, user)
        parsed = self._parse_json_response(result)
        return parsed if isinstance(parsed, dict) else ({"raw_validation": result} if result else None)

    def validate_with_ai(self, data_sample: list[dict], expected_schema: str = "") -> Optional[dict]:
        """Use AI to validate data quality and suggest improvements."""
        system = (
            "You are a data quality engineer. Review the dataset and identify: "
            "1) Data quality issues, 2) Missing information, "
            "3) Inconsistencies, 4) Suggestions for improvement. "
            "Return as JSON: {quality_score: 1-10, issues: [...], suggestions: [...]}"
        )
        schema_note = f"\nExpected schema: {expected_schema}" if expected_schema else ""
        user = f"Review this dataset:{schema_note}\n\n{json.dumps(data_sample[:10], indent=2, default=str)}"

        result = self._call_llm(system, user)
        parsed = self._parse_json_response(result)
        return parsed if isinstance(parsed, dict) else ({"raw_validation": result} if result else None)
