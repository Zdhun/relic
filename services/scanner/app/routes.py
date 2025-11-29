import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from .models import ScanRequest, ScanResponse, ScanResult, ScanLog, Finding
from . import store
from .policy import is_authorized
from .sse import event_generator
from .pdf import generate_pdf

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

@router.get("/scans", response_model=list[ScanResponse])
async def list_recent_scans():
    scans = store.list_scans(limit=50)
    return [ScanResponse(scan_id=s.id) for s in scans]

