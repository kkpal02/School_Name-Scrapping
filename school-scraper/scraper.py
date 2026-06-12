"""Scrape school listings and profile pages from Private School Review."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import BASE_URL, CATEGORY
from utils import (
    absolute_url,
    clean_text,
    fetch_html,
    get_session,
    normalize_website,
    split_address_phone,
)
from config import REQUEST_TIMEOUT_SECONDS


@dataclass
class SchoolRecord:
    school: str = ""
    city: str = ""
    category: str = CATEGORY
    website: str = ""
    description: str = ""
    verification_status: str = ""
    address: str = ""
    phone: str = ""
    profile_url: str = ""
    source_location: str = ""
    missing_fields: list[str] = field(default_factory=list)

    def to_row(self) -> dict[str, str]:
        return {
            "School": self.school,
            "city": self.city,
            "category": self.category,
            "website": self.website,
            "description": self.description,
            "verification_status": self.verification_status,
            "address": self.address,
            "phone": self.phone,
        }

    def audit(self) -> None:
        self.missing_fields = []
        for key, value in self.to_row().items():
            if not clean_text(value):
                self.missing_fields.append(key)


def location_to_url_path(location: str) -> str:
    from config import LOCATION_URL_MAP

    location = clean_text(location)
    if location in LOCATION_URL_MAP:
        return LOCATION_URL_MAP[location]

    # Try "City, ST" -> state slug / city slug heuristics.
    match = re.match(r"^(.+?),\s*([A-Z]{2})$", location)
    if match:
        city, state = match.group(1).strip(), match.group(2).strip()
        state_names = {
            "AL": "alabama", "AK": "alaska", "AZ": "arizona", "AR": "arkansas",
            "CA": "california", "CO": "colorado", "CT": "connecticut", "DE": "delaware",
            "FL": "florida", "GA": "georgia", "HI": "hawaii", "ID": "idaho",
            "IL": "illinois", "IN": "indiana", "IA": "iowa", "KS": "kansas",
            "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
            "MA": "massachusetts", "MI": "michigan", "MN": "minnesota", "MS": "mississippi",
            "MO": "missouri", "MT": "montana", "NE": "nebraska", "NV": "nevada",
            "NH": "new-hampshire", "NJ": "new-jersey", "NM": "new-mexico", "NY": "new-york",
            "NC": "north-carolina", "ND": "north-dakota", "OH": "ohio", "OK": "oklahoma",
            "OR": "oregon", "PA": "pennsylvania", "RI": "rhode-island", "SC": "south-carolina",
            "SD": "south-dakota", "TN": "tennessee", "TX": "texas", "UT": "utah",
            "VT": "vermont", "VA": "virginia", "WA": "washington", "WV": "west-virginia",
            "WI": "wisconsin", "WY": "wyoming", "DC": "district-of-columbia",
        }
        state_slug = state_names.get(state.upper())
        if state_slug:
            city_slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")
            return f"{state_slug}/{city_slug}"

    city_slug = re.sub(r"[^a-z0-9]+", "-", location.lower()).strip("-")
    return f"new-york/{city_slug}"


def extract_profile_links(soup: BeautifulSoup) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href*='-profile'], a[data-slink*='-profile']"):
        href = anchor.get("data-slink") or anchor.get("href", "")
        if not href:
            continue
        if "-profile" not in href:
            continue
        full = urljoin(BASE_URL, href.split("?")[0])
        if full not in seen:
            seen.add(full)
            links.append(full)
    return links


def fetch_ajax_listing_page(location_path: str, tab: str, page_num: int) -> BeautifulSoup | None:
    url = absolute_url(f"/{location_path}/tab/{tab}/num/{page_num}")
    try:
        response = get_session().get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"},
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        payload = response.json()
        html = payload.get("result", "")
        if not html:
            return None
        return BeautifulSoup(html, "lxml")
    except Exception:
        return None



def collect_listing_urls(location_path: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def add_from_soup(soup: BeautifulSoup) -> None:
        for profile in extract_profile_links(soup):
            if profile not in seen:
                seen.add(profile)
                urls.append(profile)

    # Initial HTML page (top-ranked schools).
    add_from_soup(fetch_html(absolute_url(f"/{location_path}")))

    # AJAX paginated full school list.
    page_num = 1
    while True:
        soup = fetch_ajax_listing_page(location_path, "all", page_num)
        if soup is None:
            break
        add_from_soup(soup)
        page_num += 1

    return urls


def parse_verification_status(soup: BeautifulSoup) -> str:
    text = soup.get_text(" ", strip=True)
    if re.search(r"verified school update", text, re.I):
        return "Verified"
    if re.search(r"verified", text, re.I):
        return "Verified"
    return "Unverified"


def parse_json_ld(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.select('script[type="application/ld+json"]'):
        if not script.string:
            continue
        try:
            data = json.loads(script.string)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "School":
            return data
    return {}


def format_postal_address(address: dict[str, Any]) -> str:
    street = clean_text(str(address.get("streetAddress", "")))
    city = clean_text(str(address.get("addressLocality", "")))
    region = clean_text(str(address.get("addressRegion", "")))
    postal = clean_text(str(address.get("postalCode", "")))
    parts = [street]
    city_line = ", ".join(part for part in (city, f"{region} {postal}".strip()) if part)
    if city_line:
        parts.append(city_line)
    return clean_text(", ".join(parts))


def parse_website(soup: BeautifulSoup) -> str:
    blocked_domains = (
        "privateschoolreview.com",
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "youtube.com",
        "linkedin.com",
        "google.com",
        "myschoolapp.com",
        "nces.ed.gov",
    )

    for anchor in soup.select("a[href^='http']"):
        href = anchor.get("href", "")
        text = clean_text(anchor.get_text())
        if any(domain in href for domain in blocked_domains):
            continue
        lowered = text.lower()
        if lowered in {"visit website", "website", "school website", "view website"}:
            return normalize_website(href)
        if re.match(r"^(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}$", text, re.I):
            return normalize_website(href)

    h1 = soup.find("h1")
    if h1:
        for anchor in h1.find_all_next("a[href^='http']", limit=12):
            href = anchor.get("href", "")
            if any(domain in href for domain in blocked_domains):
                continue
            return normalize_website(href)
    return ""


def parse_description(soup: BeautifulSoup) -> str:
    data = parse_json_ld(soup)
    if data.get("description"):
        return clean_text(str(data["description"]))[:2000]

    h1 = soup.find("h1")
    if h1:
        for node in h1.find_all_next("p", limit=4):
            text = clean_text(node.get_text(" ", strip=True))
            if len(text) > 60:
                return text[:2000]

    meta = soup.select_one("meta[name='description']")
    if meta and meta.get("content"):
        return clean_text(meta["content"])[:2000]
    return ""


def parse_address_phone(soup: BeautifulSoup) -> tuple[str, str]:
    data = parse_json_ld(soup)
    address = ""
    phone = clean_text(str(data.get("telephone", "")))

    if isinstance(data.get("address"), dict):
        address = format_postal_address(data["address"])

    if not address:
        node = soup.select_one(".card-address .cr_content_wrapper, .card-address")
        if node:
            address = clean_text(node.get_text(" ", strip=True))

    if not phone:
        tel = soup.select_one("a[href^='tel:']")
        if tel:
            phone = clean_text(tel.get_text()) or clean_text(tel["href"].replace("tel:", ""))

    if address:
        address, parsed_phone = split_address_phone(address)
        phone = phone or parsed_phone

    return address, phone


def parse_city_from_address(address: str, fallback: str) -> str:
    if not address:
        return fallback
    match = re.search(r",\s*([A-Za-z .'-]+),\s*[A-Z]{2}\s*\d{5}", address)
    if match:
        return clean_text(match.group(1))
    match = re.search(r"([A-Za-z .'-]+),\s*[A-Z]{2}\s*\d{5}", address)
    if match:
        city = clean_text(match.group(1))
        # Avoid capturing street fragments like "60th St New York".
        if not re.search(r"\b(st|street|ave|avenue|rd|road|blvd|lane|dr|drive)\b", city, re.I):
            return city
        parts = city.split()
        if len(parts) >= 2:
            return clean_text(" ".join(parts[-2:]))
    return fallback


def scrape_profile(profile_url: str, source_location: str, default_city: str) -> SchoolRecord:
    soup = fetch_html(profile_url)
    data = parse_json_ld(soup)
    h1 = soup.find("h1")
    name = clean_text(str(data.get("name", ""))) or (clean_text(h1.get_text()) if h1 else "")
    address, phone = parse_address_phone(soup)
    city = parse_city_from_address(address, default_city)
    record = SchoolRecord(
        school=name,
        city=city,
        website=parse_website(soup),
        description=parse_description(soup),
        verification_status=parse_verification_status(soup),
        address=address,
        phone=phone,
        profile_url=profile_url,
        source_location=source_location,
    )
    record.audit()
    return record


def scrape_location(location: str) -> tuple[list[SchoolRecord], str | None]:
    path = location_to_url_path(location)
    listing_url = absolute_url(f"/{path}")
    error = None
    records: list[SchoolRecord] = []

    try:
        profile_urls = collect_listing_urls(path)
    except Exception as exc:
        return [], f"Failed to load listing for '{location}' ({listing_url}): {exc}"

    if not profile_urls:
        return [], f"No schools found for '{location}' at {listing_url}"

    default_city = clean_text(location.split(",")[0])
    total = len(profile_urls)
    for index, profile_url in enumerate(profile_urls, start=1):
        try:
            if index == 1 or index % 25 == 0 or index == total:
                print(f"     scraping profile {index}/{total}")
            records.append(scrape_profile(profile_url, location, default_city))
        except Exception as exc:
            records.append(
                SchoolRecord(
                    school=profile_url.rsplit("/", 1)[-1].replace("-profile", "").replace("-", " ").title(),
                    city=default_city,
                    profile_url=profile_url,
                    source_location=location,
                    missing_fields=["School", "website", "description", "address", "phone"],
                )
            )
            error = f"Partial scrape for '{location}': {exc}"

    return records, error


def dedupe_records(records: Iterable[SchoolRecord]) -> tuple[list[SchoolRecord], list[str]]:
    unique: list[SchoolRecord] = []
    seen_keys: set[str] = set()
    duplicate_notes: list[str] = []

    for record in records:
        key = clean_text(record.school).lower()
        if not key:
            key = record.profile_url.lower()
        if key in seen_keys:
            duplicate_notes.append(
                f"Duplicate removed: {record.school} ({record.profile_url}) from {record.source_location}"
            )
            continue
        seen_keys.add(key)
        unique.append(record)

    return unique, duplicate_notes
