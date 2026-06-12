#!/usr/bin/env python3
"""Scrape private schools by location and fill the Excel template."""

from __future__ import annotations

import argparse
from pathlib import Path

from excel_io import read_locations, write_missing_report, write_output
from scraper import dedupe_records, scrape_location


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Scrape private schools into Excel.")
    parser.add_argument(
        "--locations",
        type=Path,
        default=root / "input" / "locations.xlsx",
        help="Excel file containing the location list",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=root / "input" / "school_template.xlsx",
        help="Excel template with output column headers",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "output" / "schools_completed.xlsx",
        help="Path for the completed spreadsheet",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=root / "reports" / "missing_data_report.txt",
        help="Path for the missing-data report",
    )
    parser.add_argument(
        "--max-schools",
        type=int,
        default=0,
        help="Optional cap on schools per location (0 = no cap)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)

    locations = read_locations(args.locations)
    all_records = []
    location_errors: list[str] = []

    print(f"Scraping {len(locations)} location(s)...")
    for location in locations:
        print(f"  -> {location}")
        records, error = scrape_location(location)
        if error:
            location_errors.append(error)
            print(f"     warning: {error}")
        if args.max_schools > 0:
            records = records[: args.max_schools]
        print(f"     collected {len(records)} school(s)")
        all_records.extend(records)

    unique_records, duplicate_notes = dedupe_records(all_records)
    write_output(unique_records, args.template, args.output)
    write_missing_report(args.report, unique_records, location_errors, duplicate_notes)

    print("")
    print(f"Completed spreadsheet: {args.output}")
    print(f"Missing data report:    {args.report}")
    print(f"Schools written:        {len(unique_records)}")
    if duplicate_notes:
        print(f"Duplicates removed:     {len(duplicate_notes)}")


if __name__ == "__main__":
    main()
