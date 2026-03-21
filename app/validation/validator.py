"""
Data Validation Engine
-----------------------
Production-grade validation for AI training datasets.
Checks: missing fields, duplicates, schema validation,
format consistency, text quality — generates structured reports.
"""

import re
import logging
from typing import Any
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)


class ValidationIssue:
    """Represents a single validation issue."""

    def __init__(self, field: str, issue_type: str, message: str, row_indices: list[int] | None = None):
        self.field = field
        self.issue_type = issue_type
        self.message = message
        self.row_indices = row_indices or []

    def to_dict(self) -> dict:
        return {
            "field": self.field,
            "type": self.issue_type,
            "message": self.message,
            "affected_rows": len(self.row_indices),
            "sample_indices": self.row_indices[:5],
        }


class ValidationReport:
    """Container for the full validation report."""

    def __init__(self):
        self.issues: list[ValidationIssue] = []
        self.total_records: int = 0
        self.total_fields: int = 0
        self.valid_records: int = 0
        self.invalid_records: int = 0
        self.created_at: datetime = datetime.now(timezone.utc)

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.issue_type == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.issue_type == "warning")

    def to_dict(self) -> dict:
        issue_categories = list({i.field.split("_")[0] if i.field != "_all" else i.message.split()[1]
                                  for i in self.issues})
        return {
            "is_valid": self.is_valid,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "total_fields": self.total_fields,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "total_issues": len(self.issues),
            "issue_categories": issue_categories[:10],
            "created_at": self.created_at.isoformat(),
            "issues": [i.to_dict() for i in self.issues],
        }

    def summary(self) -> dict:
        """Structured summary for Toloka-style output."""
        issue_types = []
        if any(i.field != "_all" and "missing" in i.message.lower() for i in self.issues):
            issue_types.append("missing_fields")
        if any("duplicate" in i.message.lower() for i in self.issues):
            issue_types.append("duplicates")
        if any("format" in i.message.lower() or "invalid" in i.message.lower() for i in self.issues):
            issue_types.append("format_errors")
        if any("schema" in i.message.lower() or "type" in i.message.lower() for i in self.issues):
            issue_types.append("schema_violations")
        if any("consistency" in i.message.lower() or "mixed" in i.message.lower() for i in self.issues):
            issue_types.append("inconsistent_formats")

        return {
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "issues": issue_types,
        }


class DataValidator:
    """Production-grade validator for AI training datasets."""

    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    URL_PATTERN = re.compile(r'^https?://[^\s<>"{}|\\^`\[\]]+$')
    PHONE_PATTERN = re.compile(r'^[\+]?[\d\s\-\(\)]{7,20}$')
    DATE_PATTERN = re.compile(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}')
    NUMBER_PATTERN = re.compile(r'^-?\d+\.?\d*$')

    def validate(self, df: pd.DataFrame) -> ValidationReport:
        """
        Run the full validation suite on a DataFrame.

        Returns:
            ValidationReport with all found issues and valid/invalid counts.
        """
        report = ValidationReport()
        report.total_records = len(df)
        report.total_fields = len(df.columns)

        if df.empty:
            report.issues.append(ValidationIssue(
                field="_dataset",
                issue_type="error",
                message="Dataset is empty — no records extracted",
            ))
            return report

        # Run all checks
        self._check_missing_fields(df, report)
        self._check_duplicates(df, report)
        self._check_url_formats(df, report)
        self._check_email_formats(df, report)
        self._check_text_quality(df, report)
        self._check_field_consistency(df, report)
        self._check_schema_validation(df, report)
        self._check_format_consistency(df, report)

        # Calculate valid/invalid record counts
        error_rows = set()
        for issue in report.issues:
            if issue.issue_type == "error":
                error_rows.update(issue.row_indices)
        report.invalid_records = min(len(error_rows), report.total_records)
        report.valid_records = report.total_records - report.invalid_records

        logger.info(
            f"Validation complete: {report.valid_records}/{report.total_records} valid, "
            f"{report.error_count} errors, {report.warning_count} warnings"
        )
        return report

    def _check_missing_fields(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Check for missing/null values in each column."""
        for col in df.columns:
            null_mask = df[col].isnull() | (df[col].astype(str).str.strip() == "")
            null_count = null_mask.sum()

            if null_count == len(df):
                report.issues.append(ValidationIssue(
                    field=col,
                    issue_type="error",
                    message=f"Column '{col}' is entirely empty",
                    row_indices=list(df.index[null_mask]),
                ))
            elif null_count > 0:
                pct = (null_count / len(df)) * 100
                severity = "error" if pct > 50 else "warning"
                report.issues.append(ValidationIssue(
                    field=col,
                    issue_type=severity,
                    message=f"Column '{col}' has {null_count} missing values ({pct:.1f}%)",
                    row_indices=list(df.index[null_mask]),
                ))

    def _check_duplicates(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Check for duplicate rows."""
        dup_mask = df.duplicated(keep=False)
        dup_count = dup_mask.sum()

        if dup_count > 0:
            report.issues.append(ValidationIssue(
                field="_all",
                issue_type="warning",
                message=f"Found {dup_count} duplicate rows",
                row_indices=list(df.index[dup_mask]),
            ))

        key_columns = [c for c in df.columns if c.lower() in ("title", "name", "url", "id", "link")]
        for col in key_columns:
            col_dups = df[col].dropna().duplicated(keep=False)
            dup_count = col_dups.sum()
            if dup_count > 0:
                report.issues.append(ValidationIssue(
                    field=col,
                    issue_type="warning",
                    message=f"Column '{col}' has {dup_count} duplicate values",
                    row_indices=list(df.index[df[col].isin(df[col][col_dups])]),
                ))

    def _check_url_formats(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Validate URL format in URL-like columns."""
        url_cols = [c for c in df.columns if "url" in c.lower() or "link" in c.lower() or "href" in c.lower()]
        for col in url_cols:
            invalid_indices = []
            for idx, value in df[col].dropna().items():
                if isinstance(value, str) and value.strip() and not self.URL_PATTERN.match(value):
                    invalid_indices.append(idx)
            if invalid_indices:
                report.issues.append(ValidationIssue(
                    field=col,
                    issue_type="warning",
                    message=f"Column '{col}' has {len(invalid_indices)} invalid URL formats",
                    row_indices=invalid_indices,
                ))

    def _check_email_formats(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Validate email format in email-like columns."""
        email_cols = [c for c in df.columns if "email" in c.lower() or "mail" in c.lower()]
        for col in email_cols:
            invalid_indices = []
            for idx, value in df[col].dropna().items():
                if isinstance(value, str) and value.strip() and not self.EMAIL_PATTERN.match(value):
                    invalid_indices.append(idx)
            if invalid_indices:
                report.issues.append(ValidationIssue(
                    field=col,
                    issue_type="error",
                    message=f"Column '{col}' has {len(invalid_indices)} invalid email formats",
                    row_indices=invalid_indices,
                ))

    def _check_text_quality(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Check text fields for quality issues."""
        text_cols = [c for c in df.columns if c.lower() in ("title", "name", "text", "description", "content")]
        for col in text_cols:
            if col not in df.columns:
                continue
            short_mask = df[col].dropna().astype(str).str.len() < 3
            short_count = short_mask.sum()
            if short_count > len(df) * 0.3:
                report.issues.append(ValidationIssue(
                    field=col,
                    issue_type="warning",
                    message=f"Column '{col}' has {short_count} very short values (< 3 chars)",
                    row_indices=list(df.index[df[col].astype(str).str.len() < 3]),
                ))

    def _check_field_consistency(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Check for field value consistency across the dataset."""
        for col in df.columns:
            unique_values = df[col].dropna().nunique()
            if unique_values == 1 and len(df) > 5:
                report.issues.append(ValidationIssue(
                    field=col,
                    issue_type="warning",
                    message=f"Column '{col}' has only 1 unique value across {len(df)} records — may be redundant",
                ))

    def _check_schema_validation(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Validate inferred schema: detect columns that should be numeric but contain strings."""
        for col in df.columns:
            non_null = df[col].dropna()
            if len(non_null) == 0:
                continue

            str_vals = non_null.astype(str)

            # Detect columns that look numeric but have non-numeric values
            numeric_count = str_vals.apply(lambda x: bool(self.NUMBER_PATTERN.match(x.strip()))).sum()
            if 0 < numeric_count < len(non_null) and numeric_count > len(non_null) * 0.5:
                non_numeric = non_null[~str_vals.apply(lambda x: bool(self.NUMBER_PATTERN.match(x.strip())))]
                report.issues.append(ValidationIssue(
                    field=col,
                    issue_type="warning",
                    message=f"Column '{col}' has mixed types: {numeric_count} numeric, {len(non_null) - numeric_count} non-numeric",
                    row_indices=list(non_numeric.index[:10]),
                ))

            # Detect date-like columns with invalid dates
            date_count = str_vals.apply(lambda x: bool(self.DATE_PATTERN.match(x.strip()))).sum()
            if date_count > len(non_null) * 0.5 and date_count < len(non_null):
                non_dates = non_null[~str_vals.apply(lambda x: bool(self.DATE_PATTERN.match(x.strip())))]
                report.issues.append(ValidationIssue(
                    field=col,
                    issue_type="warning",
                    message=f"Column '{col}' appears to be dates but has {len(non_dates)} non-date values",
                    row_indices=list(non_dates.index[:10]),
                ))

    def _check_format_consistency(self, df: pd.DataFrame, report: ValidationReport) -> None:
        """Detect format inconsistencies within columns (e.g. mixed casing, mixed delimiters)."""
        for col in df.columns:
            non_null = df[col].dropna().astype(str)
            if len(non_null) < 5:
                continue

            # Check for mixed case patterns in columns that should be consistent
            if col.lower() in ("status", "category", "type", "tag", "label"):
                unique = non_null.str.strip().unique()
                lower_unique = set(v.lower() for v in unique)
                if len(unique) > len(lower_unique):
                    report.issues.append(ValidationIssue(
                        field=col,
                        issue_type="warning",
                        message=f"Column '{col}' has inconsistent casing ({len(unique)} variants, {len(lower_unique)} unique when lowercased)",
                    ))
