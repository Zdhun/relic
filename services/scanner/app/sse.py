import asyncio
import json
from typing import AsyncGenerator
from .models import ScanLog

async def event_generator(scan_id: str, store: dict) -> AsyncGenerator[str, None]:
    """
    Yields SSE events for a given scan_id.
    """
    # Wait for scan to start
    while scan_id not in store:
        await asyncio.sleep(0.1)
    
    scan_data = store[scan_id]
    sent_logs_count = 0
    
    while True:
        # Check for new logs
        current_logs = scan_data.get("logs", [])
        if len(current_logs) > sent_logs_count:
            for log in current_logs[sent_logs_count:]:
                # Format: event: log\ndata: {...}\n\n
                yield f"event: log\ndata: {json.dumps(log)}\n\n"
            sent_logs_count = len(current_logs)
        
        # Check if done
        if scan_data.get("status") in ["done", "failed"]:
            yield f"event: done\ndata: {json.dumps({'scan_id': scan_id, 'status': scan_data['status']})}\n\n"
            break
            
        await asyncio.sleep(0.5)
