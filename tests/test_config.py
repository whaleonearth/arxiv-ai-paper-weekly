"""Tests for configuration management module.

This module tests the loading, validation, and usage of user interest configurations.
"""

import os
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch

from src.core.config import (
    UserInterests,
    FilterConfig,
    SourceConfig,
    EmailConfig,
    load_user_interests,
    create_example_config
)


class TestFilterConfig:
    """Test FilterConfig dataclass."""
    
    def test_default_values(self):
        """Test FilterConfig creates with correct default values."""
        config = FilterConfig()
        assert config.min_github_stars == 10
        assert config.max_days_old == 7
        assert config.require_code is False
        assert config.min_paper_length == 4
    
    def test_custom_values(self):
        """Test FilterConfig accepts custom values."""
        config = FilterConfig(
            min_github_stars=50,
            max_days_old=14,
            require_code=True,
            min_paper_length=8
        )
        assert config.min_github_stars == 50
        assert config.max_days_old == 14
        assert config.require_code is True
        assert config.min_paper_length == 8


class TestSourceConfig:
    """Test SourceConfig dataclass."""
    
    def test_default_values(self):
        """Test SourceConfig creates with correct default values."""
        config = SourceConfig()
        assert config.papers_with_code is True
        assert config.semantic_scholar is True
        assert config.arxiv_recent is True
        assert config.github_trending is True
    
    def test_custom_values(self):
        """Test SourceConfig accepts custom values."""
        config = SourceConfig(
            papers_with_code=False,
            semantic_scholar=True,
            arxiv_recent=False,
            github_trending=True
        )
        assert config.papers_with_code is False
        assert config.semantic_scholar is True
        assert config.arxiv_recent is False
        assert config.github_trending is True


class TestEmailConfig:
    """Test EmailConfig dataclass."""
    
    def test_default_values(self):
        """Test EmailConfig creates with correct default values."""
        config = EmailConfig()
        assert config.max_papers_per_email == 20
        assert config.include_abstracts is True
        assert config.include_code_links is True
        assert config.include_pdf_links is True
        assert config.language == "English"
        assert config.smtp_server == ""
        assert config.smtp_port == 587
    
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'smtp.test.com',
        'SMTP_PORT': '465',
        'SENDER_EMAIL': 'test@example.com',
        'SENDER_PASSWORD': 'testpass',
        'RECEIVER_EMAIL': 'receiver@example.com'
    })
    def test_from_env_with_environment_variables(self):
        """Test EmailConfig.from_env loads environment variables correctly."""
        email_yaml_config = {
            'max_papers_per_email': 15,
            'language': 'Spanish'
        }
        config = EmailConfig.from_env(email_yaml_config)
        
        # YAML preferences
        assert config.max_papers_per_email == 15
        assert config.language == 'Spanish'
        
        # Environment variables
        assert config.smtp_server == 'smtp.test.com'
        assert config.smtp_port == 465
        assert config.sender_email == 'test@example.com'
        assert config.sender_password == 'testpass'
        assert config.receiver_email == 'receiver@example.com'
    
    def test_from_env_with_empty_config(self):
        """Test EmailConfig.from_env works with empty YAML config."""
        config = EmailConfig.from_env({})
        assert config.max_papers_per_email == 20
        assert config.language == "English"


class TestUserInterests:
    """Test UserInterests dataclass."""
    
    def setup_method(self):
        """Setup test data before each test."""
        self.valid_interests = UserInterests(
            research_areas=['machine learning', 'computer vision'],
            categories=['cs.AI', 'cs.CV'],
            keywords=['neural networks', 'deep learning']
        )
    
    def test_default_creation(self):
        """Test UserInterests creates with default values."""
        interests = UserInterests()
        assert interests.research_areas == []
        assert interests.categories == []
        assert interests.keywords == []
        assert isinstance(interests.sources, SourceConfig)
        assert isinstance(interests.filters, FilterConfig)
        assert isinstance(interests.email, EmailConfig)
    
    def test_get_all_interest_terms(self):
        """Test get_all_interest_terms combines all interest categories."""
        terms = self.valid_interests.get_all_interest_terms()
        expected = [
            'machine learning', 'computer vision',
            'neural networks', 'deep learning',
            'cs.AI', 'cs.CV'
        ]
        assert terms == expected
    
    def test_matches_interests_positive_cases(self):
        """Test matches_interests returns True for matching text."""
        test_cases = [
            "A new machine learning approach",
            "Deep learning for computer vision",
            "Neural networks in AI",
            "MACHINE LEARNING APPLICATIONS",  # Case insensitive
            "This paper discusses deep learning techniques"
        ]
        
        for text in test_cases:
            assert self.valid_interests.matches_interests(text), f"Failed for: {text}"
    
    def test_matches_interests_negative_cases(self):
        """Test matches_interests returns False for non-matching text."""
        test_cases = [
            "Quantum computing research",
            "Database optimization techniques", 
            "Software engineering best practices",
            "Hardware design methodology"
        ]
        
        for text in test_cases:
            assert not self.valid_interests.matches_interests(text), f"Failed for: {text}"
    
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'smtp.test.com',
        'SENDER_EMAIL': 'test@test.com',
        'SENDER_PASSWORD': 'password',
        'RECEIVER_EMAIL': 'receiver@test.com'
    })
    def test_validate_success(self):
        """Test validate passes for valid configuration."""
        # Reload email config with environment variables
        self.valid_interests.email = EmailConfig.from_env({})
        # Should not raise any exception
        self.valid_interests.validate()
    
    def test_validate_fails_no_interests(self):
        """Test validate fails when no interests are specified."""
        empty_interests = UserInterests()
        with pytest.raises(ValueError, match="You must specify at least one"):
            empty_interests.validate()
    
    def test_validate_fails_negative_github_stars(self):
        """Test validate fails for negative github stars."""
        interests = UserInterests(research_areas=['ai'])
        interests.filters.min_github_stars = -5
        
        with pytest.raises(ValueError, match="min_github_stars cannot be negative"):
            interests.validate()
    
    def test_validate_fails_zero_days_old(self):
        """Test validate fails for zero or negative days."""
        interests = UserInterests(research_areas=['ai'])
        interests.filters.max_days_old = 0
        
        with pytest.raises(ValueError, match="max_days_old must be positive"):
            interests.validate()
    
    def test_validate_fails_zero_papers_per_email(self):
        """Test validate fails for zero papers per email."""
        interests = UserInterests(research_areas=['ai'])
        interests.email.max_papers_per_email = 0
        
        with pytest.raises(ValueError, match="max_papers_per_email must be positive"):
            interests.validate()
    
    @patch.dict(os.environ, {}, clear=True)
    def test_validate_fails_missing_email_config(self):
        """Test validate fails when email configuration is missing."""
        interests = UserInterests(research_areas=['ai'])
        
        with pytest.raises(ValueError, match="Missing required environment variables"):
            interests.validate()


class TestLoadUserInterests:
    """Test load_user_interests function."""
    
    def create_test_config(self, config_data: dict) -> str:
        """Create a temporary config file for testing.
        
        Args:
            config_data: Configuration data to write to file
            
        Returns:
            Path to the created temporary file
        """
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        yaml.dump(config_data, temp_file, default_flow_style=False)
        temp_file.close()
        return temp_file.name
    
    def test_load_valid_configuration(self):
        """Test loading a valid configuration file."""
        config_data = {
            'research_areas': ['machine learning', 'ai'],
            'categories': ['cs.AI'],
            'keywords': ['neural networks'],
            'sources': {'papers_with_code': True},
            'filters': {'min_github_stars': 5},
            'email': {'max_papers_per_email': 10}
        }
        
        with patch.dict(os.environ, {
            'SMTP_SERVER': 'test.com',
            'SENDER_EMAIL': 'test@test.com',
            'SENDER_PASSWORD': 'pass',
            'RECEIVER_EMAIL': 'recv@test.com'
        }):
            config_path = self.create_test_config(config_data)
            try:
                interests = load_user_interests(config_path)
                
                assert interests.research_areas == ['machine learning', 'ai']
                assert interests.categories == ['cs.AI']
                assert interests.keywords == ['neural networks']
                assert interests.sources.papers_with_code is True
                assert interests.filters.min_github_stars == 5
                assert interests.email.max_papers_per_email == 10
            finally:
                os.unlink(config_path)
    
    def test_load_nonexistent_file(self):
        """Test loading from a file that doesn't exist."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_user_interests("/nonexistent/path/config.yml")
    
    def test_load_invalid_yaml(self):
        """Test loading from a file with invalid YAML."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        temp_file.write("invalid: yaml: content: [")  # Invalid YAML
        temp_file.close()
        
        try:
            with pytest.raises(yaml.YAMLError, match="invalid YAML format"):
                load_user_interests(temp_file.name)
        finally:
            os.unlink(temp_file.name)
    
    def test_load_empty_file(self):
        """Test loading from an empty file."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
        temp_file.write("")
        temp_file.close()
        
        try:
            with pytest.raises(ValueError, match="Configuration file is empty"):
                load_user_interests(temp_file.name)
        finally:
            os.unlink(temp_file.name)
    
    def test_load_invalid_structure(self):
        """Test loading from a file with invalid structure."""
        config_data = {
            'research_areas': ['machine learning'],  # Add valid interests to pass validation
            'filters': {
                'min_github_stars': 'not_a_number'  # Should be int
            }
        }
        
        config_path = self.create_test_config(config_data)
        try:
            with pytest.raises(ValueError, match="invalid structure"):
                load_user_interests(config_path)
        finally:
            os.unlink(config_path)


class TestCreateExampleConfig:
    """Test create_example_config function."""
    
    def test_creates_valid_config_file(self):
        """Test that create_example_config creates a valid YAML file."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.yml', delete=False)
        temp_file.close()
        
        try:
            create_example_config(temp_file.name)
            
            # Verify file exists and contains valid YAML
            assert os.path.exists(temp_file.name)
            
            with open(temp_file.name, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Verify required sections exist
            assert 'research_areas' in config_data
            assert 'categories' in config_data
            assert 'keywords' in config_data
            assert 'sources' in config_data
            assert 'filters' in config_data
            assert 'email' in config_data
            
            # Verify some specific values
            assert isinstance(config_data['research_areas'], list)
            assert len(config_data['research_areas']) > 0
            assert 'machine learning' in config_data['research_areas']
            
        finally:
            os.unlink(temp_file.name)


# Integration tests
class TestConfigurationIntegration:
    """Integration tests for the complete configuration system."""
    
    @patch.dict(os.environ, {
        'SMTP_SERVER': 'smtp.gmail.com',
        'SMTP_PORT': '587',
        'SENDER_EMAIL': 'sender@gmail.com', 
        'SENDER_PASSWORD': 'password123',
        'RECEIVER_EMAIL': 'receiver@gmail.com'
    })
    def test_full_configuration_workflow(self):
        """Test the complete workflow from YAML to validated config."""
        # Create example config
        temp_file = tempfile.NamedTemporaryFile(suffix='.yml', delete=False)
        temp_file.close()
        
        try:
            create_example_config(temp_file.name)
            interests = load_user_interests(temp_file.name)
            
            # Should validate successfully
            interests.validate()
            
            # Test functionality
            assert interests.matches_interests("deep learning research")
            assert not interests.matches_interests("unrelated topic")
            
            terms = interests.get_all_interest_terms()
            assert len(terms) > 0
            assert any('learning' in term.lower() for term in terms)
            
        finally:
            os.unlink(temp_file.name) 