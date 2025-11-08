"""
13F-HR Class Title Category Transformer

Focus: classify `class_title` into simple categories without parsing warrant expirations.

Rules:
- If title contains the word 'ETF' (case-insensitive) → 'ETF'
- Else if title contains '*W' (warrant notation) → 'Warrant'
- Else → original title (used as category)

Exports:
- classify_class_title_category(title: str) -> str
- classify_class_title_categories(titles: List[str]) -> List[str]
- apply_class_category_column(df, in_column='class_title', out_column='class_category') -> DataFrame
"""
from __future__ import annotations

import re
from typing import List, Optional

try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None


def classify_class_title_category(title: str) -> str:
    """Classify a single class_title into a category.

    1) Contains word 'ETF' -> 'ETF'
    2) Contains '*W' -> 'Warrant'
    3) Otherwise -> original title as the category
    """
    if title is None:
        return title
    t = str(title)
    t_upper = t.upper()
    if re.search(r"\bETF\b", t_upper):
        return "ETF"
    if "*W" in t_upper:
        return "Warrant"
    return t


def classify_class_title_categories(titles: List[str]) -> List[str]:
    """Batch classification for a list of titles."""
    return [classify_class_title_category(t) for t in titles]


def apply_class_category_column(df, in_column: str = "class_title", out_column: Optional[str] = "class_category"):
    """Apply category classification to a DataFrame column.

    - Reads from `in_column` (default: 'class_title').
    - Writes to `out_column` (default: 'class_category'). If None, modifies `in_column` in place.
    - Returns the DataFrame for convenience.
    """
    if pd is None:
        raise ImportError("pandas is required for apply_class_category_column")
    if in_column not in df.columns:
        return df
    categorized = df[in_column].astype(str).map(classify_class_title_category)
    if out_column:
        df[out_column] = categorized
    else:
        df[in_column] = categorized
    return df