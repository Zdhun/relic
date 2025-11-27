# AuditAI - AI-Assisted Web Security Auditor

AuditAI is a professional-grade security auditing tool featuring a terminal-style web console and a powerful backend scanner.
It simulates security scans with real-time log streaming via SSE and generates executive PDF reports.

## Features
- **Live Terminal Console**: Real-time log streaming using Server-Sent Events (SSE).
- **Executive Summary**: Instant PDF generation with scoring and risk assessment.
- **Safe-by-Default**: Strict policy controls (localhost/private only by default).
- **Modern Stack**: Next.js App Router, FastAPI, Docker Compose, Turborepo.

## Quickstart

### Prerequisites
- Node.js (LTS) & pnpm
- Python 3.10+ & Poetry (or pip)
- Docker & Docker Compose

### Running with Docker (Recommended)
```bash
docker compose up --build
```
Access the UI at http://localhost:3000

### Local Development
1. **Frontend**:
   ```bash
   cd apps/web
   pnpm install
   pnpm dev
   ```
2. **Backend**:
   ```bash
   cd services/scanner
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```

## Structure
- `apps/web`: Next.js frontend (BFF + UI)
- `services/scanner`: FastAPI backend (Scanner engine)

## Legal
**AUTHORIZED TARGETS ONLY.**
This tool is for educational and authorized auditing purposes only.

## Roadmap
- [ ] Real HTTP/Network scanning implementation
- [ ] LLM integration for vulnerability analysis
