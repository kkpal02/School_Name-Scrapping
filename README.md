# School_Name-Scrapping
The objective of this assignment is to collect comprehensive school information from all locations provided and organize the data according to the supplied template and sample dataset.
# School Scraper

Python automation that reads a list of locations from Excel, scrapes private school details from [Private School Review](https://www.privateschoolreview.com), fills the provided spreadsheet template, and generates a missing-data report.

## What it collects

For each school:

- School Name
- City
- Category
- Website
- Description
- Address
- Phone Number
- Verification Status

## Project structure

```
school-scraper/
├── main.py                 # Entry point
├── scraper.py              # Listing + profile scraping logic
├── excel_io.py             # Excel read/write + report generation
├── config.py               # Column names, location URL map, settings
├── create_input_files.py   # Creates default input/template workbooks
├── input/
│   ├── locations.xlsx      # Location list to scrape
│   └── school_template.xlsx
├── output/
│   └── schools_completed.xlsx
└── reports/
    └── missing_data_report.txt
```

## Setup

```bash
cd school-scraper
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
python create_input_files.py
```

## Configure locations

Edit `input/locations.xlsx` and add locations in the `Location` column, for example:

| Location |
|----------|
| New York, NY |
| Brooklyn, NY |
| Los Angeles, CA |

Supported locations can also be mapped in `config.py` under `LOCATION_URL_MAP`.

## Run

Scrape all locations and write output:

```bash
python main.py
```

Test with a small sample:

```bash
python main.py --max-schools 5
```

Custom paths:

```bash
python main.py \
  --locations input/locations.xlsx \
  --template input/school_template.xlsx \
  --output output/schools_completed.xlsx \
  --report reports/missing_data_report.txt
```

## Output files

1. `output/schools_completed.xlsx` — completed spreadsheet using the template column order
2. `reports/missing_data_report.txt` — missing fields, location errors, and duplicate removals

## Notes

- The scraper uses polite delays between requests.
- Duplicate schools found across overlapping locations are removed automatically.
- Verification status is set to `Verified` when the source page indicates a verified school update.
- Review the target website's terms of use before large-scale scraping.

## Example source

Sample data such as **The Brearley School** and **Trinity School** comes from Private School Review profile pages like:

- https://www.privateschoolreview.com/the-brearley-school-profile
- https://www.privateschoolreview.com/trinity-school-new-york-profile
