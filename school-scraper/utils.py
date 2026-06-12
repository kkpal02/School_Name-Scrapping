"""HTTP helpers for polite scraping."""

from __future__ import annotations

import re
import time
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import (
    BASE_URL,
    MAX_RETRIES,
    REQUEST_DELAY_SECONDS,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT_SECONDS,
)

_last_request_at = 0.0
_session: Optional[requests.Session] = None


def get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(REQUEST_HEADERS)
    return _session


def fetch_html(url: str) -> BeautifulSoup:
    global _last_request_at
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        elapsed = time.time() - _last_request_at
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)

        try:
            response = get_session().get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            _last_request_at = time.time()
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(REQUEST_DELAY_SECONDS * attempt)
            continue

    assert last_error is not None
    raise last_error


def absolute_url(path: str) -> str:
    return urljoin(BASE_URL, path)


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def split_address_phone(raw: str) -> tuple[str, str]:
    """Split a combined address/phone string from listing cards."""
    raw = clean_text(raw)
    if not raw:
        return "", ""

    phone_match = re.search(r"\((\d{3})\)\s*([\d-]+)", raw)
    if phone_match:
        phone = f"({phone_match.group(1)}) {phone_match.group(2)}"
        address = clean_text(raw[: phone_match.start()])
        return address, phone

    return raw, ""


def normalize_website(url: str) -> str:
    url = clean_text(url)
    if not url:
        return ""
    url = re.sub(r"^https?://", "", url, flags=re.I)
    return url.rstrip("/")
