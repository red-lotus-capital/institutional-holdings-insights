#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from src.data_extraction.extract_13F_HR import Extractor13FHR


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract SEC 13F-HR InfoTable and SEC-HEADER into a multi-sheet Excel/CSV")
    parser.add_argument("input", help="Path to combined SEC text file containing form13fInfoTable.xml")
    parser.add_argument(
        "--out-base",
        default=str(Path("data") / "extracted_13F_HR"),
        help="Base output directory (default: data/extracted_13F_HR)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input not found: {input_path}")
        return 1

    try:
        extractor = Extractor13FHR(str(input_path), base_out_dir=args.out_base)
        out_path = extractor.run()
        print(f"Success. Output: {out_path}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())