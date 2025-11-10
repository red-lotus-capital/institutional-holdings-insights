#!/usr/bin/env python3
"""
Scrape EDGAR filing detail pages listed in Excel(s) under data/edgar_links
and download the Complete Submission Text File (.txt). For Excel files
containing 'blackrock' in the filename, save the text file under
`data/raw_13F_HR/blackrock/<PeriodOfReport>.txt`.

Operations:
1) Iterate .xlsx files in data/edgar_links
2) Verify they contain Form type 13F-HR entries
3) Extract filing URL from valid rows
4) Parse Period of Report (YYYYMMDD) from filing page (fallback to .txt)
5) Identify and download the Complete Submission Text File (.txt)
6) Securely save output when Excel filename contains 'blackrock'

Run:
python3 -m src.data_extraction.scrape_edgar_links
or
python3 src/data_extraction/scrape_edgar_links.py
"""

import os
import sys
import re
import time
from pathlib import Path
from typing import Optional, List, Dict, Tuple

USER_AGENT = (
    "institutional-holdings-insights/1.0 (contact: dev@example.com) "
    "requests"
)
DEFAULT_TIMEOUT = 20
BASE_EDGAR = "https://www.sec.gov"

try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None

try:
    import requests  # type: ignore
except Exception:
    requests = None

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None


def _safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_excel(file_path: Path) -> List["pd.DataFrame"]:
    if pd is None:
        raise RuntimeError("pandas is required to read Excel files")
    # Read all sheets to be flexible with varying Excel formats
    xls = pd.ExcelFile(file_path)
    dfs = [xls.parse(sheet_name) for sheet_name in xls.sheet_names]
    return dfs


def _find_column(df: "pd.DataFrame", names: List[str]) -> Optional[str]:
    lower_cols = {c.lower(): c for c in df.columns}
    for name in names:
        key = name.lower()
        if key in lower_cols:
            return lower_cols[key]
    return None


def _normalize_period(period_str: str) -> Optional[str]:
    if not period_str:
        return None
    s = period_str.strip()
    # Accept formats like YYYY-MM-DD or MM-DD-YYYY or YYYYMMDD
    m = re.search(r"(\d{4})[-/]?(\d{2})[-/]?(\d{2})", s)
    if m:
        return f"{m.group(1)}{m.group(2)}{m.group(3)}"
    # Try DD-Mon-YYYY or Mon-DD-YYYY
    m2 = re.search(r"(\d{2})[-/ ]([A-Za-z]{3})[-/ ](\d{4})", s)
    if m2:
        try:
            import datetime
            dt = datetime.datetime.strptime("-".join(m2.groups()), "%d-%b-%Y")
            return dt.strftime("%Y%m%d")
        except Exception:
            pass
    return None


class FilingPageParser:
    @staticmethod
    def extract_period_from_html(html: str) -> Optional[str]:
        # Use BeautifulSoup if available, else regex fallback
        if BeautifulSoup:
            soup = BeautifulSoup(html, "html.parser")
            # Look for label text "Period of Report"
            label = soup.find(string=re.compile(r"Period\s+of\s+Report", re.I))
            if label:
                # Common EDGAR detail page structure: the value is near the label
                # Try next elements around the label
                parent = label.parent
                # Collect candidates from siblings
                candidates: List[str] = []
                if parent:
                    for sib in parent.find_all_next(string=True, limit=5):
                        val = str(sib).strip()
                        if val and not re.search(r"Period\s+of\s+Report", val, re.I):
                            candidates.append(val)
                for cand in candidates:
                    norm = _normalize_period(cand)
                    if norm:
                        return norm
            # Additional selectors
            for node in soup.find_all(string=re.compile(r"Period\s*of\s*Report", re.I)):
                # examine following text nodes quickly
                texts = []
                nxt = node.parent
                for s in (nxt.find_all_next(string=True, limit=10) if nxt else []):
                    t = str(s).strip()
                    if t:
                        texts.append(t)
                for t in texts:
                    norm = _normalize_period(t)
                    if norm:
                        return norm
        # Regex fallback: find text after label
        m = re.search(r"Period\s*of\s*Report\s*[:\-]?\s*(.*?)<", html, flags=re.I | re.S)
        if m:
            val = re.sub(r"\s+", " ", m.group(1)).strip()
            norm = _normalize_period(val)
            if norm:
                return norm
        # Another fallback: find yyyymmdd in HTML
        m2 = re.search(r"(\d{4}[\-/]?\d{2}[\-/]?\d{2})", html)
        if m2:
            norm = _normalize_period(m2.group(1))
            if norm:
                return norm
        return None

    @staticmethod
    def extract_txt_link(html: str, base_url: str) -> Optional[str]:
        if BeautifulSoup:
            soup = BeautifulSoup(html, "html.parser")
            # Prefer anchors with 'Complete submission text file'
            a = soup.find("a", string=re.compile(r"Complete\s+submission\s+text\s+file", re.I))
            if a and a.get("href"):
                href = a.get("href")
                return href if href.startswith("http") else base_url.rstrip("/") + href
            # Else, first .txt link
            for a in soup.find_all("a", href=True):
                href = a.get("href")
                if href and href.lower().endswith(".txt"):
                    return href if href.startswith("http") else base_url.rstrip("/") + href
        # Regex fallback
        m = re.search(r"href=\"([^\"]+\.txt)\"", html, flags=re.I)
        if m:
            href = m.group(1)
            return href if href.startswith("http") else base_url.rstrip("/") + href
        return None


class FilingTextParser:
    @staticmethod
    def extract_period_from_text(text: str) -> Optional[str]:
        # Look for header labels used previously
        m = re.search(r"CONFORMED\s+PERIOD\s+OF\s+REPORT:\s*(\d{8})", text, flags=re.I)
        if m:
            return m.group(1)
        m2 = re.search(r"<periodOfReport>([^<]+)</periodOfReport>", text, flags=re.I)
        if m2:
            return _normalize_period(m2.group(1))
        return None


class EdgarFilingFetcher:
    @staticmethod
    def get(url: str) -> Tuple[Optional[str], Optional[str]]:
        if requests is None:
            return None, "requests library not available"
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
            if resp.status_code != 200:
                return None, f"HTTP {resp.status_code} for {url}"
            return resp.text, None
        except Exception as e:
            return None, str(e)


class EdgarLinksProcessor:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.links_dir = base_dir / "data" / "edgar_links"
        self.raw_out_base = base_dir / "data" / "raw_13F_HR"

    def list_excel_files(self) -> List[Path]:
        if not self.links_dir.exists():
            return []
        return [p for p in self.links_dir.iterdir() if p.is_file() and p.suffix.lower() == ".xlsx"]

    def process_file(self, xlsx_path: Path) -> Dict[str, str]:
        result: Dict[str, str] = {"file": str(xlsx_path), "status": "skipped"}
        if xlsx_path.suffix.lower() != ".xlsx":
            result["error"] = "Not an .xlsx file"
            return result
        try:
            dfs = _read_excel(xlsx_path)
        except Exception as e:
            result["error"] = f"Failed to read Excel: {e}"
            return result
        # Find column names flexibly
        filing_url_col_candidates = ["filings url", "filing url", "url", "link", "href"]
        form_type_candidates = ["form type", "form", "type"]
        processed = 0
        for df in dfs:
            if df is None or df.empty:
                continue
            # normalize columns
            # Try to find required columns
            form_col = _find_column(df, form_type_candidates)
            url_col = _find_column(df, filing_url_col_candidates)
            if not form_col or not url_col:
                continue
            for _, row in df.iterrows():
                form_val = str(row.get(form_col, "")).strip().upper()
                if "13F-HR" not in form_val:
                    continue
                filing_url = str(row.get(url_col, "")).strip()
                if not filing_url:
                    continue
                # fetch filing detail page
                html, err = EdgarFilingFetcher.get(filing_url)
                if err or not html:
                    result[f"error_{processed}"] = f"Filing page fetch failed: {err}"
                    continue
                period = FilingPageParser.extract_period_from_html(html)
                txt_url = FilingPageParser.extract_txt_link(html, BASE_EDGAR)
                if not txt_url:
                    result[f"error_{processed}"] = "No .txt link found on filing page"
                    continue
                text, err2 = EdgarFilingFetcher.get(txt_url)
                if err2 or not text:
                    result[f"error_{processed}"] = f"Text file fetch failed: {err2}"
                    continue
                if not period:
                    period = FilingTextParser.extract_period_from_text(text)
                if not period:
                    result[f"error_{processed}"] = "Missing Period of Report"
                    continue
                # Conditionally save if this Excel belongs to a known issuer (e.g., BlackRock or Vanguard)
                name_lower = xlsx_path.name.lower()
                if ("blackrock" in name_lower) or ("vanguard" in name_lower):
                    issuer = "blackrock" if "blackrock" in name_lower else "vanguard"
                    issuer_dir = self.raw_out_base / issuer
                    _safe_mkdir(issuer_dir)
                    safe_period = re.sub(r"[^0-9]", "", period)
                    if len(safe_period) != 8:
                        result[f"error_{processed}"] = f"Unsafe period value: {period}"
                        continue
                    out_path = issuer_dir / f"{safe_period}.txt"
                    try:
                        # Avoid overwriting silently; if exists, append a timestamp suffix
                        if out_path.exists():
                            ts = int(time.time())
                            out_path = issuer_dir / f"{safe_period}_{ts}.txt"
                        out_path.write_text(text, encoding="utf-8")
                        result[f"saved_{processed}"] = str(out_path)
                        result["status"] = "saved"
                    except Exception as e:
                        result[f"error_{processed}"] = f"Failed to save: {e}"
                        continue
                processed += 1
        if processed == 0 and result.get("status") != "saved":
            result["status"] = "no_matches"
        return result


def main() -> int:
    base = Path(__file__).resolve().parents[2]  # project root
    processor = EdgarLinksProcessor(base)
    files = processor.list_excel_files()
    if not files:
        print("No .xlsx files found in data/edgar_links")
        return 0
    overall: List[Dict[str, str]] = []
    for xlsx in files:
        res = processor.process_file(xlsx)
        overall.append(res)
        print(f"Processed: {xlsx.name} -> {res.get('status')}\n  Details: "
              f"{', '.join([f'{k}:{v}' for k,v in res.items() if k.startswith('error_') or k.startswith('saved_')])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())