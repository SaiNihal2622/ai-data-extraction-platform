"""
Data Exporter Module
--------------------
Exports processed datasets to CSV and JSON formats.
Supports both file-based and in-memory stream exports.
"""

import io
import os
import json
import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)

# Default export directory
EXPORT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "exports")


class DataExporter:
    """Exports processed data to various formats."""

    def __init__(self, export_dir: str = EXPORT_DIR):
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def to_csv(self, df: pd.DataFrame, filename: str | None = None) -> str:
        """
        Export DataFrame to a CSV file.

        Args:
            df: DataFrame to export.
            filename: Optional filename (auto-generated if not provided).

        Returns:
            Path to the exported CSV file.
        """
        if filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.csv"

        filepath = os.path.join(self.export_dir, filename)
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info(f"Exported {len(df)} records to {filepath}")
        return filepath

    def to_json(self, df: pd.DataFrame, filename: str | None = None) -> str:
        """
        Export DataFrame to a JSON file.

        Args:
            df: DataFrame to export.
            filename: Optional filename (auto-generated if not provided).

        Returns:
            Path to the exported JSON file.
        """
        if filename is None:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.json"

        filepath = os.path.join(self.export_dir, filename)

        # Convert to records and handle NaN values
        records = json.loads(df.to_json(orient="records", default_handler=str))

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported {len(df)} records to {filepath}")
        return filepath

    def to_csv_stream(self, df: pd.DataFrame) -> io.BytesIO:
        """
        Export DataFrame to an in-memory CSV stream.

        Args:
            df: DataFrame to export.

        Returns:
            BytesIO stream containing CSV data.
        """
        stream = io.BytesIO()
        df.to_csv(stream, index=False, encoding="utf-8-sig")
        stream.seek(0)
        return stream

    def to_json_stream(self, df: pd.DataFrame) -> io.BytesIO:
        """
        Export DataFrame to an in-memory JSON stream.

        Args:
            df: DataFrame to export.

        Returns:
            BytesIO stream containing JSON data.
        """
        records = json.loads(df.to_json(orient="records", default_handler=str))
        content = json.dumps(records, indent=2, ensure_ascii=False).encode("utf-8")
        stream = io.BytesIO(content)
        stream.seek(0)
        return stream
