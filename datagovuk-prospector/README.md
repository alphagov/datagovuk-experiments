# Datagovuk Prospector

At the moment we have two ways to add new datasets to data.gov.uk; publishers add datasets manually through their publisher accounts or they set up ckan harvest sources for our ckan instance to harvest on a regular beat.

This project aims to explore a new way for us to discover public open data across government and add it to data.gov.uk.

## Concept

### Explore

Scrape/spider web pages (from a certain allow list of domains) and persist their content to a datastore

### Sift

Identify pages that have a high probability of containing meaningful datasets - probably old fashioned heuristics + scoring.

### Refine

Enrich and explain datasets for consumption by users - take high scoring pages to an LLM to get potential datasets/resources.


## Developing locally

Install python requirements

```bash
uv venv --python 3.12
uv sync
```

Load sample gov.uk pages in to a local sqlite DB;

```bash
uv run python prospector/explore.py
```

Assign scores to pages in the sqlite DB:

```bash
uv run prospector/sift.py
```

Refine in to datasets that can be ingested in to data.gov.uk;

```bash
ollama pull qwen3.5:4b
uv run python prospector/refine.py
```

Load resulting refinements.jsonl in to data.gov.uk (within datagovuk repo);
https://github.com/alphagov/datagovuk/blob/firebreak-datagovuk-prospector/datagovuk/directory/management/commands/ingest_datasets.py

```bash
just bash
python manage.py ingest_datasets --datasets-file refinements.jsonl
```
