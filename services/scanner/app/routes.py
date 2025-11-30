import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from .models import ScanRequest, ScanResponse, ScanResult, ScanLog, Finding
from . import store
from .policy import is_authorized
from .sse import event_generator
from .pdf import generate_pdf, generate_markdown, generate_ai_pdf
from .ai.schema import build_ai_scan_view
from .config import settings
import json

AI_REPORT_SYSTEM_PROMPT = """
You are a senior web security auditor. You receive a normalized JSON object describing the result of a web security scan (network exposure, TLS, headers, CORS, discovery, findings, performance, etc.).

Your job is to transform this technical scan into a concise but professional security summary, in FRENCH, targeting:
- a technical audience (developers / security engineers),
- and a non-technical decision-maker (CTO / product owner) who wants to quickly understand the risk.

CRITICAL CONSTRAINTS:
- You MUST output STRICT JSON.
- Do NOT include any markdown, code fences, comments, or explanations outside the JSON.
- Do NOT change the JSON SCHEMA.
- Do NOT invent vulnerabilities that are not supported by the input.
- If some information is missing in the input, do NOT hallucinate: just focus on what is given.

OUTPUT SCHEMA (MANDATORY):

{
  "global_score": {
    "letter": "A | B | C | D | E | F",
    "numeric": 0-100
  },
  "overall_risk_level": "Très faible | Faible | Moyen | Élevé | Critique",
  "executive_summary": "Texte en français, 3 à 6 phrases, paragraphe unique.",
  "top_3_vulnerabilities": [
    {
      "title": "Titre court de la vulnérabilité",
      "severity": "low | medium | high | critical",
      "area": "TLS | Headers | CORS | Network | Cookies | Application | Authentication | Configuration",
      "explanation_simple": "Explication en français, 1 à 3 phrases, vulgarisées mais techniquement correctes.",
      "fix_recommendation": "Recommandation concrète en français, 1 à 3 phrases, orientées action (ce que l'équipe doit faire)."
    }
  ],
  "site_map": {
    "total_pages": 0,
    "pages": ["url1", "url2"]
  },
  "infrastructure": {
    "hosting_provider": "Texte ou null",
    "tls_issuer": "Texte ou null",
    "server_header": "Texte ou null",
    "ip": "Texte ou null"
  },
  "model_name": "Nom du modèle IA utilisé"
}

DETAILED INSTRUCTIONS:

1) global_score
- If the input already contains a grade/score, REUSE it and map it consistently:
  - A ≈ 90-100
  - B ≈ 80-89
  - C ≈ 70-79
  - D ≈ 60-69
  - E ≈ 50-59
  - F < 50
- The numeric field should reflect the global security posture based on:
  - network exposure (open ports, unexpected services),
  - TLS configuration (protocol, ciphers, validity),
  - presence/absence of key security headers,
  - presence of serious findings (high/critical),
  - any blocking or visibility limitations.
- If the scan already provides a score/grade, you should keep it coherent with that value.

2) overall_risk_level
- Must be one of: "Très faible", "Faible", "Moyen", "Élevé", "Critique".
- The level should reflect:
  - the most severe vulnerabilities,
  - how easy they are to exploit,
  - their impact on confidentiality / integrity / availability.

3) executive_summary
- MUST be in French.
- 3 to 6 sentences max.
- Single paragraph.
- It SHOULD mention, when relevant:
  - le score global,
  - la surface d’exposition réseau,
  - l’état du chiffrement et de l’HTTPS,
  - les principales faiblesses,
  - une conclusion claire sur le niveau de risque.
- Style: ton professionnel, clair, sans jargon inutile.

4) top_3_vulnerabilities
- You MUST select up to 3 vulnerabilities from the scan findings.
- Prioritize by severity, exploitability, importance.
- Do NOT invent new findings.
- For each vulnerability:
  - "title": reformule le titre pour qu’il soit clair et court.
  - "severity": low/medium/high/critical.
  - "area": zone impactée.
  - "explanation_simple": explique en français, 1 à 3 phrases.
  - "fix_recommendation": action claire et concrète pour corriger.

5) site_map
- Use the discovery information from the input.
- "total_pages": count of discovered pages.
- "pages": list of URLs.
- Do NOT invent additional URLs.

6) infrastructure
- Deduce from input (dns_resolution, tls_info, headers).
- "hosting_provider": e.g. Vercel, AWS, or null.
- "tls_issuer": Organization name from TLS info.
- "server_header": Value of 'Server' header.
- "ip": Resolved IP address.

LENGTH & STYLE CONSTRAINTS:
- executive_summary: max 6 phrases.
- explanation_simple: 1 to 3 sentences.
- fix_recommendation: 1 to 3 sentences.
- No bullet points, no markdown, no HTML.
- Strictly in French.

REMINDER:
- Output ONLY the JSON object, nothing else.
"""

router = APIRouter()

from .scanner.engine import ScanEngine
from .scanner.models import ScanLogEntry

async def run_scan_task(scan_id: str, target: str):
    """Runs the real scan using ScanEngine."""
    engine = ScanEngine()
    
    # We don't need to init logs in store, as we append them or store at end.
    # For SSE, we might need a way to stream logs.
    # The current SSE implementation likely polls the `scans` dict.
    # We need to check `sse.py` to see how it works.
    # If it polls, we need to update it to poll the DB or use a different mechanism.
    # For now, let's assume we update the DB with logs periodically or just at the end?
    # The user wants "Persistence", but SSE needs real-time.
    # If we write to DB on every log, it might be slow for SQLite?
    # Actually SQLite is fast enough for this scale.
    # Let's define a log callback that updates the DB or an in-memory buffer for SSE?
    # Wait, the prompt says "Replace the in-memory storage with a lightweight SQLite-backed persistence layer".
    # But SSE needs to read live updates.
    # If `sse.py` reads from `scans`, we need to update `sse.py` too.
    # Let's check `sse.py` in the next step. For now, I will write the task logic assuming `store` handles updates.

    # To support SSE without changing `sse.py` too much (if it takes a dict), we might need to adapt.
    # But `sse.py` takes `scans` dict. We should probably update `sse.py` to take `scan_id` and query DB.

    # Let's implement the task to update DB at the end for the result,
    # and maybe we can keep a small in-memory buffer for active scans for SSE?
    # Or just write to DB.

    # Actually, for this iteration, let's focus on persistence.
    # I'll implement the task to save the final result.

    logs_buffer = []

    async def log_callback(entry: ScanLogEntry):
        # Convert to dict
        log_dict = {
            "timestamp": entry.timestamp.isoformat(),
            "level": entry.level,
            "message": entry.message
        }
        logs_buffer.append(log_dict)
        # Update active logs in store for SSE
        store.append_log(scan_id, log_dict)

    # Run the scan
    try:
        # Update status to running (already done in start_scan but good to confirm)
        store.update_scan_status(scan_id, "running")

        result = await engine.run_scan(target, log_callback)

        # Convert dataclass result to Pydantic model dict
        findings_dicts = [
            {
                "title": f.title,
                "severity": f.severity,
                "category": f.category,
                "description": f.description,
                "recommendation": f.recommendation,
                "evidence": f.evidence
            } for f in result.findings
        ]

        logs_dicts = [
            {
                "timestamp": l.timestamp,
                "level": l.level,
                "message": l.message
            } for l in result.logs
        ]

        # Create ScanResult Pydantic model
        scan_result = ScanResult(
            scan_id=scan_id,
            target=result.target,
            status="done",
            score=result.score,
            grade=result.grade,
            findings=findings_dicts,
            logs=logs_dicts,
            timestamp=result.scanned_at,
            response_time_ms=result.response_time_ms,
            debug_info=result.debug_info,
            scan_status=result.scan_status,
            blocking_mechanism=result.blocking_mechanism,
            visibility_level=result.visibility_level
        )

        # Save to DB
        store.save_scan_result(scan_id, scan_result)

    except Exception as e:
        print(f"Scan failed: {e}")
        store.fail_scan(scan_id, str(e))

@router.post("/scan", response_model=ScanResponse)
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    if not is_authorized(request.target):
        raise HTTPException(status_code=403, detail="Target not authorized (Localhost/Private only)")

    # Create scan in DB
    scan = store.create_scan(request.target)

    background_tasks.add_task(run_scan_task, scan.id, request.target)

    return ScanResponse(scan_id=scan.id)

@router.get("/scan/{scan_id}/events")
async def scan_events(scan_id: str):
    # We need to check if scan exists
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    # We need to update event_generator to work with DB or handle it differently
    # For now, pass the store function or similar
    return StreamingResponse(event_generator(scan_id, store), media_type="text/event-stream")

@router.get("/scan/{scan_id}")
async def get_scan_result(scan_id: str):
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "completed":
        return {"status": scan.status}

    # Return the stored JSON result
    return scan.result_json

@router.get("/scan/{scan_id}/report.pdf")
async def get_scan_pdf(scan_id: str):
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "completed" or not scan.result_json:
        raise HTTPException(status_code=400, detail="Report not ready")

    # Generate PDF on the fly from stored result
    # Reconstruct ScanResult object
    try:
        result_obj = ScanResult(**scan.result_json)
        pdf_bytes = generate_pdf(result_obj)
        return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=report_{scan_id}.pdf"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")

@router.get("/scan/{scan_id}/report.json")
async def get_scan_json(scan_id: str):
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "completed" or not scan.result_json:
        raise HTTPException(status_code=400, detail="Report not ready")

    return Response(content=json.dumps(scan.result_json, indent=2), media_type="application/json", headers={"Content-Disposition": f"attachment; filename=report_{scan_id}.json"})

@router.get("/scan/{scan_id}/report.md")
async def get_scan_markdown(scan_id: str):
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "completed" or not scan.result_json:
        raise HTTPException(status_code=400, detail="Report not ready")

    try:
        result_obj = ScanResult(**scan.result_json)
        md_content = generate_markdown(result_obj)
        return Response(content=md_content, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=report_{scan_id}.md"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Markdown: {e}")

@router.get("/scan/{scan_id}/ai-debug")
async def get_scan_ai_debug(scan_id: str):
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "completed" or not scan.result_json:
        raise HTTPException(status_code=400, detail="Report not ready")

    try:
        raw_scan = scan.result_json
        print(f"DEBUG: raw_scan keys: {list(raw_scan.keys())}")
        if "debug_info" in raw_scan:
            print(f"DEBUG: debug_info type: {type(raw_scan['debug_info'])}")
            if isinstance(raw_scan['debug_info'], dict):
                print(f"DEBUG: debug_info keys: {list(raw_scan['debug_info'].keys())}")

        # Prepare data for AI view builder
        # We need to merge debug_info (which contains the details) with top-level fields
        debug_info = raw_scan.get("debug_info")
        if debug_info is None:
            debug_info = {}
            print("DEBUG: debug_info is None")
        elif not isinstance(debug_info, dict):
            print(f"DEBUG: debug_info is not a dict, it is {type(debug_info)}")
            debug_info = {}

        ai_input = debug_info.copy()

        # Ensure top-level fields override or supplement debug_info
        ai_input["target"] = raw_scan.get("target")
        ai_input["grade"] = raw_scan.get("grade")
        ai_input["score"] = raw_scan.get("score")
        ai_input["scan_status"] = raw_scan.get("scan_status")
        ai_input["blocking_mechanism"] = raw_scan.get("blocking_mechanism")
        ai_input["visibility_level"] = raw_scan.get("visibility_level")
        ai_input["findings"] = raw_scan.get("findings")

        print(f"DEBUG: ai_input keys passed to builder: {list(ai_input.keys())}")

        ai_view = build_ai_scan_view(ai_input)
        print(f"DEBUG: ai_view result keys: {list(ai_view.keys())}")

        return {
            "scan_id": scan_id,
            "raw_scan": raw_scan,
            "ai_view": ai_view
        }
    except Exception as e:
        print(f"ERROR in get_scan_ai_debug: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate AI view: {e}")

@router.post("/scan/{scan_id}/ai-analysis")
async def generate_scan_ai_analysis(scan_id: str, provider: str = None):
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "completed" or not scan.result_json:
        raise HTTPException(status_code=400, detail="Report not ready")

    try:
        raw_scan = scan.result_json

        # Prepare data for AI view builder (reuse logic from ai-debug)
        debug_info = raw_scan.get("debug_info")
        if not isinstance(debug_info, dict):
            debug_info = {}

        ai_input = debug_info.copy()
        ai_input["target"] = raw_scan.get("target")
        ai_input["grade"] = raw_scan.get("grade")
        ai_input["score"] = raw_scan.get("score")
        ai_input["scan_status"] = raw_scan.get("scan_status")
        ai_input["blocking_mechanism"] = raw_scan.get("blocking_mechanism")
        ai_input["visibility_level"] = raw_scan.get("visibility_level")
        ai_input["findings"] = raw_scan.get("findings")

        ai_view = build_ai_scan_view(ai_input)

        # Construct System Prompt
        system_prompt = AI_REPORT_SYSTEM_PROMPT

        # Construct User Prompt
        user_prompt = f"""Here is the scan result for {ai_input.get('target')}:
{json.dumps(ai_view, indent=2)}

Analyze this data and provide the security report in the requested JSON format.
"""

        # Call AI Analyzer
        from .ai.analyzer import analyzer
        response_text = analyzer.analyze(system_prompt, user_prompt, provider)

        # Clean up response if it contains markdown code blocks
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        # Parse JSON
        try:
            analysis_result = json.loads(cleaned_response)
            
            # Inject model name
            actual_model = settings.OLLAMA_MODEL if provider == "ollama" else settings.OPENROUTER_MODEL
            # If provider is None, it defaults to Ollama in analyzer, but we should check what analyzer actually used.
            # The analyzer logic defaults to Ollama if provider is None.
            if not provider:
                provider = "ollama"
                actual_model = settings.OLLAMA_MODEL
            
            analysis_result["model_name"] = f"{provider}:{actual_model}"
            
            return analysis_result
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response: {cleaned_response}")
            raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")

    except Exception as e:
        print(f"ERROR in generate_scan_ai_analysis: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate AI analysis: {e}")

@router.get("/scans", response_model=list[ScanResponse])
async def list_recent_scans():
    scans = store.list_scans(limit=50)
    return [ScanResponse(scan_id=s.id) for s in scans]


@router.get("/scan/{scan_id}/ai-report.pdf")
async def get_scan_ai_report_pdf(scan_id: str, provider: str = None):
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "completed" or not scan.result_json:
        raise HTTPException(status_code=400, detail="Report not ready")

    try:
        raw_scan = scan.result_json

        # Prepare data for AI view builder
        debug_info = raw_scan.get("debug_info")
        if not isinstance(debug_info, dict):
            debug_info = {}

        ai_input = debug_info.copy()
        ai_input["target"] = raw_scan.get("target")
        ai_input["grade"] = raw_scan.get("grade")
        ai_input["score"] = raw_scan.get("score")
        ai_input["scan_status"] = raw_scan.get("scan_status")
        ai_input["blocking_mechanism"] = raw_scan.get("blocking_mechanism")
        ai_input["visibility_level"] = raw_scan.get("visibility_level")
        ai_input["findings"] = raw_scan.get("findings")

        ai_view = build_ai_scan_view(ai_input)

        # Construct System Prompt
        system_prompt = AI_REPORT_SYSTEM_PROMPT

        # Construct User Prompt
        user_prompt = f"""Here is the scan result for {ai_input.get('target')}:
{json.dumps(ai_view, indent=2)}

Analyze this data and provide the security report in the requested JSON format.
"""

        # Call AI Analyzer
        from .ai.analyzer import analyzer
        response_text = analyzer.analyze(system_prompt, user_prompt, provider)

        # Clean up response
        cleaned_response = response_text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        # Parse JSON
        try:
            ai_summary = json.loads(cleaned_response)
            
            # Inject model name
            actual_model = settings.OLLAMA_MODEL if provider == "ollama" else settings.OPENROUTER_MODEL
            if not provider:
                provider = "ollama"
                actual_model = settings.OLLAMA_MODEL
            ai_summary["model_name"] = f"{provider}:{actual_model}"
            
            # Generate PDF
            result_obj = ScanResult(**scan.result_json)
            pdf_bytes = generate_ai_pdf(result_obj, ai_summary)
            
            return Response(
                content=pdf_bytes, 
                media_type="application/pdf", 
                headers={"Content-Disposition": f"attachment; filename=ai_report_{scan_id}.pdf"}
            )
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response: {cleaned_response}")
            raise HTTPException(status_code=500, detail=f"AI returned invalid JSON: {str(e)}")

    except Exception as e:
        print(f"ERROR in get_scan_ai_report_pdf: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate AI PDF: {e}")
