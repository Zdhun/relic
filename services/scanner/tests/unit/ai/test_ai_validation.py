"""
Unit tests for AI output validation module.
Tests validation logic without network access.

These tests verify:
1. Valid AI JSON validates successfully
2. Invalid JSON shape (missing fields) fails and triggers fallback
3. Severity normalization: "High" becomes "high"
4. Extra keys are rejected with extra=forbid
"""

import pytest
from app.ai.models import AIReport, AIKeyVulnerability, AIGlobalScore, AISiteMap, AIInfrastructure
from app.ai.validation import validate_ai_report, FALLBACK_REPORT
from pydantic import ValidationError


class TestAIReportValidation:
    """Tests for the AIReport Pydantic model via validate_ai_report."""
    
    def test_valid_report_validates_successfully(self):
        """Valid JSON with all required fields should validate."""
        valid_json = '''
        {
            "global_score": {"letter": "B", "numeric": 75},
            "overall_risk_level": "Moyen",
            "executive_summary": "Ce site présente un niveau de sécurité acceptable avec quelques points d'amélioration.",
            "key_vulnerabilities": [
                {
                    "title": "Headers de sécurité manquants",
                    "severity": "medium",
                    "area": "Headers",
                    "explanation_simple": "Certains en-têtes HTTP de sécurité sont absents.",
                    "fix_recommendation": "Ajouter X-Frame-Options et Content-Security-Policy."
                }
            ],
            "site_map": {"total_pages": 5, "pages": ["/", "/about", "/contact"]},
            "infrastructure": {"hosting_provider": "Vercel", "ip": "76.76.21.21"}
        }
        '''
        result, is_valid = validate_ai_report(valid_json, scan_id="test-001")
        
        assert is_valid is True
        assert result["global_score"]["letter"] == "B"
        assert result["global_score"]["numeric"] == 75
        assert len(result["key_vulnerabilities"]) == 1
        assert result["overall_risk_level"] == "moyen"  # Normalized to lowercase
    
    def test_missing_required_fields_triggers_fallback(self):
        """Missing required fields should fail validation and return fallback."""
        invalid_json = '''
        {
            "global_score": {"letter": "A", "numeric": 90},
            "executive_summary": "Missing overall_risk_level field"
        }
        '''
        result, is_valid = validate_ai_report(invalid_json, scan_id="test-002")
        
        assert is_valid is False
        assert result["overall_risk_level"] == "moyen"  # Fallback value
        assert "validation_failed" in result.get("model_name", "")
    
    def test_severity_normalization_high_to_lowercase(self):
        """Severity 'High' or 'HIGH' should be normalized to 'high'."""
        vuln = AIKeyVulnerability(
            title="Test",
            severity="HIGH",  # Uppercase
            area="TLS",
            explanation_simple="Test explanation",
            fix_recommendation="Test fix"
        )
        assert vuln.severity == "high"
    
    def test_severity_normalization_mixed_case(self):
        """Mixed case severity should normalize correctly."""
        vuln = AIKeyVulnerability(
            title="Test",
            severity="CrItIcAl",
            area="Network",
            explanation_simple="Test explanation",
            fix_recommendation="Test fix"
        )
        assert vuln.severity == "critical"
    
    def test_extra_keys_rejected(self):
        """Unknown keys should be rejected with extra='forbid'."""
        invalid_json = '''
        {
            "global_score": {"letter": "A", "numeric": 95},
            "overall_risk_level": "faible",
            "executive_summary": "Everything looks good for this test.",
            "unknown_field": "should cause rejection",
            "site_map": {},
            "infrastructure": {}
        }
        '''
        result, is_valid = validate_ai_report(invalid_json, scan_id="test-003")
        
        assert is_valid is False
    
    def test_malformed_json_triggers_fallback(self):
        """Completely malformed JSON should trigger fallback gracefully."""
        malformed = "This is not JSON at all { broken"
        
        result, is_valid = validate_ai_report(malformed, scan_id="test-004")
        
        assert is_valid is False
        assert "indisponible" in result["executive_summary"]
    
    def test_markdown_wrapped_json_parses_correctly(self):
        """JSON wrapped in markdown code blocks should still parse."""
        wrapped_json = '''
        ```json
        {
            "global_score": {"letter": "C", "numeric": 65},
            "overall_risk_level": "moyen",
            "executive_summary": "Niveau de sécurité moyen détecté.",
            "key_vulnerabilities": [],
            "site_map": {"total_pages": 0, "pages": []},
            "infrastructure": {}
        }
        ```
        '''
        result, is_valid = validate_ai_report(wrapped_json, scan_id="test-005")
        
        assert is_valid is True
        assert result["global_score"]["numeric"] == 65
    
    def test_model_name_injected_correctly(self):
        """Model name should be injected into valid report."""
        valid_json = '''
        {
            "global_score": {"letter": "A", "numeric": 92},
            "overall_risk_level": "faible",
            "executive_summary": "Excellente posture de sécurité avec quelques points mineurs.",
            "key_vulnerabilities": [],
            "site_map": {},
            "infrastructure": {}
        }
        '''
        result, is_valid = validate_ai_report(
            valid_json, 
            scan_id="test-006",
            model_name="ollama:llama3"
        )
        
        assert is_valid is True
        assert result["model_name"] == "ollama:llama3"
    
    def test_empty_vulnerabilities_list_is_valid(self):
        """Empty key_vulnerabilities list should be valid."""
        valid_json = '''
        {
            "global_score": {"letter": "A+", "numeric": 98},
            "overall_risk_level": "très faible",
            "executive_summary": "Aucune vulnérabilité critique détectée dans cette analyse.",
            "key_vulnerabilities": [],
            "site_map": {"total_pages": 1, "pages": ["/"]},
            "infrastructure": {"hosting_provider": "AWS"}
        }
        '''
        result, is_valid = validate_ai_report(valid_json, scan_id="test-007")
        
        assert is_valid is True
        assert result["key_vulnerabilities"] == []
    
    def test_model_name_in_fallback_includes_validation_failed(self):
        """Fallback report should indicate validation_failed in model_name."""
        invalid_json = '{"broken": true}'
        
        result, is_valid = validate_ai_report(
            invalid_json,
            scan_id="test-008",
            model_name="ollama:test"
        )
        
        assert is_valid is False
        assert "validation_failed" in result["model_name"]
        assert "ollama:test" in result["model_name"]


class TestRiskLevelNormalization:
    """Tests for French risk level normalization."""
    
    def test_uppercase_risk_normalized(self):
        """'MOYEN' should become 'moyen'."""
        report = AIReport(
            global_score=AIGlobalScore(letter="C", numeric=60),
            overall_risk_level="MOYEN",
            executive_summary="Test summary with enough characters for validation.",
        )
        assert report.overall_risk_level == "moyen"
    
    def test_eleve_accent_handling(self):
        """'Eleve' without accent should map to 'élevé'."""
        report = AIReport(
            global_score=AIGlobalScore(letter="D", numeric=45),
            overall_risk_level="Eleve",
            executive_summary="Test summary with enough characters for validation.",
        )
        assert report.overall_risk_level == "élevé"
    
    def test_tres_faible_accent_handling(self):
        """'tres faible' without accent should map to 'très faible'."""
        report = AIReport(
            global_score=AIGlobalScore(letter="A", numeric=95),
            overall_risk_level="tres faible",
            executive_summary="Test summary with enough characters for validation.",
        )
        assert report.overall_risk_level == "très faible"


class TestAIGlobalScore:
    """Tests for AIGlobalScore model."""
    
    def test_valid_score(self):
        """Valid score values should work."""
        score = AIGlobalScore(letter="A", numeric=95)
        assert score.letter == "A"
        assert score.numeric == 95
    
    def test_score_bounds_min(self):
        """Score of 0 should be valid."""
        score = AIGlobalScore(letter="F", numeric=0)
        assert score.numeric == 0
    
    def test_score_bounds_max(self):
        """Score of 100 should be valid."""
        score = AIGlobalScore(letter="A+", numeric=100)
        assert score.numeric == 100
    
    def test_score_above_max_invalid(self):
        """Score above 100 should raise ValidationError."""
        with pytest.raises(ValidationError):
            AIGlobalScore(letter="A", numeric=101)
    
    def test_score_below_min_invalid(self):
        """Score below 0 should raise ValidationError."""
        with pytest.raises(ValidationError):
            AIGlobalScore(letter="F", numeric=-1)
    
    def test_extra_field_rejected(self):
        """Extra fields should be rejected."""
        with pytest.raises(ValidationError):
            AIGlobalScore(letter="A", numeric=90, extra_field="rejected")


class TestAIKeyVulnerability:
    """Tests for AIKeyVulnerability model."""
    
    def test_valid_vulnerability(self):
        """Valid vulnerability should work."""
        vuln = AIKeyVulnerability(
            title="Missing Security Headers",
            severity="high",
            area="Headers",
            explanation_simple="Security headers are missing.",
            fix_recommendation="Add CSP and X-Frame-Options."
        )
        assert vuln.title == "Missing Security Headers"
        assert vuln.severity == "high"
    
    def test_invalid_severity_rejected(self):
        """Invalid severity value should raise ValidationError."""
        with pytest.raises(ValidationError):
            AIKeyVulnerability(
                title="Test",
                severity="super-critical",  # Not a valid Literal
                area="Test",
                explanation_simple="Test",
                fix_recommendation="Test"
            )
    
    def test_empty_title_rejected(self):
        """Empty title should be rejected."""
        with pytest.raises(ValidationError):
            AIKeyVulnerability(
                title="",  # Empty, should fail min_length=1
                severity="low",
                area="Test",
                explanation_simple="Test explanation",
                fix_recommendation="Test fix"
            )


class TestFallbackReport:
    """Tests for fallback report structure."""
    
    def test_fallback_has_required_fields(self):
        """Fallback report should have all required API fields."""
        assert "global_score" in FALLBACK_REPORT
        assert "overall_risk_level" in FALLBACK_REPORT
        assert "executive_summary" in FALLBACK_REPORT
        assert "key_vulnerabilities" in FALLBACK_REPORT
    
    def test_fallback_risk_is_medium(self):
        """Fallback risk should be 'moyen' (medium)."""
        assert FALLBACK_REPORT["overall_risk_level"] == "moyen"
    
    def test_fallback_vulnerabilities_empty(self):
        """Fallback vulnerabilities should be empty list."""
        assert FALLBACK_REPORT["key_vulnerabilities"] == []
