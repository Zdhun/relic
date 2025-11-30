from typing import List, Dict, Any, Tuple
from .models import Finding
from .http_client import HttpClient

async def check_cors(target_url: str, initial_headers: Dict[str, str], http_client: HttpClient, log_callback, cookies_present: bool = False) -> Tuple[List[Finding], Dict[str, Any]]:
    """
    Analyzes CORS headers for dangerous configurations using passive analysis and active probing.
    Returns a list of findings and a dictionary with raw CORS info.
    """
    findings = []
    headers_lower = {k.lower(): v for k, v in initial_headers.items()}
    
    cors_info = {
        "allow_origin": headers_lower.get("access-control-allow-origin"),
        "allow_credentials": headers_lower.get("access-control-allow-credentials"),
        "vary": headers_lower.get("vary"),
        "probes": [],
        "notes": []
    }
    
    allow_origin = cors_info["allow_origin"]
    allow_credentials = cors_info["allow_credentials"]
    credentials_true = allow_credentials and allow_credentials.lower() == "true"
    
    # Determine risk context
    risk_level = "info"
    if allow_origin == "*":
        if credentials_true and cookies_present:
            risk_level = "high"
        elif credentials_true:
            risk_level = "medium" # Credentials allowed but no cookies found (maybe auth via header?)
        elif cookies_present:
            risk_level = "low" # Wildcard but no credentials, though cookies exist (maybe session riding risk if logic flawed?)
        else:
            risk_level = "info" # Wildcard, no creds, no cookies (likely public API)
            
    cors_info["context"] = {
        "cookies_present": cookies_present,
        "credentials_enabled": credentials_true,
        "risk_level": risk_level
    }
    
    # 1. Passive Analysis
    if allow_origin == "*" and credentials_true:
        # This is technically invalid per spec (wildcard + creds), but some browsers might support it or server is confused.
        # If it works, it's critical.
        severity = "high" if cookies_present else "medium"
        findings.append(Finding(
            title="Dangerous CORS: Wildcard Origin with Credentials",
            severity=severity,
            category="cors",
            description="The server allows access from any origin ('*') while also allowing credentials. This is a critical security risk if authentication cookies are used.",
            recommendation="Restrict 'Access-Control-Allow-Origin' to a whitelist of trusted domains.",
            evidence=f"Access-Control-Allow-Origin: *\nAccess-Control-Allow-Credentials: true\nContext: Cookies Present={cookies_present}"
        ))
        cors_info["notes"].append("Passive: Wildcard + Credentials detected.")
        
    elif allow_origin == "*":
        # Wildcard without credentials
        severity = "info"
        desc = "The server allows access from any origin ('*')."
        
        if not cookies_present and not credentials_true:
            desc += " No cookies or credentials detected, so this is likely a public API or static content. Risk is low."
        else:
            severity = "low"
            desc += " This is acceptable for public APIs but risky for internal services."

        findings.append(Finding(
            title="Permissive CORS: Wildcard Origin",
            severity=severity,
            category="cors",
            description=desc,
            recommendation="Ensure this is intended for a public API. Otherwise, restrict origins.",
            evidence=f"Access-Control-Allow-Origin: *\nContext: Cookies Present={cookies_present}, Credentials Allowed={credentials_true}"
        ))
        cors_info["notes"].append("Passive: Wildcard detected.")

    # 2. Active Probing
    # Probe 1: Evil Origin
    evil_origin = "https://evil.example.com"
    if log_callback:
        await log_callback("INFO", f"Probing CORS with Origin: {evil_origin}")
        
    probe_headers = {"Origin": evil_origin}
    response = await http_client.get(target_url, headers=probe_headers)
    
    if response:
        resp_origin = response.headers.get("Access-Control-Allow-Origin")
        resp_creds = response.headers.get("Access-Control-Allow-Credentials")
        
        probe_result = {
            "sent_origin": evil_origin,
            "received_origin": resp_origin,
            "received_credentials": resp_creds,
            "status": response.status_code
        }
        cors_info["probes"].append(probe_result)
        
        if resp_origin == evil_origin:
            severity = "medium"
            title = "CORS Misconfiguration: Origin Reflection"
            desc = f"The server reflects the arbitrary origin '{evil_origin}' in 'Access-Control-Allow-Origin'."
            
            if resp_creds and resp_creds.lower() == "true":
                severity = "high"
                title = "Dangerous CORS: Origin Reflection with Credentials"
                desc += " It also allows credentials, which is a critical risk."
            
            findings.append(Finding(
                title=title,
                severity=severity,
                category="cors",
                description=desc,
                recommendation="Validate the 'Origin' header against a whitelist before reflecting it.",
                evidence=f"Sent Origin: {evil_origin}\nReceived ACAO: {resp_origin}\nACAC: {resp_creds}"
            ))
            cors_info["notes"].append(f"Active: Reflection detected for {evil_origin}")
            
    # Probe 2: Null Origin (optional, but good for local file attacks)
    null_origin = "null"
    if log_callback:
        await log_callback("INFO", f"Probing CORS with Origin: {null_origin}")
        
    response_null = await http_client.get(target_url, headers={"Origin": null_origin})
    if response_null:
        resp_origin = response_null.headers.get("Access-Control-Allow-Origin")
        resp_creds = response_null.headers.get("Access-Control-Allow-Credentials")
        
        probe_result = {
            "sent_origin": null_origin,
            "received_origin": resp_origin,
            "received_credentials": resp_creds,
            "status": response_null.status_code
        }
        cors_info["probes"].append(probe_result)
        
        if resp_origin == null_origin and resp_creds and resp_creds.lower() == "true":
             findings.append(Finding(
                title="Dangerous CORS: Null Origin with Credentials",
                severity="high",
                category="cors",
                description="The server allows the 'null' origin with credentials. This can be exploited via sandboxed iframes.",
                recommendation="Do not allow 'null' origin with credentials.",
                evidence=f"Sent Origin: null\nReceived ACAO: null\nACAC: true"
            ))
             cors_info["notes"].append("Active: Null origin allowed with credentials.")

    return findings, cors_info
