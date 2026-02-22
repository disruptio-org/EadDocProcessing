# DocProcessing API

Production-ready FastAPI backend for processing batch PDFs containing multiple concatenated documents. Features **dual-pipeline PO extraction** (Pipeline A: LLM-first, Pipeline B: hybrid regex+LLM), **automatic reconciliation**, **PDF splitting**, and **Excel indexation**.

## Features

- **PDF Upload & Storage** — Upload batch PDFs with UUID-based filing
- **Document Boundary Detection** — Heuristic-based page-level splitting (supports PT/EN/DE/FR/ES pagination markers)
- **Dual Pipeline PO Extraction**:
  - **Pipeline A**: LLM-first (flexible, robust) via OpenAI Responses API
  - **Pipeline B**: Regex-first + LLM fallback (conservative)
- **A/B Reconciliation** — Automatic match/mismatch/review classification
- **PDF Splitting** — Individual PDFs per detected document
- **Excel Export** — Full indexation with A/B results, match status, decision
- **Reject Queue** — Review management for mismatches and low-confidence
- **Async Processing** — RQ-based job queue with progress tracking

## Quick Start

### 1. Install Dependencies

```bash
cd DocProcessing
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
# Edit .env with your OPENAI_API_KEY
```

### 3. Run the API Server

```bash
uvicorn app.main:app --reload --port 8000
```

The API docs are available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. (Optional) Run the RQ Worker

Requires Redis running locally:

```bash
python -m app.worker
```

> **Note**: If Redis is not available, the `/v1/process` endpoint falls back to synchronous execution in a background thread (dev mode).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/files` | Upload a batch PDF |
| `POST` | `/v1/extract/text` | Extract text per page |
| `POST` | `/v1/extract/boundaries` | Detect document boundaries |
| `POST` | `/v1/extract/po?pipeline=A\|B` | Extract PO numbers |
| `POST` | `/v1/reconcile/po` | Reconcile A vs B results |
| `POST` | `/v1/split` | Split PDF by ranges |
| `POST` | `/v1/export/excel` | Generate index Excel |
| `GET`  | `/v1/export/excel/{id}` | Download Excel file |
| `POST` | `/v1/process` | Full async processing flow |
| `GET`  | `/v1/jobs/{job_id}` | Check job status |
| `POST` | `/v1/rejects` | Create reject record |
| `POST` | `/v1/rejects/resolve` | Resolve a reject |
| `GET`  | `/v1/rejects` | List rejects |
| `GET`  | `/health` | Health check |

## Example Requests (cURL)

### Upload a PDF

```bash
curl -X POST http://localhost:8000/v1/files \
  -F "file=@batch_document.pdf"
```

Response:
```json
{
  "source_file_id": "a1b2c3d4-...",
  "filename": "batch_document.pdf",
  "page_count": 42,
  "size_bytes": 1234567
}
```

### Process (Full Dual Pipeline Flow)

```bash
curl -X POST http://localhost:8000/v1/process \
  -H "Content-Type: application/json" \
  -d '{"source_file_id": "a1b2c3d4-...", "mode": "dual"}'
```

Response:
```json
{
  "job_id": "e5f6g7h8-...",
  "source_file_id": "a1b2c3d4-...",
  "status": "PENDING",
  "progress": 0.0,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### Check Job Status

```bash
curl http://localhost:8000/v1/jobs/e5f6g7h8-...
```

### Download Excel Output

```bash
curl -O http://localhost:8000/v1/export/excel/a1b2c3d4-...
```

### List Rejects

```bash
curl "http://localhost:8000/v1/rejects?source_file_id=a1b2c3d4-..."
```

### Detect Boundaries (standalone)

```bash
curl -X POST http://localhost:8000/v1/extract/boundaries \
  -H "Content-Type: application/json" \
  -d '{"source_file_id": "a1b2c3d4-..."}'
```

### Extract PO with Pipeline B

```bash
curl -X POST "http://localhost:8000/v1/extract/po?pipeline=B" \
  -H "Content-Type: application/json" \
  -d '{
    "source_file_id": "a1b2c3d4-...",
    "ranges": [{"start_page": 0, "end_page": 3}]
  }'
```

## Running Tests

```bash
pytest tests/ -v
```

## File Structure

```
data/
  uploads/{source_file_id}.pdf
  outputs/{source_file_id}/
    docs/{doc_id}.pdf            # Split documents
    index.xlsx                   # Excel index
    artifacts/                   # Intermediate results
      text_extraction.json
      boundaries.json
      extract_A.json
      extract_B.json
      reconcile.json
    job.json                     # Job state
  rejects/
    {reject_id}.json             # Review cases
```

## Project Structure

```
app/
  main.py                  # FastAPI entry point
  config.py                # Settings from .env
  worker.py                # RQ worker entrypoint
  routers/                 # API route handlers
    files.py, extract.py, reconcile.py, split.py,
    export.py, process.py, jobs.py, rejects.py
  services/                # Business logic
    text_extraction.py     # PDF text extraction (pypdf)
    boundary_detection.py  # Document boundary detection
    po_extraction.py       # Keywords + regex PO extraction
    pipeline_a.py          # LLM-first pipeline
    pipeline_b.py          # Hybrid regex+LLM pipeline
    openai_client.py       # OpenAI Responses API client
    pdf_splitter.py        # PDF splitting
    excel_export.py        # Excel generation
  schemas/                 # Pydantic models
  reconcile/               # A vs B reconciliation engine
  storage/                 # Filesystem + job persistence
  workers/                 # Async task definitions
tests/
  test_po_regex.py
  test_reconcile.py
  test_keywords.py
```

## Production Notes

### Cloud Storage (GCS)
Replace `app/storage/local.py` with a GCS-backed implementation. The interface is the same — `save_upload()`, `get_upload_path()`, etc.

### Cloud Run / Docker
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Redis for Production
Use Cloud Memorystore (Redis) or a managed Redis instance. Configure `REDIS_URL` in `.env`.

### Scaling
- The API and worker can scale independently
- Use multiple RQ workers for parallel document processing
- Consider Cloud Tasks or Pub/Sub for production job queues

## Configuration Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required for LLM) |
| `OPENAI_MODEL` | `gpt-4.1` | Primary model for Pipeline A |
| `PIPELINE_B_FALLBACK_MODEL` | `gpt-4.1-mini` | Fallback model for Pipeline B |
| `MIN_CONFIDENCE` | `0.6` | Minimum confidence threshold |
| `ALLOW_LEADING_ZERO_EQUIV` | `true` | Leading-zero PO equivalence |
| `STORAGE_BASE_PATH` | `data/` | Base storage directory |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
