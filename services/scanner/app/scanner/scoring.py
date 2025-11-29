from typing import List, Tuple
from .models import Finding

PENALTIES = {
    "critical": 40,
    "high": 25,
    "medium": 10,
    "low": 5,
    "info": 0
}

def calculate_score(findings: List[Finding]) -> Tuple[int, str]:
    """
    Calculates the security score and grade based on findings.
    Score starts at 100 and decreases based on penalties.
    """
    score = 100
    
    for finding in findings:
        penalty = PENALTIES.get(finding.severity, 0)
        score -= penalty
        
    # Ensure score doesn't drop below 0
    score = max(0, score)
    
    # Determine Grade
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    elif score >= 50:
        grade = "E"
    else:
        grade = "F"
        
    return score, grade
