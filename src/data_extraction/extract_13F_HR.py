import os
import re
from datetime import datetime
from typing import List, Dict, Optional

try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None

import xml.etree.ElementTree as ET

INFORMATION_TABLE_NS = "http://www.sec.gov/edgar/document/thirteenf/informationtable"
NS = {"it": INFORMATION_TABLE_NS}


class FilingDateResolver:
    @staticmethod
    def parse_date(text: str) -> str:
        m = re.search(r"CONFORMED\s+PERIOD\s+OF\s+REPORT:\s*(\d{8})", text)
        if m:
            return m.group(1)
        m = re.search(r"<periodOfReport>(\d{2}-\d{2}-\d{4})</periodOfReport>", text)
        if m:
            dt = datetime.strptime(m.group(1), "%m-%d-%Y")
            return dt.strftime("%Y%m%d")
        m = re.search(r"<reportCalendarOrQuarter>(\d{2}-\d{2}-\d{4})</reportCalendarOrQuarter>", text)
        if m:
            dt = datetime.strptime(m.group(1), "%m-%d-%Y")
            return dt.strftime("%Y%m%d")
        m = re.search(r"FILED\s+AS\s+OF\s+DATE:\s*(\d{8})", text)
        if m:
            return m.group(1)
        return datetime.today().strftime("%Y%m%d")


class InfoTableExtractor:
    def __init__(self, text: str):
        self.text = text

    def extract_xml(self) -> Optional[str]:
        m = re.search(
            r"<FILENAME>form13fInfoTable\.xml[\s\S]*?<TEXT>\s*(<informationTable[\s\S]*?</informationTable>)\s*</TEXT>",
            self.text,
        )
        if m:
            return m.group(1)
        m = re.search(r"(<informationTable[\s\S]*?</informationTable>)", self.text)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _get_text(node: ET.Element, path: str) -> str:
        target = node.find(path, NS)
        return (target.text or "").strip() if target is not None and target.text is not None else ""

    @staticmethod
    def _to_int(s: str) -> Optional[int]:
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            digits = re.sub(r"[^0-9]", "", s)
            return int(digits) if digits else None

    def parse_rows(self, xml: str) -> List[Dict[str, object]]:
        root = ET.fromstring(xml)
        rows: List[Dict[str, object]] = []
        for it_node in root.findall("it:infoTable", NS):
            issuer = self._get_text(it_node, "it:nameOfIssuer")
            class_title = self._get_text(it_node, "it:titleOfClass")
            cusip = self._get_text(it_node, "it:cusip")
            value = self._get_text(it_node, "it:value")
            shares = self._get_text(it_node, "it:shrsOrPrnAmt/it:sshPrnamt")
            shares_type = self._get_text(it_node, "it:shrsOrPrnAmt/it:sshPrnamtType")
            discretion = self._get_text(it_node, "it:investmentDiscretion")
            other_manager = self._get_text(it_node, "it:otherManager")
            vote_sole = self._get_text(it_node, "it:votingAuthority/it:Sole")
            vote_shared = self._get_text(it_node, "it:votingAuthority/it:Shared")
            vote_none = self._get_text(it_node, "it:votingAuthority/it:None")

            rows.append({
                "issuer_name": issuer,
                "class_title": class_title,
                "cusip": cusip,
                "value_usd_quarter_end": self._to_int(value),
                "shares_or_principal": self._to_int(shares),
                "shares_type": shares_type,
                "discretion": discretion,
                "other_manager_seq": self._to_int(other_manager),
                "vote_sole": self._to_int(vote_sole),
                "vote_shared": self._to_int(vote_shared),
                "vote_none": self._to_int(vote_none),
            })
        return rows

    @staticmethod
    def to_dataframe(rows: List[Dict[str, object]]):
        if pd is None:
            return None
        df = pd.DataFrame(rows)
        cols = [
            "issuer_name",
            "class_title",
            "cusip",
            "value_usd_quarter_end",
            "shares_or_principal",
            "shares_type",
            "discretion",
            "other_manager_seq",
            "vote_sole",
            "vote_shared",
            "vote_none",
        ]
        df = df[[c for c in cols if c in df.columns]]
        return df


class SECHeaderParser:
    def __init__(self, text: str):
        self.text = text

    def extract_block(self) -> Optional[str]:
        m = re.search(r"<SEC-HEADER>([\s\S]*?)</SEC-HEADER>", self.text)
        if m:
            return m.group(1).strip()
        return None

    @staticmethod
    def parse_rows(header_text: str) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        section_stack: List[str] = []
        for raw_line in header_text.splitlines():
            line = raw_line.rstrip()
            if not line:
                continue
            leading_ws = len(line) - len(line.lstrip(" \t"))
            indent_level = line[:leading_ws].count("\t") + (line[:leading_ws].count(" ") // 2)
            content = line.lstrip(" \t")
            if content.endswith(":") and ":\t" not in content:
                section_name = content[:-1].strip()
                while len(section_stack) > indent_level:
                    section_stack.pop()
                if len(section_stack) == indent_level:
                    section_stack.append(section_name)
                else:
                    section_stack = section_stack[:indent_level] + [section_name]
                continue
            if ":" in content:
                field, value = content.split(":", 1)
                field = field.strip()
                value = value.strip()
                while len(section_stack) > indent_level:
                    section_stack.pop()
                section_path = " > ".join(section_stack) if section_stack else "HEADER"
                rows.append({"section_path": section_path, "field": field, "value": value})
                continue
            section_path = " > ".join(section_stack) if section_stack else "HEADER"
            rows.append({"section_path": section_path, "field": "_note", "value": content})
        return rows

    @staticmethod
    def to_dataframe(rows: List[Dict[str, object]]):
        if pd is None:
            return None
        df = pd.DataFrame(rows)
        cols = ["section_path", "field", "value"]
        df = df[[c for c in cols if c in df.columns]]
        return df


class PathUtils:
    @staticmethod
    def ensure_dir(path: str) -> None:
        os.makedirs(path, exist_ok=True)

    @staticmethod
    def derive_issuer_from_path(input_path: str) -> str:
        parts = os.path.normpath(input_path).split(os.sep)
        try:
            idx = parts.index("raw_13F_HR")
            return parts[idx + 1]
        except Exception:
            return os.path.basename(os.path.dirname(input_path)) or "unknown_issuer"


class FilingDataResolver:
    @staticmethod
    def parse_field(header_text: str, pattern: str) -> str:
        m = re.search(pattern, header_text, flags=re.IGNORECASE | re.MULTILINE)
        return (m.group(1).strip() if m else "")

    @staticmethod
    def compose_business_address(header_text: str) -> str:
        street = FilingDataResolver.parse_field(header_text, r"BUSINESS ADDRESS:\s*[\r\n]+\s*STREET 1:\s*(.+)")
        city = FilingDataResolver.parse_field(header_text, r"BUSINESS ADDRESS:.*?[\r\n]+\s*CITY:\s*(.+)")
        state = FilingDataResolver.parse_field(header_text, r"BUSINESS ADDRESS:.*?[\r\n]+\s*STATE:\s*([A-Z]{2})")
        zip_code = FilingDataResolver.parse_field(header_text, r"BUSINESS ADDRESS:.*?[\r\n]+\s*ZIP:\s*(\d{5}(?:-\d{4})?)")
        parts = [p for p in [street, city, state, zip_code] if p]
        return ", ".join(parts)

    @staticmethod
    def parse(header_text: str):
        rows = []
        add = rows.append
        # Top submission metadata
        add({"Field": "Accession_Number", "Value": FilingDataResolver.parse_field(header_text, r"ACCESSION NUMBER:\s*([0-9\-]+)")})
        add({"Field": "Submission_Type", "Value": FilingDataResolver.parse_field(header_text, r"CONFORMED SUBMISSION TYPE:\s*([A-Z0-9\-]+)")})
        add({"Field": "Period_of_Report", "Value": FilingDataResolver.parse_field(header_text, r"CONFORMED PERIOD OF REPORT:\s*(\d{8})")})
        add({"Field": "Filed_Date", "Value": FilingDataResolver.parse_field(header_text, r"FILED AS OF DATE:\s*(\d{8})")})
        # Company data
        add({"Field": "Filer_Name", "Value": FilingDataResolver.parse_field(header_text, r"COMPANY CONFORMED NAME:\s*(.+)")})
        add({"Field": "CIK", "Value": FilingDataResolver.parse_field(header_text, r"CENTRAL INDEX KEY:\s*(\d+)")})
        # SIC may appear like: STANDARD INDUSTRIAL CLASSIFICATION: [desc] [6211]
        sic_code = FilingDataResolver.parse_field(header_text, r"STANDARD INDUSTRIAL CLASSIFICATION:\s*.*\[(\d+)\]")
        if not sic_code:
            sic_code = FilingDataResolver.parse_field(header_text, r"SIC:\s*(\d+)")
        add({"Field": "SIC", "Value": sic_code})
        add({"Field": "IRS_Number", "Value": FilingDataResolver.parse_field(header_text, r"IRS NUMBER:\s*(\d+)")})
        add({"Field": "State_of_Incorporation", "Value": FilingDataResolver.parse_field(header_text, r"STATE OF INCORPORATION:\s*([A-Z]{2})")})
        add({"Field": "Fiscal_Year_End", "Value": FilingDataResolver.parse_field(header_text, r"FISCAL YEAR END:\s*(\d{4})")})
        # Business address block
        add({"Field": "Business_Address", "Value": FilingDataResolver.compose_business_address(header_text)})
        add({"Field": "Business_Phone", "Value": FilingDataResolver.parse_field(header_text, r"BUSINESS PHONE:\s*([^\n]+)")})
        # Filing values
        add({"Field": "SEC_File_Number", "Value": FilingDataResolver.parse_field(header_text, r"SEC FILE NUMBER:\s*([0-9\-]+)")})
        add({"Field": "Film_Number", "Value": FilingDataResolver.parse_field(header_text, r"FILM NUMBER:\s*(\d+)")})
        # Former company
        add({"Field": "Former_Name", "Value": FilingDataResolver.parse_field(header_text, r"FORMER CONFORMED NAME:\s*(.+)")})
        add({"Field": "Former_Name_Change_Date", "Value": FilingDataResolver.parse_field(header_text, r"DATE OF NAME CHANGE:\s*(\d{8})")})
        return rows


class TypeBlockScraper13FHR:
    @staticmethod
    def extract_block(text: str) -> Optional[str]:
        m_start = re.search(r"<TYPE>\s*13F-HR\b", text, flags=re.IGNORECASE)
        if not m_start:
            return None
        m_end = re.search(r"<TYPE>\s*INFORMATION TABLE\b", text[m_start.end():], flags=re.IGNORECASE)
        end_pos = m_start.end() + (m_end.start() if m_end else 0)
        block = text[m_start.end(): end_pos].strip()
        return block if block else None

    @staticmethod
    def parse_to_rows(block: str) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            # Inline XML value like: <cik>0002012383</cik>
            m_xml = re.match(r"^<([A-Za-z0-9]+)>(.*?)</\1>$", line)
            if m_xml:
                rows.append({"Field": m_xml.group(1), "Value": m_xml.group(2).strip()})
                continue
            # Ignore bare XML tags (opening/closing) without inline values
            if re.match(r"^</?[A-Za-z0-9]+>", line):
                continue
            # Checkbox pattern like: "Check here if Amendment [X]"
            m_cb = re.match(r"^(.*?)(\[\s*[Xx]\s*\]|\[\s*\])", line)
            if m_cb:
                field = m_cb.group(1).strip().rstrip(":")
                value = "Yes" if "x" in m_cb.group(2).lower() else "No"
                rows.append({"Field": field or "_checkbox", "Value": value})
                continue
            if ":" in line:
                field, value = line.split(":", 1)
                rows.append({"Field": field.strip(), "Value": value.strip()})
            else:
                rows.append({"Field": "_text", "Value": line})
        return rows


class WorkbookWriter:
    def write(self, out_xlsx_path: str, df_infotable, filing_data_rows=None, type_block_rows=None):
        try:
            import pandas as pd
            with pd.ExcelWriter(out_xlsx_path, engine="openpyxl") as writer:
                if df_infotable is not None:
                    df_infotable.to_excel(writer, index=False, sheet_name="InfoTable")
                if filing_data_rows:
                    df_filing = pd.DataFrame(filing_data_rows, columns=["Field", "Value"])
                    df_filing.to_excel(writer, index=False, sheet_name="FilingData")
                if type_block_rows:
                    df_type = pd.DataFrame(type_block_rows, columns=["Field", "Value"])
                    df_type.to_excel(writer, index=False, sheet_name="13F-HR")
            return True
        except Exception:
            import os
            import csv
            base, _ = os.path.splitext(out_xlsx_path)
            out_info_csv = base + "_infotable.csv"
            out_filing_csv = base + "_filing_data.csv"
            out_type_csv = base + "_13fhr.csv"
            if df_infotable is not None:
                if hasattr(df_infotable, "to_csv"):
                    df_infotable.to_csv(out_info_csv, index=False)
                else:
                    cols = list(df_infotable[0].keys()) if df_infotable else []
                    with open(out_info_csv, "w", newline="") as f:
                        w = csv.DictWriter(f, fieldnames=cols)
                        w.writeheader()
                        for r in df_infotable:
                            w.writerow(r)
            if filing_data_rows:
                with open(out_filing_csv, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=["Field", "Value"])
                    w.writeheader()
                    for r in filing_data_rows:
                        w.writerow(r)
            if type_block_rows:
                with open(out_type_csv, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=["Field", "Value"])
                    w.writeheader()
                    for r in type_block_rows:
                        w.writerow(r)
            return False


class Extractor13FHR:
    def run(self, input_path: str, base_output_dir: str = None):
        # Read text
        with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        # Resolve filing date
        date_str = FilingDateResolver.parse_date(text)
        # Extract FilingData from SEC-HEADER (sheet removed from output)
        header_parser = SECHeaderParser(text)
        header_block = header_parser.extract_block()
        filing_data_rows = FilingDataResolver.parse(header_block) if header_block else []
        # Extract InfoTable
        info_extractor = InfoTableExtractor(text)
        xml = info_extractor.extract_xml()
        info_rows = info_extractor.parse_rows(xml) if xml else []
        df_infotable = InfoTableExtractor.to_dataframe(info_rows)
        # Extract 13F-HR type block
        type_block = TypeBlockScraper13FHR.extract_block(text)
        type_rows = TypeBlockScraper13FHR.parse_to_rows(type_block) if type_block else []
        # Derive output path
        issuer = PathUtils.derive_issuer_from_path(input_path)
        out_base = base_output_dir or os.path.join("data", "extracted_13F_HR")
        out_dir = os.path.join(out_base, issuer)
        PathUtils.ensure_dir(out_dir)
        out_xlsx_path = os.path.join(out_dir, f"{date_str}.xlsx")
        # Write workbook: InfoTable, FilingData, 13F-HR (no SEC-HEADER)
        WorkbookWriter().write(out_xlsx_path, df_infotable=df_infotable, filing_data_rows=filing_data_rows, type_block_rows=type_rows)
        return out_xlsx_path


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Extract 13F-HR submission text to an Excel workbook")
    parser.add_argument("input_path", help="Path to the 13F-HR submission .txt file")
    parser.add_argument(
        "--out-dir",
        dest="base_output_dir",
        default=None,
        help="Base output directory (default: data/extracted_13F_HR)",
    )
    args = parser.parse_args()

    try:
        extractor = Extractor13FHR()
        out_path = extractor.run(args.input_path, base_output_dir=args.base_output_dir)
        print(f"Workbook written: {out_path}")
        sys.exit(0)
    except Exception as e:
        print(f"Error extracting workbook: {e}", file=sys.stderr)
        sys.exit(2)