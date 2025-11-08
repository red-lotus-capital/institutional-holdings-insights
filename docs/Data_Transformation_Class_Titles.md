# Class Title Transformation

This document describes how security class titles in 13F-HR InfoTable data are interpreted and normalized by the transformation module under `src/data_transformation`.

## Purpose
- Provide consistent, human-readable normalization for the `class_title` field extracted from 13F-HR filings.
- Establish guidance for special notations frequently seen in 13F data.

## Warrant Notation: `*W EXP MM/DD/YYYY`
- The entries labeled like `*W EXP MM/DD/YYYY` represent **warrants**—financial instruments that give the holder the right (but not the obligation) to purchase a company’s equity (typically common stock) at a specified price before a stated expiration date.
- In the context of a **Form 13F-HR** (a quarterly report filed by institutional investment managers with the SEC), these appear within the `<titleOfClass>` field to describe the specific class or type of security being reported.
- The format `*W EXP MM/DD/YYYY` is a common convention used in 13F filings to denote warrants with a particular expiration date. The placeholder `99/99/9999` typically indicates that the expiration date is either unknown, not applicable, or not disclosed.
- Warrants are distinct from options and stock; they are issued by the company itself and often accompany bonds or preferred stock as a “sweetener” to attract investors.

**Summary**: These entries describe **equity warrants** held by the filer, reported in a 13F-HR filing under the security class field, using a standard notation that includes their expiration dates.

## Normalization Behavior
The transformation module currently normalizes warrant titles as follows:
- `*W EXP 07/01/2024` → `Warrant (expires 2024-07-01)`
- `*W EXP 99/99/9999` → `Warrant (expiry unknown)`

Normalization preserves non-warrant titles unchanged.

## Functions
The module `src/data_transformation/class_title_transformer.py` provides:
- `normalize_class_title(title: str) -> str`
  - Normalizes a single `class_title` string. Handles warrant patterns and unknown expiry placeholders.
- `normalize_class_titles(titles: List[str]) -> List[str]`
  - Batch-normalizes a list of titles.
- `normalize_class_title_column(df, column='class_title', out_column=None)`
  - DataFrame helper: normalizes a column in-place (default) or writes to `out_column`.

## Usage Examples
```python
from src.data_transformation.class_title_transformer import (
    normalize_class_title, normalize_class_titles, normalize_class_title_column
)

# Single title
normalize_class_title("*W EXP 07/01/2024")
# -> "Warrant (expires 2024-07-01)"

# List of titles
titles = ["COMMON", "*W EXP 99/99/9999", "PFD"]
normalize_class_titles(titles)
# -> ["COMMON", "Warrant (expiry unknown)", "PFD"]

# DataFrame column (in-place)
import pandas as pd

df = pd.DataFrame({
    "class_title": ["*W EXP 07/01/2024", "COMMON", "*W EXP 99/99/9999"]
})
normalize_class_title_column(df, column="class_title")
# df["class_title"] becomes ["Warrant (expires 2024-07-01)", "COMMON", "Warrant (expiry unknown)"]

# DataFrame column (to a new column)
normalize_class_title_column(df, column="class_title", out_column="class_title_normalized")
# df["class_title_normalized"] contains normalized values, original column preserved
```

## Extensibility
- Additional patterns can be added over time (e.g., ADR/ADS, preferred depositary shares, units, rights, notes/debentures).
- Consider pairing normalization with a classification field (e.g., `security_type`) for analytics.