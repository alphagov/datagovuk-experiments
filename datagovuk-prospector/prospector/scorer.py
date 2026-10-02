import json
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


def calculate_dataset_score(html_content: str, url: str) -> dict:
    """Calculates a confidence score (0.0 to 1.0) indicating whether an HTML page
    from any domain represents a dataset compatible with open data standards.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    score = 0.0
    matches = []
    extracted_resources = []

    # ----------------------------------------------------
    # Rule 1: Direct File Attachments / Data Extensions
    # ----------------------------------------------------
    data_extensions = (
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
        ".netcdf",
        ".nc",
        ".shp",
    )

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        clean_href = href.split("?")[0].split("#")[0].lower()

        if any(clean_href.endswith(ext) for ext in data_extensions):
            full_url = urljoin(url, href)
            ext = clean_href.split(".")[-1].upper()
            extracted_resources.append(
                {
                    "name": a.get_text(strip=True) or f"{ext} Resource",
                    "url": full_url,
                    "format": ext,
                }
            )

    if extracted_resources:
        score += 0.3
        matches.append(
            f"Found {len(extracted_resources)} downloadable data resources"
        )

    # ----------------------------------------------------
    # Rule 2: Standard Schema.org / JSON-LD Metadata
    # ----------------------------------------------------
    # Any open data portal using standard web semantics (Schema.org/Dataset)
    has_schema_dataset = False
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            # Handle single object or array of objects
            items = data if isinstance(data, list) else [data]
            for item in items:
                item_type = item.get("@type", "")
                if item_type == "Dataset" or (
                    isinstance(item_type, list) and "Dataset" in item_type
                ):
                    has_schema_dataset = True
                    break
        except (json.JSONDecodeError, TypeError):
            continue

    if has_schema_dataset:
        score += 0.2
        matches.append("Schema.org/Dataset JSON-LD metadata present")

    # ----------------------------------------------------
    # Rule 3: HTML Data Table Density
    # ----------------------------------------------------
    tables = soup.find_all("table")
    total_numeric_cells = 0

    for table in tables:
        cells = [td.get_text(strip=True) for td in table.find_all(["td", "th"])]
        # Count cells containing numerical figures
        total_numeric_cells += sum(
            1 for cell in cells if re.search(r"\b\d+(\.\d+)?\b", cell)
        )

    if total_numeric_cells >= 10:
        score += 0.1
        matches.append(
            f"High-density data tables found ({total_numeric_cells} numeric cells)"
        )

    # ----------------------------------------------------
    # Rule 4: Open Licensing References
    # ----------------------------------------------------
    # Look for generic open data licenses (Creative Commons, OGL, Open Database License, etc.)
    license_patterns = r"(creative\s*commons|cc-by|open\s*government\s*licence|ogl|opendatacommons|odbl|public\0domain)"

    has_license_link = soup.find(
        "a", href=re.compile(license_patterns, re.IGNORECASE)
    )
    has_license_text = re.search(license_patterns, html_content, re.IGNORECASE)

    if has_license_link or has_license_text:
        score += 0.2
        matches.append("Open data license or terms reference detected")

    # ----------------------------------------------------
    # Rule 5: Generic Title & Heading Keywords
    # ----------------------------------------------------
    h1 = soup.find("h1")
    title_tag = soup.find("title")

    header_text = (h1.get_text() if h1 else "") + " " + (
        title_tag.get_text() if title_tag else ""
    )
    keywords = (
        "dataset",
        "data set",
        "open data",
        "statistics",
        "time series",
        "data dictionary",
        "raw data",
        "microdata",
    )

    if any(kw in header_text.lower() for kw in keywords):
        score += 0.2
        matches.append("Dataset keywords present in page title/H1")

    # Final score normalization
    final_score = round(min(score, 1.0), 2)

    return {
        "url": url,
        "score": final_score,
        "is_dataset": final_score >= 0.40,
        "resources": extracted_resources,
        "matched_rules": matches,
    }
