from typing import List, Dict, Callable, Awaitable
from .models import Finding, ScanLogEntry
from .http_client import HttpClient

async def check_exposure(headers: Dict[str, str]) -> List[Finding]:
    """
    Checks for information disclosure in headers.
    """
    findings = []
    headers_lower = {k.lower(): v for k, v in headers.items()}
    
    if "server" in headers_lower:
        findings.append(Finding(
            title="Server Header Exposed",
            severity="info",
            category="exposure",
            description=f"The 'Server' header is exposed: {headers_lower['server']}.",
            recommendation="Configure the server to suppress or obscure the 'Server' header."
        ))
        
    if "x-powered-by" in headers_lower:
        findings.append(Finding(
            title="X-Powered-By Header Exposed",
            severity="low",
            category="exposure",
            description=f"The 'X-Powered-By' header is exposed: {headers_lower['x-powered-by']}.",
            recommendation="Remove the 'X-Powered-By' header to hide the underlying technology."
        ))
        
    return findings

import random
import string
import urllib.parse
from typing import List, Dict, Callable, Awaitable, Tuple, Set

async def extract_params(url: str) -> Dict[str, Set[str]]:
    """Extracts parameters from a URL."""
    params_map = {}
    parsed = urllib.parse.urlparse(url)
    if parsed.query:
        qs = urllib.parse.parse_qs(parsed.query)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if base_url not in params_map:
            params_map[base_url] = set()
        for k in qs.keys():
            params_map[base_url].add(k)
    return params_map

import time
from ..config import settings

async def check_xss_url(url: str, http_client: HttpClient, log_callback: Callable[[str, str], Awaitable[None]] = None) -> Tuple[List[Finding], List[Dict]]:
    """
    Checks a single URL for XSS vulnerabilities.
    Returns a tuple of (findings, evidence_list).
    """
    findings = []
    evidence_list = []
    
    # Payloads
    canary_token = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    payloads = [
        f"auditai_canary_{canary_token}",
        f"\"><script>alert('{canary_token}')</script>",
        f"\"><img src=x onerror=alert('{canary_token}')>",
        f"</script><script>alert('{canary_token}')</script>",
        f"javascript:alert('{canary_token}')",
        f"\" onmouseover=\"alert('{canary_token}')", # Attribute injection
        f"';alert('{canary_token}');//" # JS context injection
    ]
    
    params_map = await extract_params(url)
    if not params_map:
        return findings, evidence_list

    for base_url, params in params_map.items():
        for param in params:
            for payload in payloads:
                test_url = f"{base_url}?{param}={urllib.parse.quote(payload)}"
                try:
                    response = await http_client.get(test_url)
                    if response:
                        evidence_list.append({
                            "url": test_url,
                            "payload": payload,
                            "status_code": response.status_code
                        })
                        
                        if "text/html" in response.headers.get("Content-Type", "").lower():
                            body = response.text
                            if payload in body:
                                severity = "high"
                                description = f"Reflected XSS detected on parameter '{param}'."
                                evidence_str = f"Payload: {payload}\nURL: {test_url}\nReflected in response."
                                
                                # Context analysis
                                if f"value=\"{payload}\"" in body or f"value='{payload}'" in body:
                                    description += " Reflected inside attribute value."
                                elif f"<script>{payload}</script>" in body or f"<script>...{payload}...</script>" in body: # simplified check
                                    description += " Reflected inside script block."
                                elif "<script>" in payload and "<script>" in body:
                                    description += " Script tags were reflected unescaped."
                                
                                findings.append(Finding(
                                    title="Reflected XSS Vulnerability",
                                    severity=severity,
                                    category="xss",
                                    description=description,
                                    recommendation="Implement context-aware output encoding and validate all input.",
                                    evidence=evidence_str
                                ))
                                
                                if log_callback:
                                    await log_callback("WARNING", f"XSS detected on {base_url} param {param}")
                                
                                # Stop testing this param if vulnerable
                                break
                except Exception as e:
                    if log_callback:
                        await log_callback("ERROR", f"XSS check error for {test_url}: {e}")
                        
    return findings, evidence_list

async def check_xss(target: str, http_client: HttpClient, log_callback: Callable[[str, str], Awaitable[None]] = None, discovered_urls: List[str] = None) -> tuple[List[Finding], Dict[str, any]]:
    """
    Checks for Reflected XSS using parameter discovery and multiple payloads.
    """
    findings = []
    evidence = []
    
    urls_to_test = set()
    urls_to_test.add(target)
    if discovered_urls:
        for url in discovered_urls:
            urls_to_test.add(url)
            
    tested_count = 0
    MAX_TESTS = 20
    
    if log_callback:
        await log_callback("INFO", f"Starting XSS check on {len(urls_to_test)} URLs.")

    for url in urls_to_test:
        if tested_count >= MAX_TESTS:
            break
            
        # We need to be careful about counting "tests" vs "urls".
        # The helper checks all params/payloads for a URL.
        # For simplicity in this refactor, we just call the helper.
        # Ideally we'd pass limits down, but let's keep it simple.
        
        f, e = await check_xss_url(url, http_client, log_callback)
        findings.extend(f)
        evidence.extend(e)
        tested_count += len(e) # Approximate count based on requests made
        
    outcome_info = {
        "outcome": "pass",
        "reason": "No XSS reflections detected",
        "evidence": evidence
    }

    if findings:
        outcome_info["outcome"] = "fail"
        outcome_info["reason"] = "XSS reflection detected"
    elif not evidence:
        outcome_info["outcome"] = "not_tested"
        outcome_info["reason"] = "No suitable URLs with parameters were found for XSS testing."
        
    if evidence:
        outcome_info["status_code"] = evidence[0]["status_code"]

    return findings, outcome_info

async def check_sqli_url(url: str, http_client: HttpClient, log_callback: Callable[[str, str], Awaitable[None]] = None) -> Tuple[List[Finding], List[Dict]]:
    """
    Checks a single URL for SQLi vulnerabilities, including Blind SQLi.
    Returns a tuple of (findings, evidence_list).
    """
    findings = []
    evidence_list = []
    
    # Error-based payloads
    error_payloads = [
        "' OR 1=1--",
        "' OR 'a'='a'--",
        "') OR 1=1--",
        '" OR 1=1--',
        "' AND 1=0--"
    ]
    
    # Time-based payloads (generic sleep for 5 seconds)
    # Note: Syntax varies by DB. We try a few common ones.
    # We use a placeholder {sleep} which we replace with the delay
    sleep_delay = int(settings.BLIND_SQLI_THRESHOLD)
    time_payloads = [
        f"'; SELECT SLEEP({sleep_delay})--", # MySQL
        f"'; WAITFOR DELAY '00:00:{sleep_delay:02d}'--", # SQL Server
        f"'; SELECT pg_sleep({sleep_delay})--", # PostgreSQL
        f"' OR SLEEP({sleep_delay})--", # MySQL alternative
    ]
    
    error_signatures = [
        "you have an error in your sql syntax",
        "warning: mysql_",
        "sqlstate[hy000]",
        "ora-00933",
        "unclosed quotation mark after the character string",
        "microsoft ole db provider for sql server",
        "syntax error at or near",
        "sqlstate"
    ]
    
    params_map = await extract_params(url)
    if not params_map:
        return findings, evidence_list

    for base_url, params in params_map.items():
        for param in params:
            # 1. Error-based checks
            for payload in error_payloads:
                test_url = f"{base_url}?{param}={urllib.parse.quote(payload)}"
                try:
                    response = await http_client.get(test_url)
                    if response:
                        evidence_list.append({
                            "url": test_url,
                            "payload": payload,
                            "status_code": response.status_code,
                            "type": "error_based"
                        })
                        
                        body = response.text.lower()
                        found_sig = None
                        for sig in error_signatures:
                            if sig in body:
                                found_sig = sig
                                break
                        
                        if found_sig:
                            findings.append(Finding(
                                title="Potential SQL Injection Error",
                                severity="high",
                                category="sqli",
                                description="The application returned a database error message, suggesting a potential SQL injection vulnerability.",
                                recommendation="Use parameterized queries or prepared statements to prevent SQL injection.",
                                evidence=f"Error signature found: '{found_sig}' at {test_url}\nPayload: {payload}"
                            ))
                            
                            if log_callback:
                                await log_callback("WARNING", f"SQL Error found: {found_sig} on {base_url} param {param}")
                            
                            break # Stop testing this param
                            
                except Exception as e:
                    if log_callback:
                        await log_callback("ERROR", f"SQLi check error for {test_url}: {e}")

            # 2. Time-based checks (Blind SQLi)
            # Only run if no error-based found to save time? Or run anyway?
            # Let's run anyway for completeness but maybe limit to one payload if found.
            
            for payload in time_payloads:
                test_url = f"{base_url}?{param}={urllib.parse.quote(payload)}"
                try:
                    start_time = time.time()
                    response = await http_client.get(test_url)
                    duration = time.time() - start_time
                    
                    if response:
                        evidence_list.append({
                            "url": test_url,
                            "payload": payload,
                            "status_code": response.status_code,
                            "duration": duration,
                            "type": "time_based"
                        })
                        
                        if duration >= settings.BLIND_SQLI_THRESHOLD:
                            # Potential Blind SQLi
                            # To be sure, we should compare with a baseline, but for now absolute threshold is okay-ish
                            findings.append(Finding(
                                title="Potential Blind SQL Injection (Time-based)",
                                severity="critical",
                                category="sqli",
                                description=f"The application took {duration:.2f}s to respond to a sleep payload, suggesting a potential Blind SQL injection vulnerability.",
                                recommendation="Use parameterized queries or prepared statements.",
                                evidence=f"Payload: {payload}\nURL: {test_url}\nResponse time: {duration:.2f}s (Threshold: {settings.BLIND_SQLI_THRESHOLD}s)"
                            ))
                            if log_callback:
                                await log_callback("WARNING", f"Blind SQLi detected: {duration:.2f}s delay on {base_url} param {param}")
                            break # Stop testing this param
                            
                except Exception as e:
                    # Timeout might happen if it sleeps too long, which is also a sign!
                    # But http_client timeout is usually higher (e.g. 10s) than threshold (5s).
                    if "timeout" in str(e).lower():
                         findings.append(Finding(
                                title="Potential Blind SQL Injection (Timeout)",
                                severity="critical",
                                category="sqli",
                                description="The application timed out when sent a sleep payload, suggesting a potential Blind SQL injection vulnerability.",
                                recommendation="Use parameterized queries or prepared statements.",
                                evidence=f"Payload: {payload}\nURL: {test_url}\nRequest timed out."
                            ))
                         if log_callback:
                            await log_callback("WARNING", f"Blind SQLi (Timeout) on {base_url} param {param}")
                    else:
                        if log_callback:
                            await log_callback("ERROR", f"Blind SQLi check error for {test_url}: {e}")
                        
    return findings, evidence_list

async def check_sqli(target: str, http_client: HttpClient, log_callback: Callable[[str, str], Awaitable[None]] = None, discovered_urls: List[str] = None) -> tuple[List[Finding], Dict[str, any]]:
    """
    Checks for SQL Injection errors using multiple payloads and parameter discovery.
    """
    findings = []
    evidence = []
    
    urls_to_test = set()
    urls_to_test.add(target)
    if discovered_urls:
        for url in discovered_urls:
            urls_to_test.add(url)
            
    tested_count = 0
    MAX_TESTS = 20
    
    if log_callback:
        await log_callback("INFO", f"Starting SQLi check on {len(urls_to_test)} URLs.")

    for url in urls_to_test:
        if tested_count >= MAX_TESTS:
            break
            
        f, e = await check_sqli_url(url, http_client, log_callback)
        findings.extend(f)
        evidence.extend(e)
        tested_count += len(e)
        
    outcome_info = {
        "outcome": "pass",
        "reason": "No SQL errors detected",
        "evidence": evidence
    }

    if findings:
        outcome_info["outcome"] = "fail"
        outcome_info["reason"] = "SQL error signature found"
    elif not evidence:
        outcome_info["outcome"] = "not_tested"
        outcome_info["reason"] = "No suitable URLs with parameters were found for SQLi testing."
        
    if evidence:
        outcome_info["status_code"] = evidence[0]["status_code"]

    return findings, outcome_info

async def check_https_enforcement(target_info: 'TargetInfo', http_client: HttpClient, log_callback: Callable[[str, str], Awaitable[None]] = None) -> tuple[List[Finding], Dict[str, any]]:
    """
    Checks if HTTPS is enforced when accessing via HTTP.
    Returns findings and raw debug info.
    """
    findings = []
    
    if log_callback:
        await log_callback("INFO", f"Entering check_https_enforcement. Scheme: {target_info.scheme}")

    # Only run if scheme is http
    if target_info.scheme != "http":
        debug_data = {
            "checked": False,
            "reason": "target already HTTPS",
            "https_reachable": True,
            "http_redirected_to_https": None,
            "http_final_url": None
        }
        if log_callback:
            await log_callback("INFO", "HTTPS enforcement: skipped (target already HTTPS).")
        return findings, debug_data

    debug_data = {
        "checked": True,
        "http_redirected_to_https": False,
        "http_final_url": None,
        "https_reachable": False,
        "outcome": "pass", # Default to pass, will update if fail or blocked
        "reason": "HTTPS enforced"
    }

    if log_callback:
        await log_callback("INFO", "Checking HTTP -> HTTPS redirection...")

    # 1. Check HTTP redirection
    # target_info.full_url should be the http url since scheme is http
    http_url = target_info.full_url
    
    try:
        response = await http_client.get(http_url)
        if response:
            final_url = str(response.url)
            debug_data["http_final_url"] = final_url
            if final_url.startswith("https://"):
                debug_data["http_redirected_to_https"] = True
                if log_callback:
                    await log_callback("INFO", "HTTP redirects to HTTPS.")
            else:
                if log_callback:
                    await log_callback("INFO", "HTTP does NOT redirect to HTTPS.")
    except Exception as e:
        if log_callback:
            await log_callback("ERROR", f"HTTP check failed: {e}")

    # 2. Check HTTPS reachability
    https_url = f"https://{target_info.hostname}/" # Default port 443
    if log_callback:
        await log_callback("INFO", f"Checking HTTPS reachability at {https_url}...")
        
    try:
        # Use a short timeout for this check
        response_https = await http_client.get(https_url)
        if response_https:
            debug_data["https_reachable"] = True
            debug_data["https_status_code"] = response_https.status_code
            if log_callback:
                await log_callback("INFO", "HTTPS is reachable.")
        else:
            if log_callback:
                await log_callback("INFO", "HTTPS is NOT reachable.")
    except Exception:
        pass

    # Generate finding
    if not debug_data["http_redirected_to_https"] and debug_data["https_reachable"]:
        findings.append(Finding(
            title="Le site est accessible en HTTP (HTTPS non imposé)",
            severity="high",
            category="tls", # Fits TLS/Encryption category
            description="Le site est accessible en HTTP sans redirection automatique vers HTTPS, bien que HTTPS soit disponible.",
            recommendation="Forcer la redirection 301 vers HTTPS, servir HSTS uniquement sur HTTPS, envisager includeSubDomains.",
            evidence=f"HTTP URL: {debug_data['http_final_url']}\nHTTPS is reachable."
        ))
        debug_data["outcome"] = "fail"
        debug_data["reason"] = "HTTPS not enforced"
        if log_callback:
            await log_callback("WARNING", "HTTPS enforcement missing!")

    return findings, debug_data
