import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from ollama import chat
from pydantic import BaseModel, Field

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


def extract_page_data(
    html_content: str, page_url: str
) -> dict:
    """Extracts download links and clean text deterministically from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html_content, "html.parser")

    # A. Extract direct data resource links deterministically
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

    # B. Extract clean main body text for LLM context
    for noise in soup(["script", "style", "nav", "footer", "header", "form"]):
        noise.decompose()

    main_content = (
        soup.find("main") or soup.find("div", id="content") or soup.body
    )
    clean_text = (
        main_content.get_text(separator="\n", strip=True) if main_content else ""
    )

    return {
        "text_content": "\n".join(clean_text.split("\n")[:100]),  # Top 100 lines
        "resources": extracted_resources,
    }


class CKANDatasetSchema(BaseModel):
    title: str = Field(description="A clean, concise dataset title.")
    description: str = Field(
        description="A clear summary of the dataset in Markdown. One or two paragraphs, but more are acceptible."
    )
    author: str = Field(
        description="The publishing organization or owner if mentioned, otherwise 'Unknown'."
    )


def process_dataset_with_llm(
    html_content: str, page_url: str, model_name: str = "qwen3.5:2b"
) -> CKANDatasetSchema:
    # Step 1: Deterministic extraction
    extracted_data = extract_page_data(html_content, page_url)

    # Step 2: Build prompt
    prompt = f"""
Analyze the following webpage content and extracted data resources.
Synthesize a title, description, author.

Source URL: {page_url}

Page Text:
```
{extracted_data['text_content']}
```
"""

    print(f"Prompt length: {len(prompt.split(" "))}")
    # Step 3: Call Ollama with Pydantic schema enforcement
    response = chat(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert open data cataloguer. "
                    "Analyze the input and return metadata adhering strictly to the required schema. "
                    "Never alter or fabricate resource URLs."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        format=CKANDatasetSchema.model_json_schema(),  # Enforces Pydantic schema constraints natively
        options={
            "temperature": 0.1, # Low temperature for factual precision
            "num_ctx": 4096,  # Cap context size
            "num_thread": 8,  # Match CPU physical performance cores
        },
    )

    # Step 4: Validate JSON directly into Pydantic model
    response = CKANDatasetSchema.model_validate_json(response.message.content)
    dataset = response.model_dump()
    dataset["resources"] = extracted_data["resources"]
    return dataset
