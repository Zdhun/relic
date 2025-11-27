from typing import Dict, Any

# Simple in-memory store
# {scan_id: {"status": str, "logs": List[dict], "result": dict, "pdf": bytes}}
scans: Dict[str, Any] = {}
