from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ScanRequest(BaseModel):
    target: str

class ScanLog(BaseModel):
    ts: str
    level: str
    msg: str

class Finding(BaseModel):
    title: str
    severity: str
    impact: str
    recommendation: str

class ScanResult(BaseModel):
    scan_id: str
    target: str
    status: str
    score: int
    grade: str
    findings: List[Finding]
    timestamp: datetime

class ScanResponse(BaseModel):
    scan_id: str
