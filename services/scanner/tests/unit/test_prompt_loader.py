"""
Unit tests for the AI prompt loader utility.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.ai.prompt_loader import (
    load_prompt,
    get_prompt_path,
    clear_cache,
    PromptLoadError,
    PROMPTS_DIR,
)


class TestLoadPrompt:
    """Tests for the load_prompt function."""
    
    def setup_method(self):
        """Clear the cache before each test."""
        clear_cache()
    
    def test_load_existing_prompt_returns_non_empty_content(self):
        """Test that loading an existing prompt returns non-empty content."""
        content = load_prompt("security_report_system_v1")
        
        assert content is not None
        assert isinstance(content, str)
        assert len(content) > 0
        # Verify it's the correct prompt by checking for key phrases
        assert "senior web security auditor" in content.lower()
        assert "json" in content.lower()
    
    def test_missing_file_raises_prompt_load_error(self):
        """Test that loading a non-existent prompt raises PromptLoadError."""
        with pytest.raises(PromptLoadError) as exc_info:
            load_prompt("nonexistent_prompt_xyz_12345")
        
        error_message = str(exc_info.value)
        assert "not found" in error_message.lower()
        assert "nonexistent_prompt_xyz_12345" in error_message
    
    def test_caching_returns_same_content(self):
        """Test that subsequent calls return cached content."""
        # First call
        content1 = load_prompt("security_report_system_v1")
        # Second call
        content2 = load_prompt("security_report_system_v1")
        
        # Should be the exact same object due to LRU cache
        assert content1 is content2
    
    def test_cache_info_shows_hits(self):
        """Test that caching is working by checking cache stats."""
        clear_cache()
        
        # First call - should be a miss
        load_prompt("security_report_system_v1")
        cache_info = load_prompt.cache_info()
        assert cache_info.hits == 0
        assert cache_info.misses == 1
        
        # Second call - should be a hit
        load_prompt("security_report_system_v1")
        cache_info = load_prompt.cache_info()
        assert cache_info.hits == 1
        assert cache_info.misses == 1
    
    def test_clear_cache_resets_state(self):
        """Test that clear_cache() resets the cache."""
        load_prompt("security_report_system_v1")
        
        # Get cache info before clear
        cache_info_before = load_prompt.cache_info()
        assert cache_info_before.currsize > 0
        
        # Clear the cache
        clear_cache()
        
        # Cache should be empty now
        cache_info_after = load_prompt.cache_info()
        assert cache_info_after.currsize == 0


class TestGetPromptPath:
    """Tests for the get_prompt_path utility function."""
    
    def test_returns_correct_path(self):
        """Test that get_prompt_path returns the expected path."""
        path = get_prompt_path("security_report_system_v1")
        
        assert isinstance(path, Path)
        assert path.name == "security_report_system_v1.txt"
        assert path.parent == PROMPTS_DIR
    
    def test_path_for_existing_file_exists(self):
        """Test that path for existing prompt points to real file."""
        path = get_prompt_path("security_report_system_v1")
        assert path.exists()
        assert path.is_file()


class TestPromptFileContent:
    """Tests for the actual prompt file content."""
    
    def test_prompt_file_has_version_header(self):
        """Test that the prompt file contains version information."""
        content = load_prompt("security_report_system_v1")
        
        # Check for version header
        assert "VERSION:" in content or "version:" in content.lower()
        assert "v1" in content.lower() or "1.0" in content
    
    def test_prompt_file_has_required_schema_fields(self):
        """Test that the prompt file contains required output schema fields."""
        content = load_prompt("security_report_system_v1")
        
        # Key schema fields that must be present
        required_fields = [
            "global_score",
            "overall_risk_level",
            "executive_summary",
            "key_vulnerabilities",
            "site_map",
            "infrastructure",
        ]
        
        for field in required_fields:
            assert field in content, f"Missing required field: {field}"


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def setup_method(self):
        """Clear the cache before each test."""
        clear_cache()
    
    def test_empty_prompt_name_raises_error(self):
        """Test that empty prompt name is handled."""
        with pytest.raises(PromptLoadError):
            load_prompt("")
    
    def test_prompt_name_with_extension_fails(self):
        """Test that including .txt extension fails (expected behavior)."""
        # The function expects just the name without extension
        with pytest.raises(PromptLoadError):
            load_prompt("security_report_system_v1.txt")
    
    @patch("app.ai.prompt_loader.PROMPTS_DIR")
    def test_io_error_raises_prompt_load_error(self, mock_prompts_dir):
        """Test that I/O errors are wrapped in PromptLoadError."""
        clear_cache()
        
        # Create a mock path that raises IOError on read
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_text.side_effect = IOError("Disk error")
        mock_path.__truediv__ = MagicMock(return_value=mock_path)
        mock_prompts_dir.__truediv__ = MagicMock(return_value=mock_path)
        
        with pytest.raises(PromptLoadError) as exc_info:
            load_prompt("test_prompt")
        
        assert "failed to read" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
