"""Tests for Papers with Code API integration.

This module tests the Papers with Code integration including API client,
data conversion, and trending paper discovery functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import requests

from src.integrations.papers_with_code import (
    PapersWithCodeAPI,
    PapersWithCodeConfig,
    PapersWithCodeConverter,
    discover_trending_papers
)
from src.data.paper_models import TrendingPaper, CodeRepository, EngagementMetrics, TrendingReason


class TestPapersWithCodeConfig:
    """Test PapersWithCodeConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = PapersWithCodeConfig()
        
        assert config.base_url == "https://paperswithcode.com/api/v1"
        assert config.request_timeout == 30
        assert config.max_retries == 3
        assert config.papers_per_request == 50
        assert config.rate_limit_delay == 1.0
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = PapersWithCodeConfig(
            base_url="https://custom.api.com",
            request_timeout=60,
            max_retries=5,
            papers_per_request=100,
            rate_limit_delay=2.0
        )
        
        assert config.base_url == "https://custom.api.com"
        assert config.request_timeout == 60
        assert config.max_retries == 5
        assert config.papers_per_request == 100
        assert config.rate_limit_delay == 2.0


class TestPapersWithCodeAPI:
    """Test PapersWithCodeAPI client."""
    
    def setup_method(self):
        """Setup test data before each test."""
        self.config = PapersWithCodeConfig(rate_limit_delay=0.0)  # No delay for tests
        self.api = PapersWithCodeAPI(self.config)
        
        # Sample API response data
        self.sample_paper = {
            'id': 'test-paper-1',
            'title': 'Test Paper: A Novel Approach',
            'abstract': 'This paper presents a novel approach to testing...',
            'authors': ['Alice Smith', 'Bob Jones'],
            'arxiv_id': '2401.12345',
            'published': '2024-01-15T10:00:00Z',
            'repositories': [
                {
                    'url': 'https://github.com/test/repo1',
                    'name': 'repo1',
                    'description': 'Test repository with documentation and examples',
                    'stars': 250,
                    'forks': 45,
                    'language': 'Python',
                    'license': {'name': 'MIT'}
                }
            ],
            'tasks': ['Image Classification', 'Computer Vision']
        }
        
        self.sample_api_response = {
            'results': [self.sample_paper],
            'next': None,
            'count': 1
        }
    
    def test_api_initialization(self):
        """Test API client initialization."""
        api = PapersWithCodeAPI()
        assert api.config.base_url == "https://paperswithcode.com/api/v1"
        assert api.session is not None
        
        # Test with custom config
        custom_config = PapersWithCodeConfig(base_url="https://custom.com")
        api_custom = PapersWithCodeAPI(custom_config)
        assert api_custom.config.base_url == "https://custom.com"
    
    @patch('requests.Session.get')
    def test_make_request_success(self, mock_get):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {'test': 'data'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.api._make_request('papers/')
        
        assert result == {'test': 'data'}
        mock_get.assert_called_once_with(
            'https://paperswithcode.com/api/v1/papers/',
            params=None,
            timeout=30
        )
    
    @patch('requests.Session.get')
    def test_make_request_failure(self, mock_get):
        """Test API request failure."""
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        result = self.api._make_request('papers/')
        
        assert result is None
    
    @patch('requests.Session.get')
    def test_make_request_with_params(self, mock_get):
        """Test API request with parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {'test': 'data'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        params = {'page': 1, 'ordering': '-github_stars'}
        result = self.api._make_request('papers/', params)
        
        assert result == {'test': 'data'}
        mock_get.assert_called_once_with(
            'https://paperswithcode.com/api/v1/papers/',
            params=params,
            timeout=30
        )
    
    def test_is_trending_paper_with_stars(self):
        """Test trending paper detection with sufficient stars."""
        paper = {
            'repositories': [
                {'stars': 100},
                {'stars': 5}
            ]
        }
        
        result = self.api._is_trending_paper(paper, days_back=7, min_stars=50)
        assert result is True
    
    def test_is_trending_paper_insufficient_stars(self):
        """Test trending paper detection with insufficient stars."""
        paper = {
            'repositories': [
                {'stars': 10},
                {'stars': 5}
            ]
        }
        
        result = self.api._is_trending_paper(paper, days_back=7, min_stars=50)
        assert result is False
    
    def test_is_trending_paper_no_repositories(self):
        """Test trending paper detection with no repositories."""
        paper = {'repositories': []}
        
        result = self.api._is_trending_paper(paper, days_back=7, min_stars=10)
        assert result is False
    
    @patch('time.sleep')
    @patch.object(PapersWithCodeAPI, '_make_request')
    def test_get_trending_papers(self, mock_request, mock_sleep):
        """Test getting trending papers."""
        # Mock API responses
        mock_request.side_effect = [
            self.sample_api_response,  # First page
            {'results': [], 'next': None}  # Second page (empty)
        ]
        
        papers = self.api.get_trending_papers(days_back=7, min_stars=10)
        
        assert len(papers) == 1
        assert papers[0]['title'] == 'Test Paper: A Novel Approach'
        
        # Verify API calls
        assert mock_request.call_count == 1
        mock_request.assert_called_with('papers/', {
            'page': 1,
            'ordering': '-github_stars',
            'page_size': 50
        })
    
    @patch.object(PapersWithCodeAPI, '_make_request')
    def test_get_paper_details(self, mock_request):
        """Test getting detailed paper information."""
        mock_request.return_value = self.sample_paper
        
        result = self.api.get_paper_details('test-paper-1')
        
        assert result == self.sample_paper
        mock_request.assert_called_once_with('papers/test-paper-1/')
    
    @patch.object(PapersWithCodeAPI, '_make_request')
    def test_get_paper_repositories(self, mock_request):
        """Test getting paper repositories."""
        repo_response = {
            'results': [
                {
                    'url': 'https://github.com/test/repo',
                    'stars': 100
                }
            ]
        }
        mock_request.return_value = repo_response
        
        result = self.api.get_paper_repositories('test-paper-1')
        
        assert len(result) == 1
        assert result[0]['url'] == 'https://github.com/test/repo'
        mock_request.assert_called_once_with('papers/test-paper-1/repositories/')


class TestPapersWithCodeConverter:
    """Test PapersWithCodeConverter functionality."""
    
    def setup_method(self):
        """Setup test data before each test."""
        self.converter = PapersWithCodeConverter()
        
        self.sample_pwc_paper = {
            'title': 'Test Paper: Novel Deep Learning',
            'abstract': 'This paper presents novel deep learning techniques...',
            'authors': ['Alice Smith', 'Bob Jones', 'Carol White'],
            'arxiv_id': '2401.12345',
            'published': '2024-01-15T10:00:00Z',
            'repositories': [
                {
                    'url': 'https://github.com/test/repo1',
                    'name': 'repo1',
                    'description': 'Main implementation with documentation and examples',
                    'stars': 500,
                    'forks': 75,
                    'language': 'Python',
                    'license': {'name': 'MIT'}
                },
                {
                    'url': 'https://github.com/test/repo2', 
                    'name': 'repo2',
                    'description': 'Alternative implementation',
                    'stars': 150,
                    'forks': 20,
                    'language': 'PyTorch'
                }
            ],
            'tasks': ['Image Classification', 'Computer Vision'],
            'citations': 25
        }
    
    def test_convert_paper_basic(self):
        """Test basic paper conversion."""
        paper = self.converter.convert_paper(self.sample_pwc_paper)
        
        assert isinstance(paper, TrendingPaper)
        assert paper.title == 'Test Paper: Novel Deep Learning'
        assert paper.abstract == 'This paper presents novel deep learning techniques...'
        assert paper.authors == ['Alice Smith', 'Bob Jones', 'Carol White']
        assert paper.arxiv_id == '2401.12345'
        assert paper.arxiv_url == 'https://arxiv.org/abs/2401.12345'
        assert paper.pdf_url == 'https://arxiv.org/pdf/2401.12345.pdf'
        assert paper.categories == ['Image Classification', 'Computer Vision']
        assert paper.discovery_source == "papers_with_code"
    
    def test_convert_paper_with_repositories(self):
        """Test paper conversion with repositories."""
        paper = self.converter.convert_paper(self.sample_pwc_paper)
        
        # Should have primary repository and additional ones
        assert paper.primary_repository is not None
        assert paper.primary_repository.url == 'https://github.com/test/repo1'
        assert paper.primary_repository.stars == 500
        assert paper.primary_repository.license_type == 'MIT'
        
        assert len(paper.additional_repositories) == 1
        assert paper.additional_repositories[0].url == 'https://github.com/test/repo2'
        assert paper.additional_repositories[0].stars == 150
    
    def test_convert_paper_engagement_metrics(self):
        """Test engagement metrics calculation."""
        paper = self.converter.convert_paper(self.sample_pwc_paper)
        
        # Should sum up GitHub metrics from all repos
        assert paper.engagement.github_stars == 650  # 500 + 150
        assert paper.engagement.github_forks == 95   # 75 + 20
        assert paper.engagement.citation_count == 25
        assert paper.engagement.days_since_publication > 0
    
    def test_convert_paper_trending_reasons(self):
        """Test trending reasons determination."""
        paper = self.converter.convert_paper(self.sample_pwc_paper)
        
        # Should have multiple trending reasons
        assert TrendingReason.HIGH_GITHUB_ACTIVITY in paper.trending_reasons
        assert TrendingReason.CODE_QUALITY in paper.trending_reasons
        # May have others depending on current date vs publication date
    
    def test_convert_paper_publication_date(self):
        """Test publication date parsing."""
        paper = self.converter.convert_paper(self.sample_pwc_paper)
        
        assert paper.publication_date is not None
        assert paper.publication_date.year == 2024
        assert paper.publication_date.month == 1
        assert paper.publication_date.day == 15
    
    def test_convert_paper_authors_string(self):
        """Test author parsing when authors is a string."""
        paper_data = self.sample_pwc_paper.copy()
        paper_data['authors'] = 'Single Author'
        
        paper = self.converter.convert_paper(paper_data)
        
        assert paper.authors == ['Single Author']
    
    def test_convert_paper_authors_dict_list(self):
        """Test author parsing when authors is list of dicts."""
        paper_data = self.sample_pwc_paper.copy()
        paper_data['authors'] = [
            {'name': 'Alice Smith'},
            {'name': 'Bob Jones'}
        ]
        
        paper = self.converter.convert_paper(paper_data)
        
        assert paper.authors == ['Alice Smith', 'Bob Jones']
    
    def test_convert_paper_no_arxiv(self):
        """Test paper conversion without arXiv ID."""
        paper_data = self.sample_pwc_paper.copy()
        del paper_data['arxiv_id']
        
        paper = self.converter.convert_paper(paper_data)
        
        assert paper.arxiv_id is None
        assert paper.arxiv_url is None
        assert paper.pdf_url is None
    
    def test_convert_repositories(self):
        """Test repository conversion."""
        repos = self.converter._convert_repositories(self.sample_pwc_paper['repositories'])
        
        assert len(repos) == 2
        
        # Should be sorted by stars (highest first)
        assert repos[0].stars == 500
        assert repos[1].stars == 150
        
        # Check repository details
        assert repos[0].url == 'https://github.com/test/repo1'
        assert repos[0].name == 'repo1'
        assert repos[0].primary_language == 'Python'
        assert repos[0].license_type == 'MIT'
        assert repos[0].has_documentation is True  # Based on description heuristic
        assert repos[0].has_examples is True       # Based on description heuristic
    
    def test_has_documentation_heuristic(self):
        """Test documentation detection heuristic."""
        # Should detect documentation indicators
        repo_with_docs = {
            'description': 'Implementation with comprehensive documentation',
            'name': 'test-repo'
        }
        assert self.converter._has_documentation(repo_with_docs) is True
        
        # Should not detect documentation
        repo_without_docs = {
            'description': 'Simple implementation',
            'name': 'test-repo'
        }
        assert self.converter._has_documentation(repo_without_docs) is False
    
    def test_has_tests_heuristic(self):
        """Test tests detection heuristic."""
        # Popular repo should be assumed to have tests
        popular_repo = {'stars': 500}
        assert self.converter._has_tests(popular_repo) is True
        
        # Unpopular repo assumed not to have tests
        unpopular_repo = {'stars': 50}
        assert self.converter._has_tests(unpopular_repo) is False
    
    def test_has_examples_heuristic(self):
        """Test examples detection heuristic."""
        # Should detect example indicators
        repo_with_examples = {
            'description': 'PyTorch implementation with tutorial and examples'
        }
        assert self.converter._has_examples(repo_with_examples) is True
        
        # Should not detect examples
        repo_without_examples = {
            'description': 'Basic implementation'
        }
        assert self.converter._has_examples(repo_without_examples) is False
    
    def test_convert_paper_error_handling(self):
        """Test error handling in paper conversion."""
        # Invalid paper data should still create a paper but with empty/default values
        invalid_paper = {'invalid': 'data'}
        
        paper = self.converter.convert_paper(invalid_paper)
        
        # Should create a paper with empty/default values rather than failing
        assert isinstance(paper, TrendingPaper)
        assert paper.title == ''
        assert paper.abstract == ''
        assert paper.authors == []
    
    def test_calculate_engagement_metrics_edge_cases(self):
        """Test engagement metrics calculation with edge cases."""
        # Paper without repositories
        paper_data = {
            'title': 'Test',
            'abstract': 'Test',
            'authors': []
        }
        
        engagement = self.converter._calculate_engagement_metrics(paper_data, [])
        
        assert engagement.github_stars == 0
        assert engagement.github_forks == 0
        assert engagement.citation_count == 0
        assert engagement.days_since_publication == 0


@patch('time.sleep')  # Mock sleep to speed up tests
class TestDiscoverTrendingPapers:
    """Test the main discover_trending_papers function."""
    
    @patch.object(PapersWithCodeAPI, 'get_trending_papers')
    def test_discover_trending_papers_success(self, mock_get_papers, mock_sleep):
        """Test successful trending papers discovery."""
        # Mock API response
        sample_pwc_paper = {
            'title': 'Test Paper',
            'abstract': 'Test abstract',
            'authors': ['Author 1'],
            'repositories': [
                {
                    'url': 'https://github.com/test/repo',
                    'name': 'repo',
                    'description': 'Test repo',
                    'stars': 100,
                    'forks': 20
                }
            ]
        }
        mock_get_papers.return_value = [sample_pwc_paper]
        
        papers = discover_trending_papers(max_papers=10)
        
        assert len(papers) == 1
        assert isinstance(papers[0], TrendingPaper)
        assert papers[0].title == 'Test Paper'
        assert papers[0].discovery_source == "papers_with_code"
    
    @patch.object(PapersWithCodeAPI, 'get_trending_papers')
    def test_discover_trending_papers_empty_result(self, mock_get_papers, mock_sleep):
        """Test trending papers discovery with empty result."""
        mock_get_papers.return_value = []
        
        papers = discover_trending_papers()
        
        assert len(papers) == 0
    
    @patch.object(PapersWithCodeAPI, 'get_trending_papers')
    def test_discover_trending_papers_with_config(self, mock_get_papers, mock_sleep):
        """Test trending papers discovery with custom config."""
        mock_get_papers.return_value = []
        
        config = PapersWithCodeConfig(request_timeout=60)
        papers = discover_trending_papers(
            config=config,
            days_back=14,
            min_stars=50,
            max_papers=25
        )
        
        assert len(papers) == 0
        # Verify API was called with correct parameters
        mock_get_papers.assert_called_once_with(14, 50)
    
    @patch.object(PapersWithCodeAPI, 'get_trending_papers')
    def test_discover_trending_papers_sorting(self, mock_get_papers, mock_sleep):
        """Test that papers are sorted by trending score."""
        # Create papers with different scores
        paper1 = {
            'title': 'Low Score Paper',
            'abstract': 'Abstract 1',
            'authors': ['Author 1'],
            'repositories': [{'url': 'https://github.com/test/repo1', 'name': 'repo1', 'stars': 10, 'forks': 2}]
        }
        paper2 = {
            'title': 'High Score Paper', 
            'abstract': 'Abstract 2',
            'authors': ['Author 2'],
            'repositories': [{'url': 'https://github.com/test/repo2', 'name': 'repo2', 'stars': 1000, 'forks': 200}]
        }
        
        mock_get_papers.return_value = [paper1, paper2]
        
        papers = discover_trending_papers()
        
        assert len(papers) == 2
        # Higher scored paper should be first
        assert papers[0].title == 'High Score Paper'
        assert papers[1].title == 'Low Score Paper'
        assert papers[0].trending_score > papers[1].trending_score 