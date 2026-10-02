#!/usr/bin/env python3
"""
Explore – scrape a set of URLs and persist their HTML to a SQLite database.

Usage:
    python explore.py [--rate-limit SECONDS] [--db PATH] [--urls PATH] [--dry-run]

A configurable rate limit (in seconds) is enforced between requests.
By default it reads from urls.txt in the same directory and stores results
in prospector.db.
"""

import argparse
import os
import sys
import time
from pathlib import Path

from prospector.db import setup_db, persist_page

import requests

DEFAULT_URLS = os.path.join(os.path.dirname(__file__), "urls.txt")
DEFAULT_RATE_LIMIT = 2  # seconds between requests


def read_urls(urls_path: str) -> list[str]:
    """Read a urls.txt file, skipping blank lines and comments."""
    urls = []
    with open(urls_path, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                urls.append(stripped)
    return urls


def fetch_page(url: str) -> tuple[int | None, str | None, str | None]:
    """Fetch a URL and return (status_code, html, error)."""
    try:
        resp = requests.get(url, timeout=30, headers={
            "User-Agent": "datagovuk-prospector/0.1 (https://data.gov.uk)"
        })
        return resp.status_code, resp.text, None
    except requests.RequestException as exc:
        return None, None, str(exc)


def main():
    parser = argparse.ArgumentParser(description="Scrape URLs and persist to SQLite")
    parser.add_argument("--rate-limit", type=float, default=DEFAULT_RATE_LIMIT,
                        help="Seconds to wait between requests (default: 0.5)")
    parser.add_argument("--urls", type=str, default=DEFAULT_URLS,
                        help="Path to urls.txt (default: urls.txt in this dir)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only list URLs to be scraped, do not fetch")
    args = parser.parse_args()

    setup_db()

    urls = read_urls(args.urls)
    if not urls:
        print("No URLs found in", args.urls)
        sys.exit(0)

    print(f"Found {len(urls)} URL(s) to scrape")

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")

        if args.dry_run:
            continue

        status_code, html, error = fetch_page(url)

        if error:
            print(f"  ERROR: {error}")
        else:
            size = len(html) if html else 0
            print(f"  Status: {status_code}  HTML: {size} bytes")

        persist_page(url, status_code, html, error)

        # Rate limiting – skip delay after the last URL
        if i < len(urls):
            time.sleep(args.rate_limit)

    print("Done.")


if __name__ == "__main__":
    main()
