"""Create default input Excel files for the scraper."""

from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from config import OUTPUT_COLUMNS

ROOT = Path(__file__).resolve().parent
INPUT_DIR = ROOT / "input"


def main() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    locations_path = INPUT_DIR / "locations.xlsx"
    pd.DataFrame({"Location": ["New York, NY"]}).to_excel(locations_path, index=False)

    template_path = INPUT_DIR / "school_template.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "Schools"
    ws.append(OUTPUT_COLUMNS)
    wb.save(template_path)

    print(f"Created {locations_path}")
    print(f"Created {template_path}")


if __name__ == "__main__":
    main()
