"""
LLM-Assisted Extraction Module
--------------------------------
Uses OpenRouter or Gemini API to assist with data extraction tasks:
pattern detection, selector suggestion, data summarization, and validation.
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
    AI-powered assistant for data extraction tasks.

    Connects to OpenRouter API (OpenAI-compatible) or falls back gracefully
    when no API key is configured.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-001")
        self._client = None

    @property
    def is_available(self) -> bool:
        """Check if LLM service is configured and available."""
        return bool(self.api_key and self.api_key != "your_openrouter_api_key_here")

    def _get_client(self):
        """Get or create the OpenAI-compatible client for OpenRouter."""
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
        """
        Make a call to the LLM API.

        Args:
            system_prompt: System instruction for the model.
            user_prompt: User message to send.

        Returns:
            Model response text, or None if unavailable.
        """
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

    def detect_patterns(self, html_snippet: str) -> Optional[dict]:
        """
        Analyze HTML to detect repeating data patterns.

        Args:
            html_snippet: A sample of the HTML content (first 3000 chars).

        Returns:
            Dictionary with detected patterns and suggested selectors.
        """
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
        if result:
            try:
                # Try to extract JSON from the response
                json_match = result
                if "```json" in result:
                    json_match = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    json_match = result.split("```")[1].split("```")[0]
                return json.loads(json_match)
            except (json.JSONDecodeError, IndexError):
                return {"raw_analysis": result}
        return None

    def suggest_selectors(self, html_snippet: str, data_description: str) -> Optional[list[dict]]:
        """
        Suggest CSS selectors for extracting specific data.

        Args:
            html_snippet: Sample HTML content.
            data_description: Natural language description of desired data.

        Returns:
            List of selector suggestions.
        """
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
        if result:
            try:
                json_match = result
                if "```json" in result:
                    json_match = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    json_match = result.split("```")[1].split("```")[0]
                return json.loads(json_match)
            except (json.JSONDecodeError, IndexError):
                return [{"raw_suggestion": result}]
        return None

    def summarize_data(self, data_sample: list[dict]) -> Optional[str]:
        """
        Generate a human-readable summary of extracted data.

        Args:
            data_sample: First 10 records of the dataset.

        Returns:
            Natural language summary string.
        """
        system = (
            "You are a data analyst. Summarize the given dataset sample. "
            "Describe: what the data contains, key fields, data quality, "
            "and any notable patterns. Keep it concise (3-5 sentences)."
        )
        user = f"Dataset sample (first records):\n\n{json.dumps(data_sample[:10], indent=2, default=str)}"

        return self._call_llm(system, user)

    def validate_with_ai(self, data_sample: list[dict], expected_schema: str = "") -> Optional[dict]:
        """
        Use AI to validate data quality and suggest improvements.

        Args:
            data_sample: Sample records to validate.
            expected_schema: Optional expected schema description.

        Returns:
            Validation results and suggestions.
        """
        system = (
            "You are a data quality engineer. Review the dataset and identify: "
            "1) Data quality issues, 2) Missing information, "
            "3) Inconsistencies, 4) Suggestions for improvement. "
            "Return as JSON: {quality_score: 1-10, issues: [...], suggestions: [...]}"
        )
        schema_note = f"\nExpected schema: {expected_schema}" if expected_schema else ""
        user = f"Review this dataset:{schema_note}\n\n{json.dumps(data_sample[:10], indent=2, default=str)}"

        result = self._call_llm(system, user)
        if result:
            try:
                json_match = result
                if "```json" in result:
                    json_match = result.split("```json")[1].split("```")[0]
                elif "```" in result:
                    json_match = result.split("```")[1].split("```")[0]
                return json.loads(json_match)
            except (json.JSONDecodeError, IndexError):
                return {"raw_validation": result}
        return None
