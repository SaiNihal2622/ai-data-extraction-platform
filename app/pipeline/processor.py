"""
Data Processing Pipeline
-------------------------
Cleans, normalizes, deduplicates, and transforms extracted data.
Uses Pandas for tabular operations.
"""

import re
import logging
from typing import Any

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes and cleans extracted web data."""

    def __init__(self):
        self._df: pd.DataFrame | None = None

    def load_data(self, records: list[dict]) -> pd.DataFrame:
        """
        Load a list of dictionaries into a Pandas DataFrame.

        Args:
            records: List of extracted data dictionaries.

        Returns:
            Cleaned DataFrame.
        """
        if not records:
            self._df = pd.DataFrame()
            return self._df

        self._df = pd.DataFrame(records)
        logger.info(f"Loaded {len(self._df)} records with columns: {list(self._df.columns)}")
        return self._df

    def clean_text(self, df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Clean text fields: strip whitespace, normalize unicode, remove control chars.

        Args:
            df: DataFrame to clean. Uses internal state if None.

        Returns:
            Cleaned DataFrame.
        """
        df = df if df is not None else self._df
        if df is None or df.empty:
            return pd.DataFrame()

        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].apply(self._clean_string)

        self._df = df
        return df

    @staticmethod
    def _clean_string(value: Any) -> Any:
        """Clean a single string value."""
        if not isinstance(value, str):
            return value

        # Normalize whitespace
        value = re.sub(r'\s+', ' ', value).strip()

        # Remove control characters (keep newlines)
        value = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)

        # Normalize quotes
        value = value.replace('\u2018', "'").replace('\u2019', "'")
        value = value.replace('\u201c', '"').replace('\u201d', '"')

        # Trim excessive length
        if len(value) > 5000:
            value = value[:5000] + "..."

        return value if value else None

    def remove_duplicates(
        self, df: pd.DataFrame | None = None, subset: list[str] | None = None
    ) -> pd.DataFrame:
        """
        Remove duplicate rows.

        Args:
            df: DataFrame to deduplicate.
            subset: Columns to consider for duplicate detection.

        Returns:
            Deduplicated DataFrame.
        """
        df = df if df is not None else self._df
        if df is None or df.empty:
            return pd.DataFrame()

        original_count = len(df)

        if subset:
            # Only use columns that exist
            valid_subset = [c for c in subset if c in df.columns]
            if valid_subset:
                df = df.drop_duplicates(subset=valid_subset, keep="first")
            else:
                df = df.drop_duplicates(keep="first")
        else:
            df = df.drop_duplicates(keep="first")

        removed = original_count - len(df)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate rows")

        self._df = df.reset_index(drop=True)
        return self._df

    def normalize_fields(self, df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        Normalize field values: lowercase specific columns, format URLs, etc.

        Args:
            df: DataFrame to normalize.

        Returns:
            Normalized DataFrame.
        """
        df = df if df is not None else self._df
        if df is None or df.empty:
            return pd.DataFrame()

        # Normalize URL fields
        url_columns = [c for c in df.columns if "url" in c.lower() or "link" in c.lower()]
        for col in url_columns:
            df[col] = df[col].apply(self._normalize_url)

        # Replace empty strings with NaN for consistent handling
        df = df.replace({"": np.nan, "N/A": np.nan, "n/a": np.nan, "None": np.nan, "null": np.nan})

        self._df = df
        return df

    @staticmethod
    def _normalize_url(value: Any) -> Any:
        """Normalize a URL string."""
        if not isinstance(value, str):
            return value
        # Remove trailing slashes
        value = value.rstrip("/")
        # Ensure scheme
        if value and not value.startswith(("http://", "https://")):
            if value.startswith("//"):
                value = "https:" + value
        return value

    def process(self, records: list[dict]) -> pd.DataFrame:
        """
        Run the full processing pipeline.

        Args:
            records: Raw extracted data records.

        Returns:
            Fully processed DataFrame.
        """
        df = self.load_data(records)
        if df.empty:
            return df

        df = self.clean_text(df)
        df = self.normalize_fields(df)
        df = self.remove_duplicates(df)

        logger.info(f"Processing complete: {len(df)} records, {len(df.columns)} columns")
        return df

    def get_summary(self, df: pd.DataFrame | None = None) -> dict:
        """
        Generate a summary of the processed dataset.

        Returns:
            Summary dictionary with statistics.
        """
        df = df if df is not None else self._df
        if df is None or df.empty:
            return {"total_records": 0, "columns": [], "null_counts": {}}

        return {
            "total_records": len(df),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "null_counts": df.isnull().sum().to_dict(),
            "sample": df.head(3).to_dict(orient="records"),
        }
