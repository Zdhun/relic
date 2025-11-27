import asyncio
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from .models import ScanRequest, ScanResponse, ScanResult, ScanLog, Finding
from .store import scans
from .policy import is_authorized
from .sse import event_generator
from .pdf import generate_pdf

router = APIRouter()

async def run_scan_simulation(scan_id: str, target: str):
    """Simulates a scan process."""
    steps = [
        ("INFO", "Starting scan for target: " + target),
        ("INFO", "Resolving DNS..."),
        ("INFO", "Checking SSL/TLS configuration..."),
        ("WARNING", "Weak cipher suite detected: TLS_RSA_WITH_AES_128_CBC_SHA"),
        ("INFO", "Crawling endpoints..."),
        ("INFO", "Analyzing HTTP headers..."),
        ("INFO", "Testing for XSS vulnerabilities..."),
        ("INFO", "Testing for SQL Injection..."),
        ("INFO", "Scan completed.")
    ]
    
    scans[scan_id]["logs"] = []
    
    for level, msg in steps:
        await asyncio.sleep(0.8) # Simulate work
        log = {"ts": datetime.now().strftime("%H:%M:%S"), "level": level, "msg": msg}
        scans[scan_id]["logs"].append(log)
    
    # Generate result
    findings = [
        Finding(title="Weak SSL Cipher", severity="Medium", impact="Potential traffic interception", recommendation="Disable TLS 1.0/1.1 and weak ciphers"),
        Finding(title="Missing HSTS Header", severity="Low", impact="Man-in-the-middle risk", recommendation="Enable Strict-Transport-Security"),
        Finding(title="Exposed Server Version", severity="Info", impact="Information disclosure", recommendation="Hide server tokens")
    ]
    
    result = ScanResult(
        scan_id=scan_id,
        target=target,
        status="done",
        score=75,
        grade="B",
        findings=findings,
        timestamp=datetime.now()
    )
    
    scans[scan_id]["result"] = result.model_dump()
    scans[scan_id]["status"] = "done"
    
    # Generate PDF
    pdf_bytes = generate_pdf(result)
    scans[scan_id]["pdf"] = pdf_bytes

@router.post("/scan", response_model=ScanResponse)
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    if not is_authorized(request.target):
        raise HTTPException(status_code=403, detail="Target not authorized (Localhost/Private only)")
        
    scan_id = str(uuid.uuid4())
    scans[scan_id] = {"status": "running", "logs": [], "result": None, "pdf": None}
    
    background_tasks.add_task(run_scan_simulation, scan_id, request.target)
    
    return ScanResponse(scan_id=scan_id)

@router.get("/scan/{scan_id}/events")
async def scan_events(scan_id: str):
    if scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    return StreamingResponse(event_generator(scan_id, scans), media_type="text/event-stream")

@router.get("/scan/{scan_id}")
async def get_scan_result(scan_id: str):
    if scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    data = scans[scan_id]
    if data["status"] != "done":
        return {"status": data["status"]}
        
    return data["result"]

@router.get("/scan/{scan_id}/report.pdf")
async def get_scan_pdf(scan_id: str):
    if scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    data = scans[scan_id]
    if not data.get("pdf"):
        raise HTTPException(status_code=400, detail="PDF not ready")
        
    return Response(content=data["pdf"], media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=report_{scan_id}.pdf"})
