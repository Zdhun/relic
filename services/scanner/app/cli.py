import typer
import asyncio
import os
from typing import Optional
from pathlib import Path
from .scanner.engine import ScanEngine
from .scanner.models import ScanLogEntry
from .models import ScanResult
from .pdf import generate_pdf, generate_json, generate_markdown
from .config import settings

app = typer.Typer()

async def run_scan_async(target: str, json_out: Optional[Path], pdf_out: Optional[Path], markdown_out: Optional[Path]):
    engine = ScanEngine()
    
    print(f"Starting scan for {target}...")
    
    async def log_callback(entry: ScanLogEntry):
        # Simple console logging
        timestamp = entry.timestamp.strftime("%H:%M:%S")
        color = typer.colors.WHITE
        if entry.level == "ERROR":
            color = typer.colors.RED
        elif entry.level == "WARNING":
            color = typer.colors.YELLOW
        elif entry.level == "INFO":
            color = typer.colors.GREEN
            
        typer.secho(f"[{timestamp}] [{entry.level}] {entry.message}", fg=color)

    try:
        result_dataclass = await engine.run_scan(target, log_callback)
        
        # Convert to Pydantic model for reporting
        # Map fields manually as before
        findings_dicts = [
            {
                "title": f.title,
                "severity": f.severity,
                "category": f.category,
                "description": f.description,
                "recommendation": f.recommendation,
                "evidence": f.evidence
            } for f in result_dataclass.findings
        ]
        
        logs_dicts = [
            {
                "timestamp": l.timestamp,
                "level": l.level,
                "message": l.message
            } for l in result_dataclass.logs
        ]
        
        result = ScanResult(
            scan_id="cli-scan", # Placeholder
            target=result_dataclass.target,
            status="done",
            score=result_dataclass.score,
            grade=result_dataclass.grade,
            findings=findings_dicts,
            logs=logs_dicts,
            timestamp=result_dataclass.scanned_at,
            response_time_ms=result_dataclass.response_time_ms,
            debug_info=result_dataclass.debug_info,
            scan_status=result_dataclass.scan_status,
            blocking_mechanism=result_dataclass.blocking_mechanism,
            visibility_level=result_dataclass.visibility_level
        )
        
        typer.secho(f"\nScan Completed!", fg=typer.colors.BRIGHT_GREEN, bold=True)
        typer.secho(f"Grade: {result.grade} (Score: {result.score})", fg=typer.colors.BRIGHT_BLUE)
        typer.secho(f"Findings: {len(result.findings)}", fg=typer.colors.WHITE)
        
        # Exports
        if json_out:
            with open(json_out, "w") as f:
                f.write(generate_json(result))
            typer.secho(f"JSON report saved to {json_out}", fg=typer.colors.GREEN)
            
        if pdf_out:
            pdf_bytes = generate_pdf(result)
            with open(pdf_out, "wb") as f:
                f.write(pdf_bytes)
            typer.secho(f"PDF report saved to {pdf_out}", fg=typer.colors.GREEN)
            
        if markdown_out:
            with open(markdown_out, "w") as f:
                f.write(generate_markdown(result))
            typer.secho(f"Markdown report saved to {markdown_out}", fg=typer.colors.GREEN)
            
    except Exception as e:
        typer.secho(f"Scan failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

@app.command()
def scan(
    target: str = typer.Argument(..., help="Target URL or IP to scan"),
    json_out: Optional[Path] = typer.Option(None, "--json-out", help="Path to save JSON report"),
    pdf_out: Optional[Path] = typer.Option(None, "--pdf-out", help="Path to save PDF report"),
    markdown_out: Optional[Path] = typer.Option(None, "--markdown-out", help="Path to save Markdown report"),
):
    """
    Run a security scan against a target.
    """
    asyncio.run(run_scan_async(target, json_out, pdf_out, markdown_out))

if __name__ == "__main__":
    app()
