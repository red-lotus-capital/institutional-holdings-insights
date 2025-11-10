# EDGAR 13F‑HR Extraction Workflow

This guide explains how to go from EDGAR filing links to a clean, structured Excel workbook for 13F‑HR filings using the provided scripts.

## Overview
- Scrape complete submission text files (`.txt`) from EDGAR using an Excel file of filing links.
- Convert each submission text file into an arranged Excel workbook with multiple sheets.
- Default directories are used so you can run commands with minimal arguments.

## Prerequisites
- macOS with `bash` and `python3` available.
- Python packages: `pandas`, `openpyxl`, `requests`, `beautifulsoup4`.
  - Install: `python3 -m pip install pandas openpyxl requests beautifulsoup4`
- Network access to `sec.gov` for scraping filing pages and text submissions.

## Directory Layout
- `scripts/`
  - `scrape_edgar_links.sh` — scrapes EDGAR filing pages listed in an Excel file and saves submission `.txt` files.
  - `extract_13F_HR.sh` — converts a submission `.txt` into an arranged Excel workbook.
- `src/data_extraction/`
  - `scrape_edgar_links.py` — Python module that powers the scraping logic.
  - `extract_13F_HR.py` — Python module that parses the submission text and writes the Excel workbook.
- `data/edgar_links/` — default location for input Excel files with filing links.
- `data/raw_13F_HR/` — target for downloaded submission `.txt` files (e.g., `data/raw_13F_HR/blackrock/`, `data/raw_13F_HR/vanguard/`).
- `data/extracted_13F_HR/` — target for generated Excel workbooks (e.g., `data/extracted_13F_HR/blackrock/`, `data/extracted_13F_HR/vanguard/`).

## Prepare Filing Links Excel
- Create or place an Excel file in `data/edgar_links` with rows for filings.
- Minimum columns required:
  - `Form type` — must include `13F-HR` rows.
  - `Filings URL` — URL for the filing detail page on EDGAR.
- Other column names are tolerated via flexible matching (e.g., `Filing URL`). Temporary Excel files like `~$...xlsx` are skipped automatically.

## Step 1: Scrape Submission Text Files
- Command: `./scripts/scrape_edgar_links.sh <filename.xlsx> [--dir <folder>]`
- Defaults: If `--dir` is not provided, the script uses `data/edgar_links`.
- Behavior:
  - Scans the Excel for rows where `Form type` is `13F-HR`.
  - Opens the filing detail page from `Filings URL`.
  - Extracts `Period of Report` from the filing page or falls back to the submission text when needed.
  - Downloads the complete submission text file (`.txt`).
  - If the Excel filename contains `blackrock`, saves to `data/raw_13F_HR/blackrock/<Period>.txt`.
- Example:
  - `./scripts/scrape_edgar_links.sh blackrock.xlsx`
- Output:
  - Saved `.txt` files under `data/raw_13F_HR/blackrock/` with filenames like `20250630.txt`, `20250331.txt`, etc.

## Step 2: Generate Arranged Excel Workbook
- Command: `./scripts/extract_13F_HR.sh <path/to/submission.txt>`
- Example:
  - `./scripts/extract_13F_HR.sh data/raw_13F_HR/blackrock/20240930.txt`
- Output:
  - Excel workbook saved under `data/extracted_13F_HR/<issuer>/<Period>.xlsx` (e.g., `data/extracted_13F_HR/blackrock/20240930.xlsx`).

## Workbook Contents
- `FilingData` — key SEC header fields such as `Accession_Number`, `Submission_Type`, `Period_of_Report`, `Filed_Date`, `Filer_Name`, `CIK`, `SIC`, `IRS_Number`, `State_of_Incorporation`, `Fiscal_Year_End`, `Business_Address`, `Business_Phone`, `SEC_File_Number`, `Film_Number`, `Former_Name`, `Former_Name_Change_Date`.
- `13F-HR` — structured key/value rows extracted from the block between `<TYPE>13F-HR` and `<TYPE>INFORMATION TABLE`. Inline XML fields are normalized; standalone tags are ignored.
- `Information Table` — parsed holdings (CUSIP, issuer, value, shares, etc.) extracted from the information table section.
- Notes:
  - The legacy `SEC-HEADER` sheet has been removed; data is surfaced in `FilingData` instead.

## End‑to‑End Example
- Scrape filings listed in `blackrock.xlsx`:
  - `./scripts/scrape_edgar_links.sh blackrock.xlsx`
- Scrape filings listed in `vanguard.xlsx`:
  - `./scripts/scrape_edgar_links.sh vanguard.xlsx`
- Generate workbook for a specific period (BlackRock):
  - `./scripts/extract_13F_HR.sh data/raw_13F_HR/blackrock/20240930.txt`
- Generate workbook for a specific period (Vanguard):
  - `./scripts/extract_13F_HR.sh data/raw_13F_HR/vanguard/20240930.txt`
- Verify outputs exist:
  - `ls data/extracted_13F_HR/blackrock/20240930.xlsx`
  - `ls data/extracted_13F_HR/vanguard/20240930.xlsx`

## Options and Behavior
- Default folder for filing links: `data/edgar_links`.
- File saving policy:
  - If a period‑named file already exists, saving behavior depends on implementation; current scripts overwrite or create a timestamped variant when needed.
- Column name matching:
  - URL column candidates include `Filings URL` (preferred) and similar variations.
  - Form type must unequivocally include `13F-HR`.

## Troubleshooting
- "Input file not found": ensure the Excel filename and folder are correct, or pass `--dir`.
- "No matches": confirm the Excel has a `Form type` column and has rows with `13F-HR`.
- Network errors or HTTP 404:
  - Re‑run the scraper; EDGAR pages can throttle or change.
  - Verify `Filings URL` points to the filing detail page, not the index.
- Missing `Period of Report`:
  - The scraper attempts to parse it from HTML; if not present, it falls back to the submission text.
- Excel writing errors:
  - Make sure `openpyxl` is installed.

## Customization
- Support additional issuers:
  - The scraper routes issuer files based on the Excel filename (e.g., `blackrock.xlsx` → `data/raw_13F_HR/blackrock`, `vanguard.xlsx` → `data/raw_13F_HR/vanguard`). To add others, extend the routing logic in `src/data_extraction/scrape_edgar_links.py` by mapping filename keywords to target subfolders.
- Skip existing files:
  - Add a switch to the shell script and processor to skip or overwrite based on preference.
- Verbose logging:
  - Wrap the Python calls with `set -x` or add logging in the modules for per‑row diagnostics.

## Design Notes
- Shell scripts provide stable CLIs and default paths; Python modules contain the parsing and scraping logic.
- Parsing focuses on correctness and readability in the final workbook; unstructured or extraneous tags are filtered out.
- Error handling is resilient: invalid rows are skipped with informative messages; temporary spreadsheets are ignored.

## Quick Reference
- Scrape: `./scripts/scrape_edgar_links.sh <filename.xlsx> [--dir <folder>]`
- Extract: `./scripts/extract_13F_HR.sh <path/to/submission.txt>`
- Inputs: `data/edgar_links/<filename.xlsx>`
- Raw output: `data/raw_13F_HR/blackrock/<Period>.txt`
- Final workbook: `data/extracted_13F_HR/blackrock/<Period>.xlsx`