# DocProcessing API — v1.1.0

FastAPI backend for processing batch PDFs containing multiple concatenated documents. Features **dual-pipeline PO extraction** (Pipeline A: LLM, Pipeline B: Regex + LLM fallback), **multi-PO support**, **supplier-aware filtering**, **automatic reconciliation**, **PDF splitting**, and **Excel indexation**.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Running the Backend](#running-the-backend)
5. [Running Tests](#running-tests)
6. [API Endpoints](#api-endpoints)
7. [Processing Flow](#processing-flow)
8. [Project Structure](#project-structure)
9. [PO Extraction Logic](#po-extraction-logic)
10. [Deployment](#deployment)

---

## Prerequisites

- **Python 3.11+** (tested with 3.12)
- **pip** (Python package manager)
- **Redis** (optional — only needed for async job queue; falls back to sync mode without it)

---

## Installation

```bash
# 1. Navigate to the project directory
cd version_1.1.0

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / Mac

# 3. Install dependencies
pip install -r requirements.txt
```

### Dependencies

| Package            | Purpose                              |
|--------------------|--------------------------------------|
| `fastapi`          | Web framework                        |
| `uvicorn`          | ASGI server                          |
| `pypdf`            | PDF text extraction                  |
| `openpyxl`         | Excel file generation                |
| `openai`           | OpenAI API client (LLM pipelines)    |
| `pydantic-settings`| Configuration management             |
| `python-dotenv`    | .env file loading                    |
| `structlog`        | Structured logging                   |
| `python-multipart` | File upload handling                 |
| `rq` + `redis`     | Async job queue (optional)           |
| `pytest` + `httpx` | Testing                              |

---

## Configuration

```bash
# Copy the example and fill in your values
copy .env.example .env
```

Edit `.env` with your settings:

| Variable                   | Default                     | Required | Description                             |
|----------------------------|-----------------------------|----------|-----------------------------------------|
| `OPENAI_API_KEY`           | —                           | **Yes**  | OpenAI API key for LLM pipelines        |
| `OPENAI_MODEL`             | `gpt-4.1`                  | No       | Model for Pipeline A                    |
| `PIPELINE_B_FALLBACK_MODEL`| `gpt-4.1-mini`             | No       | Fallback model for Pipeline B           |
| `MIN_CONFIDENCE`           | `0.6`                      | No       | Minimum confidence threshold            |
| `ALLOW_LEADING_ZERO_EQUIV` | `true`                     | No       | Treat 0XXXXXXX ≡ XXXXXXX as equivalent |
| `STORAGE_BASE_PATH`        | `data/`                    | No       | Base directory for uploads/outputs      |
| `REDIS_URL`                | `redis://localhost:6379/0`  | No       | Redis connection (async mode)           |
| `API_HOST`                 | `0.0.0.0`                  | No       | Server bind address                     |
| `API_PORT`                 | `8000`                     | No       | Server port                             |

> **Note**: If `OPENAI_API_KEY` is not set, Pipeline A (LLM) will be skipped and only Pipeline B (regex) will run.

---

## Running the Backend

### Development (with auto-reload)

```bash
# Activate your virtual environment first
venv\Scripts\activate

# Start the server (default port 8000)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or use a custom port (e.g., 500):

```bash
# Windows PowerShell
$env:API_PORT="500"; python -m uvicorn app.main:app --host 0.0.0.0 --port 500 --reload

# Linux / Mac
API_PORT=500 uvicorn app.main:app --host 0.0.0.0 --port 500 --reload
```

### Production

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verify it's running

```bash
curl http://localhost:8000/health
# → {"status":"healthy"}
```

API documentation (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend (optional)

The `frontend/` folder contains a standalone HTML/CSS/JS interface that connects to the API. Simply open `frontend/index.html` in a browser or serve it via any static file server. The frontend expects the API at the same host/port.

### Async Worker (optional)

If Redis is available, start the RQ worker for background processing:

```bash
python -m app.worker
```

> Without Redis, the `/v1/process` endpoint falls back to synchronous execution in a background thread.

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Quick summary
pytest tests/ -q
```

Current test suite: **49 tests** covering PO regex extraction, keyword matching, and reconciliation logic.

---

## API Endpoints

### File Management

| Method | Endpoint                   | Description                        |
|--------|----------------------------|------------------------------------|
| `POST` | `/v1/files`                | Upload a batch PDF                 |

### Extraction

| Method | Endpoint                         | Description                              |
|--------|----------------------------------|------------------------------------------|
| `POST` | `/v1/extract/text`               | Extract text per page                    |
| `POST` | `/v1/extract/boundaries`         | Detect document boundaries (page ranges) |
| `POST` | `/v1/extract/po?pipeline=A\|B`   | Extract PO numbers via specified pipeline|

### Reconciliation & Processing

| Method | Endpoint                  | Description                                |
|--------|---------------------------|--------------------------------------------|
| `POST` | `/v1/reconcile/po`        | Reconcile Pipeline A vs B results          |
| `POST` | `/v1/process`             | Full end-to-end processing flow            |
| `GET`  | `/v1/jobs/{job_id}`       | Check async job status                     |

### Output

| Method | Endpoint                           | Description                     |
|--------|------------------------------------|---------------------------------|
| `POST` | `/v1/split`                        | Split PDF by detected ranges    |
| `GET`  | `/v1/split/download/{file_id}`     | Download split PDFs as ZIP      |
| `POST` | `/v1/export/excel`                 | Generate Excel index            |
| `GET`  | `/v1/export/excel/{file_id}`       | Download Excel file             |

### Review & Document Management

| Method  | Endpoint                    | Description                  |
|---------|-----------------------------|------------------------------|
| `POST`  | `/v1/rejects`               | Create reject record         |
| `POST`  | `/v1/rejects/resolve`       | Resolve a reject             |
| `GET`   | `/v1/rejects`               | List rejects                 |
| `PUT`   | `/v1/documents/{doc_id}`    | Update document (PO override)|

### Health

| Method | Endpoint   | Description  |
|--------|------------|--------------|
| `GET`  | `/health`  | Health check |

---

## Processing Flow

The `/v1/process` endpoint orchestrates the full pipeline:

```
Upload PDF
    │
    ▼
01. Text Extraction (pypdf + OCR fallback)
    │
    ▼
02. Boundary Detection (page-range splitting)
    │
    ▼
03. Pipeline A — LLM Extraction (OpenAI)
    │
    ▼
04. Pipeline B — Regex Extraction (+ LLM fallback)
    │
    ▼
05. Reconciliation (A vs B comparison)
    │
    ├── MATCH_OK (100% agreement) → AUTO_OK
    ├── Partial match             → SEND_TO_REVIEW
    ├── Mismatch                  → SEND_TO_REVIEW
    └── No PO found               → SEND_TO_REVIEW
    │
    ▼
06. PDF Splitting (individual docs)
    │
    ▼
07. Excel Index Generation
```

### Reconciliation Rules

- **MATCH_OK / AUTO_OK**: Both pipelines must agree on **100% of all PO numbers** (full set equality).
- **Partial Match → REVIEW**: Pipelines share some POs but not all.
- **Mismatch → REVIEW**: Both found POs but none overlap.
- **Single Pipeline → REVIEW**: Only one pipeline returned results.

---

## Project Structure

```
version_1.1.0/
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
├── README.md                 # This file
│
├── app/                      # Backend application
│   ├── main.py               # FastAPI entry point + CORS + static files
│   ├── config.py             # Settings (from .env via pydantic-settings)
│   ├── worker.py             # RQ worker entrypoint
│   │
│   ├── routers/              # API endpoint handlers
│   │   ├── files.py          #   POST /v1/files
│   │   ├── extract.py        #   POST /v1/extract/{text,boundaries,po}
│   │   ├── reconcile.py      #   POST /v1/reconcile/po
│   │   ├── process.py        #   POST /v1/process (full flow)
│   │   ├── jobs.py           #   GET  /v1/jobs/{id}
│   │   ├── split.py          #   POST /v1/split, GET download
│   │   ├── export.py         #   POST/GET /v1/export/excel
│   │   ├── documents.py      #   PUT  /v1/documents/{id}
│   │   └── rejects.py        #   CRUD /v1/rejects
│   │
│   ├── services/             # Core business logic
│   │   ├── text_extraction.py    # PDF → text (pypdf + OCR)
│   │   ├── boundary_detection.py # Document boundary detection
│   │   ├── po_extraction.py      # Regex PO extraction + supplier filtering
│   │   ├── pipeline_a.py         # Pipeline A (LLM-first)
│   │   ├── pipeline_b.py         # Pipeline B (regex + LLM fallback)
│   │   ├── openai_client.py      # OpenAI API client
│   │   ├── pdf_splitter.py       # PDF splitting
│   │   └── excel_export.py       # Excel generation
│   │
│   ├── schemas/              # Pydantic data models
│   │   ├── common.py         #   PipelineResult, DocumentRecord
│   │   ├── extraction.py     #   Extraction request/response
│   │   ├── files.py          #   File upload models
│   │   ├── jobs.py           #   Job status models
│   │   ├── reconciliation.py #   Reconciliation models
│   │   └── rejects.py        #   Reject management models
│   │
│   ├── reconcile/            # Reconciliation engine
│   │   ├── engine.py         #   A vs B comparison logic
│   │   └── po_normalizer.py  #   PO normalization & equivalence
│   │
│   ├── storage/              # File system operations
│   │   ├── local.py          #   Local filesystem storage
│   │   └── job_store.py      #   Job state persistence
│   │
│   └── workers/              # Background task definitions
│       └── tasks.py          #   Full processing orchestration
│
├── frontend/                 # Web UI (standalone HTML/CSS/JS)
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── tests/                    # Test suite (49 tests)
│   ├── test_po_regex.py      #   PO pattern extraction tests
│   ├── test_keywords.py      #   Keyword matching tests
│   └── test_reconcile.py     #   Reconciliation logic tests
│
└── data/                     # Runtime data (auto-created)
    ├── uploads/              #   Uploaded PDFs
    ├── outputs/{file_id}/    #   Processing results
    │   ├── docs/             #     Split PDFs
    │   ├── index.xlsx        #     Excel index
    │   ├── artifacts/        #     Intermediate JSON results
    │   └── job.json          #     Job state
    └── rejects/              #   Review queue
```

---

## PO Extraction Logic

### Supported PO Patterns

| Pattern        | Format         | Example    |
|----------------|----------------|------------|
| 5XXXXXXX       | 8 digits       | 53681855   |
| 8XXXXXXX       | 8 digits       | 80001234   |
| 2XXXXXXX       | 8 digits       | 20001234   |
| 0XXXXXXX       | 8 digits       | 00001234   |
| 4XXX–4XXXXXXX  | 4–8 digits     | 41234      |
| 2XXXX–2XXXXX   | 5–6 digits     | 21234      |

### Supplier-Aware Filtering

Certain suppliers have specific rules to prevent false positives:

| Supplier                        | Rule                                          |
|---------------------------------|-----------------------------------------------|
| INDUSTRIAS TAYG S.L.            | PO must be ≥ 8 digits (rejects 6-digit codes) |

### Negative Context Filtering

Numbers preceded by these labels are automatically excluded from PO results:

`Cliente`, `Client`, `Customer`, `Kundennummer`, `GLN`, `NIF`, `IBAN`, `SWIFT`, `Cuenta`, `Código bancário`, `HRB`, `VAT number`

### Article Code Protection

Numbers immediately preceded by a letter (e.g., **R**56481001) are rejected. This prevents product/article codes from being misidentified as POs.

---

## Deployment

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY frontend/ ./frontend/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

```bash
docker build -t docprocessing .
docker run -p 8080:8080 --env-file .env docprocessing
```

### Cloud Storage

Replace `app/storage/local.py` with a cloud-backed implementation (e.g., GCS, S3). The interface uses the same function signatures: `save_upload()`, `get_upload_path()`, etc.

### Scaling

- API and worker scale independently
- Use multiple RQ workers for parallel processing
- Consider Cloud Tasks or Pub/Sub for production job queues

---

## Data Directory Structure

The `data/` directory is created automatically at runtime. To reset all processing data:

```bash
# Windows
Remove-Item -Recurse -Force data\

# Linux / Mac
rm -rf data/
```

---

**Version**: 1.1.0  
**Last Updated**: 2026-02-22
