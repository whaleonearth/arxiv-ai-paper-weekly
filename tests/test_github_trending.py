"""Tests for GitHub trending repository analysis."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import List, Dict, Any

from src.integrations.github_trending import (
    GitHubRepository,
    GitHubTrendingAPI,
    GitHubPaperExtractor,
    GitHubTrendingConverter,
    discover_trending_papers_from_github
)
from src.data.paper_models import TrendingPaper, TrendingReason


class TestGitHubRepository:
    """Test GitHubRepository data class."""
    
    def test_repository_creation(self):
        """Test creating a repository object."""
        now = datetime.now()
        
        repo = GitHubRepository(
            full_name="test/repo",
            name="repo",
            description="Test repository",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=["machine-learning", "ai"],
            created_at=now,
            updated_at=now,
            pushed_at=now,
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[]
        )
        
        assert repo.full_name == "test/repo"
        assert repo.stars == 100
        assert repo.language == "Python"
        assert repo.topics == ["machine-learning", "ai"]


class TestGitHubTrendingAPI:
    """Test GitHub API client."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api = GitHubTrendingAPI(token="test_token")
        
    def test_initialization_with_token(self):
        """Test API initialization with token."""
        api = GitHubTrendingAPI(token="test_token")
        assert "Authorization" in api.session.headers
        assert api.session.headers["Authorization"] == "token test_token"
        
    def test_initialization_without_token(self):
        """Test API initialization without token."""
        with patch('src.integrations.github_trending.logger') as mock_logger:
            api = GitHubTrendingAPI()
            mock_logger.warning.assert_called_once()
            assert "Authorization" not in api.session.headers
    
    @patch('src.integrations.github_trending.time.sleep')
    @patch('requests.Session.get')
    def test_search_repositories_success(self, mock_get, mock_sleep):
        """Test successful repository search."""
        # Mock API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "test/repo",
                    "name": "repo",
                    "description": "Test repo",
                    "html_url": "https://github.com/test/repo",
                    "clone_url": "https://github.com/test/repo.git",
                    "stargazers_count": 100,
                    "forks_count": 20,
                    "language": "Python",
                    "topics": ["ml"],
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                    "pushed_at": "2024-01-01T00:00:00Z",
                    "open_issues_count": 5,
                    "has_wiki": True,
                    "has_pages": False,
                    "license": {"name": "MIT"}
                }
            ]
        }
        mock_get.return_value = mock_response
        
        repos = self.api.search_repositories("machine learning")
        
        assert len(repos) == 1
        assert repos[0].full_name == "test/repo"
        assert repos[0].stars == 100
        mock_sleep.assert_called_once()
    
    @patch('src.integrations.github_trending.time.sleep')
    @patch('requests.Session.get')
    def test_search_repositories_api_error(self, mock_get, mock_sleep):
        """Test handling of API errors."""
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("API Error")
        
        with patch('src.integrations.github_trending.logger') as mock_logger:
            repos = self.api.search_repositories("test")
            
            assert repos == []
            mock_logger.error.assert_called_once()
    
    def test_get_trending_ml_repositories(self):
        """Test getting trending ML repositories."""
        with patch.object(self.api, 'search_repositories') as mock_search:
            # Mock repository response
            mock_repo = GitHubRepository(
                full_name="test/ml-repo",
                name="ml-repo",
                description="ML repository",
                html_url="https://github.com/test/ml-repo",
                clone_url="https://github.com/test/ml-repo.git",
                stars=200,
                forks=50,
                language="Python",
                topics=["machine-learning"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                pushed_at=datetime.now(),
                open_issues=10,
                has_wiki=True,
                has_pages=False,
                license_name="MIT",
                arxiv_links=[],
                paper_references=[]
            )
            mock_search.return_value = [mock_repo]
            
            repos = self.api.get_trending_ml_repositories(days_back=7)
            
            # Should be called multiple times for different ML queries
            assert mock_search.call_count > 0
            assert len(repos) >= 1
    
    @patch('src.integrations.github_trending.time.sleep')
    @patch('requests.Session.get')
    def test_fetch_readme_content_success(self, mock_get, mock_sleep):
        """Test successful README fetching."""
        import base64
        
        readme_content = "# Test Repository\nThis is a test."
        encoded_content = base64.b64encode(readme_content.encode()).decode()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": encoded_content,
            "encoding": "base64"
        }
        mock_get.return_value = mock_response
        
        repo = GitHubRepository(
            full_name="test/repo",
            name="repo", 
            description="Test",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[]
        )
        
        content = self.api.fetch_readme_content(repo)
        
        assert content == readme_content
        assert repo.readme_content == readme_content
    
    @patch('src.integrations.github_trending.time.sleep')
    @patch('requests.Session.get')
    def test_fetch_readme_content_not_found(self, mock_get, mock_sleep):
        """Test README not found."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        repo = GitHubRepository(
            full_name="test/repo",
            name="repo",
            description="Test",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[]
        )
        
        content = self.api.fetch_readme_content(repo)
        assert content is None
    
    def test_parse_repository_success(self):
        """Test successful repository parsing."""
        item = {
            "full_name": "test/repo",
            "name": "repo",
            "description": "Test repository",
            "html_url": "https://github.com/test/repo",
            "clone_url": "https://github.com/test/repo.git",
            "stargazers_count": 100,
            "forks_count": 20,
            "language": "Python",
            "topics": ["machine-learning"],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2024-01-01T00:00:00Z",
            "open_issues_count": 5,
            "has_wiki": True,
            "has_pages": False,
            "license": {"name": "MIT"}
        }
        
        repo = self.api._parse_repository(item)
        
        assert repo is not None
        assert repo.full_name == "test/repo"
        assert repo.stars == 100
        assert repo.license_name == "MIT"
        assert isinstance(repo.created_at, datetime)
    
    def test_parse_repository_missing_license(self):
        """Test parsing repository without license."""
        item = {
            "full_name": "test/repo",
            "name": "repo", 
            "description": "Test repository",
            "html_url": "https://github.com/test/repo",
            "clone_url": "https://github.com/test/repo.git",
            "stargazers_count": 100,
            "forks_count": 20,
            "language": "Python",
            "topics": [],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "pushed_at": "2024-01-01T00:00:00Z",
            "open_issues_count": 5,
            "has_wiki": True,
            "has_pages": False,
            "license": None
        }
        
        repo = self.api._parse_repository(item)
        
        assert repo is not None
        assert repo.license_name is None
    
    def test_parse_repository_error(self):
        """Test handling of parsing errors."""
        item = {"invalid": "data"}  # Missing required fields
        
        with patch('src.integrations.github_trending.logger') as mock_logger:
            repo = self.api._parse_repository(item)
            
            assert repo is None
            mock_logger.error.assert_called_once()
    
    def test_remove_duplicate_repos(self):
        """Test duplicate repository removal."""
        repo1 = GitHubRepository(
            full_name="test/repo1",
            name="repo1",
            description="Test",
            html_url="https://github.com/test/repo1",
            clone_url="https://github.com/test/repo1.git",
            stars=100,
            forks=20,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[]
        )
        
        repo2 = GitHubRepository(
            full_name="test/repo1",  # Duplicate
            name="repo1",
            description="Test duplicate",
            html_url="https://github.com/test/repo1",
            clone_url="https://github.com/test/repo1.git",
            stars=200,
            forks=30,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=3,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[]
        )
        
        repo3 = GitHubRepository(
            full_name="test/repo2",  # Different repo
            name="repo2",
            description="Test",
            html_url="https://github.com/test/repo2",
            clone_url="https://github.com/test/repo2.git",
            stars=50,
            forks=10,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=2,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[]
        )
        
        repos = [repo1, repo2, repo3]
        unique_repos = self.api._remove_duplicate_repos(repos)
        
        assert len(unique_repos) == 2
        assert unique_repos[0].full_name == "test/repo1"
        assert unique_repos[1].full_name == "test/repo2"


class TestGitHubPaperExtractor:
    """Test paper reference extraction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = GitHubPaperExtractor()
        self.sample_repo = GitHubRepository(
            full_name="test/repo",
            name="repo",
            description="Implementation of arXiv:2024.1234",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=["machine-learning"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[],
            readme_content="# Test Repo\nBased on https://arxiv.org/abs/2024.5678"
        )
    
    def test_extract_arxiv_references_from_description(self):
        """Test extracting arXiv IDs from description."""
        arxiv_ids = self.extractor.extract_arxiv_references(self.sample_repo)
        
        assert "2024.1234" in arxiv_ids
        assert "2024.5678" in arxiv_ids
        assert len(arxiv_ids) == 2
    
    def test_extract_arxiv_references_various_formats(self):
        """Test extracting arXiv IDs from various formats."""
        repo = GitHubRepository(
            full_name="test/repo",
            name="repo",
            description="Test",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[],
            readme_content="""
            Links to papers:
            - https://arxiv.org/abs/2024.1234
            - https://arxiv.org/pdf/2024.5678.pdf
            - arXiv:2024.9999
            - See arxiv.org/abs/2024.1111
            """
        )
        
        arxiv_ids = self.extractor.extract_arxiv_references(repo)
        
        expected_ids = {"2024.1234", "2024.5678", "2024.9999", "2024.1111"}
        assert set(arxiv_ids) == expected_ids
    
    def test_extract_arxiv_references_no_matches(self):
        """Test when no arXiv references found."""
        repo = GitHubRepository(
            full_name="test/repo",
            name="repo",
            description="Just a test repository",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[],
            readme_content="No papers here"
        )
        
        arxiv_ids = self.extractor.extract_arxiv_references(repo)
        assert arxiv_ids == []
    
    def test_extract_paper_references(self):
        """Test extracting general paper references."""
        repo = GitHubRepository(
            full_name="test/repo",
            name="repo",
            description="Test",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[],
            readme_content="""
            # Implementation
            
            [Original Paper](https://example.com)
            Paper: Attention Is All You Need
            Based on the paper "Transformer Networks for Language Understanding"
            Implements "BERT: Pre-training of Deep Bidirectional Transformers"
            """
        )
        
        references = self.extractor.extract_paper_references(repo)
        
        assert "Attention Is All You Need" in references
        assert "Transformer Networks for Language Understanding" in references
        assert "BERT: Pre-training of Deep Bidirectional Transformers" in references
        assert len([r for r in references if len(r) > 10]) >= 3
    
    def test_extract_paper_references_filters_short(self):
        """Test that short references are filtered out."""
        repo = GitHubRepository(
            full_name="test/repo",
            name="repo",
            description="Test",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[],
            readme_content="Paper: AI\nPaper: This is a long enough paper title"
        )
        
        references = self.extractor.extract_paper_references(repo)
        
        assert "AI" not in references
        assert "This is a long enough paper title" in references


class TestGitHubTrendingConverter:
    """Test conversion of repositories to trending papers."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.api = Mock(spec=GitHubTrendingAPI)
        self.extractor = Mock(spec=GitHubPaperExtractor)
        self.converter = GitHubTrendingConverter(self.api, self.extractor)
    
    def test_repository_to_trending_paper_with_arxiv(self):
        """Test converting repository with arXiv links."""
        now = datetime.now()
        repo = GitHubRepository(
            full_name="test/paper-implementation",
            name="paper-implementation",
            description="Implementation of attention mechanism",
            html_url="https://github.com/test/paper-implementation",
            clone_url="https://github.com/test/paper-implementation.git",
            stars=500,
            forks=100,
            language="Python",
            topics=["machine-learning", "transformer"],
            created_at=now - timedelta(days=10),
            updated_at=now,
            pushed_at=now - timedelta(days=1),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[],
            readme_content="# Implementation\nBased on attention paper"
        )
        
        # Mock extractor returns
        self.extractor.extract_arxiv_references.return_value = ["2024.1234"]
        self.extractor.extract_paper_references.return_value = ["Attention Is All You Need"]
        
        paper = self.converter.repository_to_trending_paper(repo)
        
        assert paper is not None
        assert paper.arxiv_id == "2024.1234"
        assert paper.discovery_source == "github_trending"
        assert paper.primary_repository is not None
        assert paper.primary_repository.stars == 500
        assert TrendingReason.HIGH_GITHUB_ACTIVITY in paper.trending_reasons
    
    def test_repository_to_trending_paper_no_papers(self):
        """Test converting repository without paper references."""
        repo = GitHubRepository(
            full_name="test/random-project",
            name="random-project",
            description="Just a random project",
            html_url="https://github.com/test/random-project",
            clone_url="https://github.com/test/random-project.git",
            stars=10,
            forks=2,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=1,
            has_wiki=False,
            has_pages=False,
            license_name=None,
            arxiv_links=[],
            paper_references=[],
            readme_content="Just a random project"
        )
        
        # Mock extractor returns no papers
        self.extractor.extract_arxiv_references.return_value = []
        self.extractor.extract_paper_references.return_value = []
        
        paper = self.converter.repository_to_trending_paper(repo)
        
        assert paper is None
    
    def test_has_tests_detection(self):
        """Test detection of test presence."""
        repo = GitHubRepository(
            full_name="test/repo",
            name="repo",
            description="Test",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=["testing"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[],
            readme_content="Uses pytest for testing"
        )
        
        has_tests = self.converter._has_tests(repo)
        assert has_tests is True
    
    def test_has_examples_detection(self):
        """Test detection of examples."""
        repo = GitHubRepository(
            full_name="test/repo",
            name="repo",
            description="Test",
            html_url="https://github.com/test/repo",
            clone_url="https://github.com/test/repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[],
            readme_content="Check out the examples/ directory for tutorials"
        )
        
        has_examples = self.converter._has_examples(repo)
        assert has_examples is True
    
    def test_extract_categories(self):
        """Test category extraction from repository."""
        repo = GitHubRepository(
            full_name="test/ml-repo",
            name="ml-repo",
            description="Machine learning and computer vision",
            html_url="https://github.com/test/ml-repo",
            clone_url="https://github.com/test/ml-repo.git",
            stars=100,
            forks=20,
            language="Python",
            topics=["nlp", "ai"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            pushed_at=datetime.now(),
            open_issues=5,
            has_wiki=True,
            has_pages=False,
            license_name="MIT",
            arxiv_links=[],
            paper_references=[]
        )
        
        categories = self.converter._extract_categories(repo)
        
        expected_categories = {"cs.LG", "cs.CV", "cs.CL", "cs.AI"}
        assert set(categories) == expected_categories


@patch('src.integrations.github_trending.GitHubTrendingAPI')
@patch('src.integrations.github_trending.GitHubPaperExtractor')
@patch('src.integrations.github_trending.GitHubTrendingConverter')
def test_discover_trending_papers_from_github(mock_converter_class, mock_extractor_class, mock_api_class):
    """Test the main discovery function."""
    # Set up mocks
    mock_api = Mock()
    mock_extractor = Mock()
    mock_converter = Mock()
    
    mock_api_class.return_value = mock_api
    mock_extractor_class.return_value = mock_extractor
    mock_converter_class.return_value = mock_converter
    
    # Mock repository
    mock_repo = Mock()
    mock_api.get_trending_ml_repositories.return_value = [mock_repo]
    
    # Mock paper conversion
    mock_paper = Mock()
    mock_paper.trending_score = 85.0
    mock_converter.repository_to_trending_paper.return_value = mock_paper
    
    # Call function
    papers = discover_trending_papers_from_github(
        github_token="test_token",
        days_back=7,
        max_papers=50
    )
    
    # Verify calls
    mock_api_class.assert_called_once_with(token="test_token")
    mock_api.get_trending_ml_repositories.assert_called_once_with(days_back=7)
    mock_converter.repository_to_trending_paper.assert_called_once_with(mock_repo)
    
    # Verify result
    assert len(papers) == 1
    assert papers[0] == mock_paper


@patch('src.integrations.github_trending.GitHubTrendingAPI')
def test_discover_trending_papers_from_github_error(mock_api_class):
    """Test error handling in discovery function."""
    mock_api_class.side_effect = Exception("API Error")
    
    with patch('src.integrations.github_trending.logger') as mock_logger:
        papers = discover_trending_papers_from_github()
        
        assert papers == []
        mock_logger.error.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 