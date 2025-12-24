# AuditAI Scanner Service

FastAPI backend for AuditAI.

## Endpoints
- `POST /scan`: Start a scan
- `GET /scan/{id}/events`: SSE stream
- `GET /scan/{id}`: Get result
- `GET /scan/{id}/report.pdf`: Download PDF

## AI Prompts

AI system prompts are stored as versioned text files in `app/ai/prompts/`:
- `security_report_system_v1.txt` — Main security report prompt (French output)

To modify prompts:
1. Create a new version file (e.g., `security_report_system_v2.txt`)
2. Update `SECURITY_REPORT_PROMPT_NAME` in `routes.py` to use the new version
3. Keep old versions for rollback capability

Prompts are cached in-memory. Use `clear_cache()` from `prompt_loader` during development.

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
