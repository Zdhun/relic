# AuditAI Scanner Service

FastAPI backend for AuditAI.

## Endpoints
- `POST /scan`: Start a scan
- `GET /scan/{id}/events`: SSE stream
- `GET /scan/{id}`: Get result
- `GET /scan/{id}/report.pdf`: Download PDF

## Development
```bash
pip install poetry
poetry install
uvicorn app.main:app --reload
```

## Testing
```bash
pytest
ruff check .
```
