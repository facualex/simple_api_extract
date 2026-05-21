import json
import logging
import os
import random
import time

import requests

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = [429, 502, 503, 504]
TMDB_MAX_PAGE = 500  # TMDB does not serve results beyond page 500
BASE_URL = os.getenv("BASE_URL", "https://api.themoviedb.org/3")
API_KEY = os.getenv("API_KEY")


def _backoff_with_jitter(attempt: int, base: float = 2.0, cap: float = 60.0) -> float:
    return random.uniform(0, min(cap, base**attempt))


def fetch_page(endpoint: str, page: int, max_retries: int = 3) -> dict:
    params = {"page": page}

    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    url = f"{BASE_URL}/{endpoint.lstrip('/')}"

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code in RETRYABLE_STATUS_CODES:
                if attempt == max_retries - 1:
                    response.raise_for_status()

                retry_after = response.headers.get("Retry-After")
                wait = (
                    int(retry_after) if retry_after else _backoff_with_jitter(attempt)
                )

                logger.warning(
                    "Transient error %d on attempt %d/%d. Retrying in %.1fs.",
                    response.status_code,
                    attempt + 1,
                    max_retries,
                    wait,
                )

                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException:
            if attempt == max_retries - 1:
                raise

            wait = _backoff_with_jitter(attempt)

            logger.warning(
                "Network error on attempt %d/%d. Retrying in %.1fs.",
                attempt + 1,
                max_retries,
                wait,
            )

            time.sleep(wait)


def fetch_all_pages(
    endpoint: str,
    page_delay: float = 0.5,
) -> list[dict]:
    """Fetch all pages for a given TMDB endpoint, returning a flat list of records."""
    all_results = []
    page = 1

    while True:
        logger.info("Fetching page %d for endpoint '%s'.", page, endpoint)

        data = fetch_page(endpoint=endpoint, page=page)
        results = data.get("results", [])
        total_pages = min(data.get("total_pages", 1), TMDB_MAX_PAGE)

        if not results:
            logger.info("No results on page %d. Extraction complete.", page)
            break

        all_results.extend(results)
        logger.info(
            "Page %d/%d: %d records fetched. Total so far: %d.",
            page,
            total_pages,
            len(results),
            len(all_results),
        )

        if page >= total_pages:
            logger.info("Last page reached (%d). Extraction complete.", page)
            break

        page += 1
        time.sleep(page_delay)

    return all_results


def extract() -> tuple[str, str]:
    endpoint = os.getenv("TMDB_ENDPOINT", "movie/popular")
    docs = fetch_all_pages(endpoint=endpoint)

    raw_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "docs.json")
    raw_path = os.path.abspath(raw_path)

    with open(raw_path, "w") as f:
        json.dump(docs, f)

    logger.info("Saved %d docs to %s.", len(docs), raw_path)

    return raw_path, BASE_URL
