#!/usr/bin/env python3
"""
Sift – score every page in the SQLite database using calculate_dataset_score()
and persist the result to the dataset_score column.

Usage:
    python sift.py [--batch-size N] [--force]

Walks all rows in the pages table, runs the scoring function, and writes
back the score.  By default it skips pages that already have a score.
Use --force to re-score everything.
"""

import argparse
import sys

from prospector.db import get_connection, get_pages, setup_db, update_dataset_score
from prospector.scorer import calculate_dataset_score


DEFAULT_BATCH_SIZE = 100


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Score all pages in the prospector database"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of pages to process before printing progress (default: {DEFAULT_BATCH_SIZE})",
    )
    args = parser.parse_args()

    setup_db()

    pages = get_pages()
    if not pages:
        print("No pages found in the database.")
        return

    print(f"Found {len(pages)} page(s) to sift")

    scored = 0
    skipped = 0
    errors = 0

    for i, (url, status_code, html, error) in enumerate(pages, 1):
        # Pages without HTML content or that errored cannot be scored
        if not html or error:
            errors += 1
            if (i % args.batch_size) == 0 or i == len(pages):
                print(
                    f"  Progress: {i}/{len(pages)} "
                    f"(scored={scored}, skipped={skipped}, errors={errors})"
                )
            continue

        result = calculate_dataset_score(html, url)
        update_dataset_score(url, result["score"], result["matched_rules"])
        scored += 1

        if (i % args.batch_size) == 0 or i == len(pages):
            print(
                f"  Progress: {i}/{len(pages)} "
                f"(scored={scored}, skipped={skipped}, errors={errors})"
            )

    print(f"Done. scored={scored}, skipped={skipped}, errors={errors}")


if __name__ == "__main__":
    main()
