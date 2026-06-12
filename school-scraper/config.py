"""Configuration for the school scraper."""

BASE_URL = "https://www.privateschoolreview.com"
CATEGORY = "Private Schools"

# Maps location names from the input sheet to Private School Review URL paths.
# Format: "City, ST" or "City" -> "state-slug/city-slug"
LOCATION_URL_MAP = {
    "New York": "new-york/new-york",
    "New York, NY": "new-york/new-york",
    "Brooklyn, NY": "new-york/brooklyn",
    "Los Angeles, CA": "california/los-angeles",
    "Chicago, IL": "illinois/chicago",
    "Boston, MA": "massachusetts/boston",
    "San Francisco, CA": "california/san-francisco",
    "Miami, FL": "florida/miami",
    "Houston, TX": "texas/houston",
    "Philadelphia, PA": "pennsylvania/philadelphia",
}

OUTPUT_COLUMNS = [
    "School",
    "city",
    "category",
    "website",
    "description",
    "verification_status",
    "address",
    "phone",
]

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_DELAY_SECONDS = 1.5
REQUEST_TIMEOUT_SECONDS = 45
MAX_RETRIES = 3
