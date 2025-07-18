"""Configuration management for user research interests.

This module handles loading and validating user preferences from YAML files.
It provides a clean interface for accessing configuration throughout the application.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger


@dataclass
class FilterConfig:
    """Configuration for filtering papers."""
    # New engagement-based filtering (from GitHub Actions)
    min_engagement_score: float = 10.0
    min_code_quality: float = 5.0
    require_code: bool = False
    
    # Legacy filtering (for backward compatibility)
    min_github_stars: int = 10
    max_days_old: int = 7
    min_paper_length: int = 4
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterConfig':
        """Create FilterConfig from dictionary, handling both old and new formats.
        
        Args:
            data: Dictionary with filter configuration
            
        Returns:
            FilterConfig instance
        """
        # Create instance with defaults
        instance = cls()
        
        # Update with provided values, handling both old and new parameter names
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
            else:
                logger.warning(f"Unknown filter parameter '{key}' ignored")
        
        return instance


@dataclass
class SourceConfig:
    """Configuration for paper sources."""
    papers_with_code: bool = True
    semantic_scholar: bool = True
    arxiv_recent: bool = True
    github_trending: bool = True


@dataclass
class EmailConfig:
    """Configuration for email preferences."""
    max_papers_per_email: int = 20
    include_abstracts: bool = True
    include_code_links: bool = True
    include_pdf_links: bool = True
    language: str = "English"
    
    # SMTP settings (from environment variables)
    smtp_server: str = ""
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    receiver_email: str = ""
    
    @classmethod
    def from_env(cls, email_config: Dict[str, Any]) -> 'EmailConfig':
        """Load email config combining YAML preferences and environment variables.
        
        Args:
            email_config: Email preferences from YAML file
            
        Returns:
            EmailConfig instance with combined settings
            
        Raises:
            ValueError: If environment variables have invalid values
        """
        # Parse SMTP port with error handling
        smtp_port_str = os.getenv('SMTP_PORT', '587')
        try:
            smtp_port = int(smtp_port_str)
            if smtp_port <= 0 or smtp_port > 65535:
                raise ValueError(f"SMTP_PORT must be between 1 and 65535, got: {smtp_port}")
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError(f"SMTP_PORT must be a number, got: '{smtp_port_str}'")
            raise
        
        return cls(
            # Preferences from YAML
            max_papers_per_email=email_config.get('max_papers_per_email', 20),
            include_abstracts=email_config.get('include_abstracts', True),
            include_code_links=email_config.get('include_code_links', True),
            include_pdf_links=email_config.get('include_pdf_links', True),
            language=email_config.get('language', 'English'),
            
            # SMTP settings from environment
            smtp_server=os.getenv('SMTP_SERVER', ''),
            smtp_port=smtp_port,
            sender_email=os.getenv('SENDER_EMAIL', ''),
            sender_password=os.getenv('SENDER_PASSWORD', ''),
            receiver_email=os.getenv('RECEIVER_EMAIL', '')
        )


@dataclass
class UserInterests:
    """User research interests and preferences."""
    research_areas: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    sources: SourceConfig = field(default_factory=SourceConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    
    def validate(self) -> None:
        """Validate the configuration for common issues.
        
        Raises:
            ValueError: If configuration has invalid values
        """
        if not self.research_areas and not self.categories and not self.keywords:
            raise ValueError(
                "Configuration Error: You must specify at least one research area, "
                "category, or keyword in config/user_interests.yml"
            )
            
        if self.filters.min_github_stars < 0:
            raise ValueError("Filter Error: min_github_stars cannot be negative")
            
        if self.filters.max_days_old <= 0:
            raise ValueError("Filter Error: max_days_old must be positive")
            
        if self.email.max_papers_per_email <= 0:
            raise ValueError("Email Error: max_papers_per_email must be positive")
            
        # Validate SMTP settings if email is enabled
        required_email_fields = [
            'smtp_server', 'sender_email', 'sender_password', 'receiver_email'
        ]
        missing_fields = [
            field for field in required_email_fields 
            if not getattr(self.email, field)
        ]
        if missing_fields:
            missing_upper = [field.upper() for field in missing_fields]
            raise ValueError(
                f"Email Configuration Error: Missing required environment variables: "
                f"{', '.join(missing_upper)}. "
                f"Please set these in your GitHub repository secrets."
            )
    
    def get_all_interest_terms(self) -> List[str]:
        """Get all interest terms for matching papers.
        
        Returns:
            Combined list of research areas, keywords, and categories
        """
        return self.research_areas + self.keywords + self.categories
    
    def matches_interests(self, text: str) -> bool:
        """Check if text matches any of the user's interests.
        
        Args:
            text: Text to check (paper title, abstract, etc.)
            
        Returns:
            True if text contains any interest terms
            
        Raises:
            TypeError: If text is None or not a string
        """
        if text is None:
            raise TypeError("Text cannot be None")
        if not isinstance(text, str):
            raise TypeError(f"Text must be a string, got {type(text)}")
            
        text_lower = text.lower()
        interest_terms = self.get_all_interest_terms()
        
        # Handle case where no interests are defined
        if not interest_terms:
            return False
        
        return any(
            term.lower() in text_lower 
            for term in interest_terms
            if term  # Skip empty terms
        )


def load_user_interests(config_path: Optional[str] = None) -> UserInterests:
    """Load user interests from YAML configuration file.
    
    Args:
        config_path: Path to configuration file. If None, uses default location.
                    Can also be set via USER_INTERESTS_CONFIG environment variable.
        
    Returns:
        UserInterests instance with loaded configuration
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If configuration is invalid
        yaml.YAMLError: If YAML file is malformed
    """
    if config_path is None:
        # Check for config path from environment variable first (GitHub Actions support)
        config_path = os.getenv('USER_INTERESTS_CONFIG')
    
    if config_path is None:
        # Default to config/user_interests.yml in project root
        # Try multiple possible locations for robustness
        current_file = Path(__file__).resolve()
        
        # First try: assume package structure (src/core/config.py)
        project_root = current_file.parent.parent.parent
        
        # Try dynamic config first (GitHub Actions), then fallback to static
        possible_paths = [
            project_root / "config" / "user_interests_dynamic.yml",  # GitHub Actions generated
            project_root / "config" / "user_interests.yml",
            Path.cwd() / "config" / "user_interests_dynamic.yml",
            Path.cwd() / "config" / "user_interests.yml"
        ]
        
        default_path = None
        for path in possible_paths:
            if path.exists():
                default_path = path
                break
        
        if default_path is None:
            # Use the primary default path for error message
            default_path = project_root / "config" / "user_interests.yml"
        
        config_path = default_path
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            f"Please create this file or copy from config/user_interests.yml.example"
        )
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(
            f"Configuration file has invalid YAML format: {config_path}\n"
            f"Error: {e}\n"
            f"Please check the file syntax and try again."
        )
    
    if not config_data:
        raise ValueError(f"Configuration file is empty: {config_path}")
    
    try:
        # Validate and extract configuration data with type checking
        research_areas = config_data.get('research_areas', [])
        categories = config_data.get('categories', [])
        keywords = config_data.get('keywords', [])
        
        # Ensure lists are actually lists
        if not isinstance(research_areas, list):
            raise ValueError("'research_areas' must be a list")
        if not isinstance(categories, list):
            raise ValueError("'categories' must be a list")  
        if not isinstance(keywords, list):
            raise ValueError("'keywords' must be a list")
        
        # Filter out None values and ensure all items are strings
        research_areas = [str(item) for item in research_areas if item is not None]
        categories = [str(item) for item in categories if item is not None]
        keywords = [str(item) for item in keywords if item is not None]
        
        # Create configuration objects
        sources_data = config_data.get('sources', {})
        filters_data = config_data.get('filters', {})
        email_data = config_data.get('email', {})
        
        if not isinstance(sources_data, dict):
            raise ValueError("'sources' must be a dictionary")
        if not isinstance(filters_data, dict):
            raise ValueError("'filters' must be a dictionary")
        if not isinstance(email_data, dict):
            raise ValueError("'email' must be a dictionary")
        
        sources = SourceConfig(**sources_data)
        filters = FilterConfig.from_dict(filters_data)
        email = EmailConfig.from_env(email_data)
        
        interests = UserInterests(
            research_areas=research_areas,
            categories=categories,
            keywords=keywords,
            sources=sources,
            filters=filters,
            email=email
        )
        
        # Validate configuration
        interests.validate()
        
        logger.info(f"Successfully loaded configuration from {config_path}")
        logger.info(f"Tracking {len(interests.research_areas)} research areas, "
                   f"{len(interests.categories)} categories, "
                   f"{len(interests.keywords)} keywords")
        
        return interests
        
    except TypeError as e:
        raise ValueError(
            f"Configuration file has invalid structure: {config_path}\n"
            f"Error: {e}\n"
            f"Please check the example configuration for the correct format."
        )


def create_example_config(output_path: str) -> None:
    """Create an example configuration file for new users.
    
    Args:
        output_path: Where to save the example configuration
    """
    example_config = {
        'research_areas': [
            'machine learning',
            'computer vision', 
            'natural language processing'
        ],
        'categories': [
            'cs.AI',
            'cs.LG', 
            'cs.CV'
        ],
        'keywords': [
            'neural networks',
            'deep learning',
            'transformers'
        ],
        'sources': {
            'papers_with_code': True,
            'semantic_scholar': True,
            'arxiv_recent': True,
            'github_trending': True
        },
        'filters': {
            'min_github_stars': 10,
            'max_days_old': 7,
            'require_code': False,
            'min_paper_length': 4
        },
        'email': {
            'max_papers_per_email': 20,
            'include_abstracts': True,
            'include_code_links': True,
            'include_pdf_links': True,
            'language': 'English'
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as file:
        yaml.dump(example_config, file, default_flow_style=False, indent=2)
    
    logger.info(f"Created example configuration at {output_path}") 