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
                "value_usd_thousands": self._to_int(value),
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
            "value_usd_thousands",
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


class WorkbookWriter:
    def __init__(self, base_out_dir: str):
        self.base_out_dir = base_out_dir

    def write(self, issuer: str, date_str: str, info_rows: List[Dict[str, object]], header_rows: Optional[List[Dict[str, object]]]) -> str:
        out_dir = os.path.join(self.base_out_dir, issuer)
        PathUtils.ensure_dir(out_dir)
        out_path_xlsx = os.path.join(out_dir, f"{date_str}.xlsx")
        if pd is not None:
            try:
                df_info = InfoTableExtractor.to_dataframe(info_rows)
                df_header = SECHeaderParser.to_dataframe(header_rows or [])
                assert df_info is not None
                with pd.ExcelWriter(out_path_xlsx) as writer:
                    df_info.to_excel(writer, sheet_name="InfoTable", index=False)
                    if df_header is not None and not df_header.empty:
                        df_header.to_excel(writer, sheet_name="SEC-HEADER", index=False)
                return out_path_xlsx
            except Exception:
                pass
        import csv
        out_info_csv = os.path.join(out_dir, f"{date_str}_infotable.csv")
        out_header_csv = os.path.join(out_dir, f"{date_str}_sec_header.csv")
        fieldnames_info = [
            "issuer_name",
            "class_title",
            "cusip",
            "value_usd_thousands",
            "shares_or_principal",
            "shares_type",
            "discretion",
            "other_manager_seq",
            "vote_sole",
            "vote_shared",
            "vote_none",
        ]
        with open(out_info_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames_info)
            w.writeheader()
            for r in info_rows:
                w.writerow(r)
        fieldnames_header = ["section_path", "field", "value"]
        with open(out_header_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames_header)
            w.writeheader()
            for r in (header_rows or []):
                w.writerow(r)
        return out_info_csv


class Extractor13FHR:
    def __init__(self, input_path: str, base_out_dir: Optional[str] = None):
        self.input_path = input_path
        self.base_out_dir = base_out_dir or os.path.join("data", "extracted_13F_HR")

    def read_text(self) -> str:
        with open(self.input_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def run(self) -> str:
        text = self.read_text()
        date_str = FilingDateResolver.parse_date(text)
        issuer = PathUtils.derive_issuer_from_path(self.input_path)

        info_extractor = InfoTableExtractor(text)
        xml = info_extractor.extract_xml()
        if not xml:
            raise RuntimeError("Could not locate <informationTable> XML block in the input file.")
        info_rows = info_extractor.parse_rows(xml)
        if not info_rows:
            raise RuntimeError("No <infoTable> entries found in the informationTable.")

        header_parser = SECHeaderParser(text)
        header_block = header_parser.extract_block()
        header_rows = SECHeaderParser.parse_rows(header_block) if header_block else []

        writer = WorkbookWriter(self.base_out_dir)
        out_path = writer.write(issuer, date_str, info_rows, header_rows)
        return out_path