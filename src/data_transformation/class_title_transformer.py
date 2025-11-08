"""
Class Title Transformation Utilities

This module provides helpers to normalize and interpret security class titles
found in 13F InfoTable data. Initial focus: normalize warrant notation
("*W EXP MM/DD/YYYY") and map it to a descriptive string.

Functions:
- normalize_class_title(title: str) -> str
- normalize_class_titles(titles: List[str]) -> List[str]
- normalize_class_title_column(df, column='class_title', out_column=None) -> DataFrame

Notes:
- The warrant pattern often appears in 13F filings as "*W EXP MM/DD/YYYY".
- A placeholder date like "99/99/9999" indicates unknown/undisclosed expiration.
"""
from __future__ import annotations

import re
from typing import List, Optional

try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None

# Pattern to detect warrant notation, allowing for unknown expiry placeholder
_WARRANT_PAT = re.compile(r"\*W\s*EXP\s*([0-9]{2}/[0-9]{2}/[0-9]{2,4}|99/99/9999)", re.IGNORECASE)


def _to_iso_date(mdy: str) -> str:
    """Convert MM/DD/YYYY (or shorter year) to ISO YYYY-MM-DD if possible.
    If year is not 4 digits, keep the original MM/DD/YYY string as-is.
    """
    parts = mdy.split("/")
    if len(parts) != 3:
        return mdy
    mm, dd, yy = parts
    if len(yy) == 4:
        return f"{yy}-{mm}-{dd}"
    return mdy


def parse_warrant_expiration(title: str) -> Optional[str]:
    """Return the expiration date string from a warrant title if present.
    Recognizes '*W EXP MM/DD/YYYY' and the placeholder '99/99/9999'.
    """
    m = _WARRANT_PAT.search(title or "")
    if not m:
        return None
    return m.group(1)


def normalize_class_title(title: str) -> str:
    """Normalize a single class title.

    - If it matches the warrant pattern '*W EXP MM/DD/YYYY', returns one of:
      - 'Warrant (expires YYYY-MM-DD)' when the date is specific
      - 'Warrant (expiry unknown)' when the placeholder '99/99/9999' is used
    - Otherwise, returns the original title unchanged.
    """
    if not title:
        return title
    expiry = parse_warrant_expiration(title)
    if expiry:
        if expiry == "99/99/9999":
            return "Warrant (expiry unknown)"
        iso = _to_iso_date(expiry)
        return f"Warrant (expires {iso})"
    return title


def normalize_class_titles(titles: List[str]) -> List[str]:
    """Normalize a list of class titles using normalize_class_title."""
    return [normalize_class_title(t) for t in titles]


def normalize_class_title_column(df, column: str = "class_title", out_column: Optional[str] = None):
    """Normalize a DataFrame column of class titles.

    - If out_column is None, modifies the input column in place.
    - If out_column is provided, writes normalized values to that column.

    Returns the DataFrame for convenience.
    """
    if pd is None:
        raise ImportError("pandas is required for normalize_class_title_column")
    if column not in df.columns:
        return df
    normalized = df[column].astype(str).map(normalize_class_title)
    if out_column:
        df[out_column] = normalized
    else:
        df[column] = normalized
    return df