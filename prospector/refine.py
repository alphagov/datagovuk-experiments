#!/usr/bin/env python3
"""
Refine – run the LLM-based dataset metadata extractor on high-scoring pages.

Usage:
    python refine.py [--limit N] [--output PATH] [--model NAME]

Walks all pages in the database with a dataset_score >= 0.4 (i.e.
is_dataset=True from the scorer) and calls process_dataset_with_llm()
on each one.  Results are appended as JSON lines to an output file.

By default the output file is refinements.jsonl in the same directory as
the prospector module.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from ollama import chat
from pydantic import BaseModel, Field, ValidationError

from prospector.db import get_high_scoring_pages

DATA_EXTENSIONS = (
    ".csv",
    ".xlsx",
    ".xls",
    ".ods",
    ".json",
    ".geojson",
    ".xml",
    ".zip",
    ".rdf",
    ".parquet",
    ".tsv",
)


class CKANDatasetSchema(BaseModel):
    title: str = Field(description="A clean, concise dataset title.")
    description: str = Field(
        description="A clear summary of the dataset in Markdown. One or two paragraphs, but more are acceptible."
    )


def extract_page_data(
    html_content: str, page_url: str
) -> dict:
    """Extracts download links and clean text deterministically from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html_content, "html.parser")

    extracted_resources = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        clean_href = href.split("?")[0].split("#")[0].lower()

        if any(clean_href.endswith(ext) for ext in DATA_EXTENSIONS):
            full_url = urljoin(page_url, href)

            if full_url not in seen_urls:
                seen_urls.add(full_url)
                ext = clean_href.split(".")[-1].upper()
                raw_text = a.get_text(strip=True) or f"{ext} File"

                extracted_resources.append(
                    {"raw_label": raw_text, "url": full_url, "format": ext}
                )

    for noise in soup(["script", "style", "nav", "footer", "header", "form"]):
        noise.decompose()

    main_content = (
        soup.find("main") or soup.find("div", id="content") or soup.body
    )
    clean_text = (
        main_content.get_text(separator="\n", strip=True) if main_content else ""
    )

    return {
        "text_content": "\n".join(clean_text.split("\n")[:100]),
        "resources": extracted_resources,
    }


def process_dataset_with_llm(
    html_content: str, page_url: str, model_name: str = "qwen3.5:2b"
) -> dict:
    """Extract structured dataset metadata from HTML using an LLM.

    Returns a dict with keys: title, description, resources.
    """
    extracted_data = extract_page_data(html_content, page_url)

    prompt = f"""
Analyze the following webpage content.
Synthesize a title and then a description - separate the two with '==='.

Source URL: {page_url}

Page Text:
```
{extracted_data['text_content']}
```
"""

    response = chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert open data cataloguer. "
                    "Analyze the input and respond only with the content requested; no pleasantries, pre-ambles or qualifiers."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        options={
            "temperature": 0.1,
            "num_ctx": 16000,
            "num_thread": 8,
        },
    )

    raw_title, raw_description = response.message.content.split("===")
    dataset = {
        "title": raw_title.strip(),
        "description": raw_description.strip(),
        "resources": extracted_data["resources"],
    }
    return dataset


DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "refinements.jsonl")
DEFAULT_MODEL = "qwen3.5:4b"
DEFAULT_THRESHOLD = 0.4


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refine high-scoring pages with LLM-based metadata extraction"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of datasets to process (default: unlimited)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT,
        help=f"Output JSONL file path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Ollama model name (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    pages = get_high_scoring_pages(threshold=DEFAULT_THRESHOLD, limit=args.limit)
    if not pages:
        print("No high-scoring datasets found (score >= " + str(DEFAULT_THRESHOLD) + ").")
        return

    print(f"Found {len(pages)} dataset(s) with score >= {DEFAULT_THRESHOLD}")

    processed = 0
    errors = 0

    with open(args.output, "a", encoding="utf-8") as out:
        for i, (url, html) in enumerate(pages, 1):
            print(f"[{i}/{len(pages)}] {url}")
            try:
                start = time.time()
                dataset = process_dataset_with_llm(html, url, model_name=args.model)
                record = {
                    "url": url,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    **dataset,
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n")
                processed += 1
                took = time.time() - start
                print(f"  -> {record['title']} (took {took}S)")
            except Exception as exc:
                errors += 1
                print(f"  ERROR: {exc}")

    print(f"Done. processed={processed}, errors={errors}, output={args.output}")


if __name__ == "__main__":
    main()
