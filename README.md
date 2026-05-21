# TMDB Extraction Pipeline

A focused Python pipeline that extracts movie data from the [TMDB API](https://developer.themoviedb.org/docs) and lands it as raw JSON, ready for downstream transformation.

Built as a portfolio piece demonstrating production-grade API ingestion patterns without the overhead of a full orchestration framework.

## What it does

Paginates through a configurable TMDB endpoint (e.g. `movie/popular`, `movie/top_rated`, `tv/popular`), fetches all available results up to TMDB's 500-page limit, and writes the raw payload to `data/raw/docs.json`.

## Engineering decisions

**Retry logic with exponential backoff and jitter** — transient failures (429, 502, 503, 504) are retried automatically. Jitter is applied to prevent thundering-herd behaviour when multiple workers would otherwise retry in sync.

**Pagination cap** — TMDB's API returns up to ~57,000 total pages but silently errors beyond page 500. The pipeline caps pagination at 500 and logs clearly when the limit is reached, rather than running indefinitely or failing silently.

**Bearer token auth** — credentials are passed via `Authorization: Bearer` header rather than a query parameter, keeping secrets out of server access logs.

**Environment-driven configuration** — endpoint, base URL, and credentials are all env vars, making the pipeline portable across environments without code changes.

**Load env before import** — `load_dotenv()` is called before importing the extraction module so that module-level `os.getenv()` calls resolve correctly.

## Project structure

```
.
├── src/
│   ├── extract.py      # pagination, retry logic, auth
│   └── main.py         # entrypoint
├── tests/
│   └── test_extract.py # unit tests with mocked HTTP
├── data/
│   └── raw/            # landing zone for extracted JSON
├── .env.example
└── requirements.txt
```

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your TMDB API Read Access Token to .env
```

## Running

```bash
python src/main.py
```

To extract a different endpoint, set `TMDB_ENDPOINT` in `.env`:

```
TMDB_ENDPOINT=movie/top_rated   # or tv/popular, movie/upcoming, etc.
```

## Tests

```bash
pytest tests/
```

All HTTP calls are mocked — no network access required. Tests cover happy path, multi-page pagination, transient error retry, and network failure retry.

## Stack

Python · requests · pytest · python-dotenv
