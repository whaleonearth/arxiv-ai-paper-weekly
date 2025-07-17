"""Tests for the unified paper discovery service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List

from src.services.paper_discovery import (
    PaperDiscoveryService,
    PaperInterestMatcher,
    PaperDeduplicator,
    DiscoveryConfig,
    DiscoveryResult,
    create_discovery_service
)
from src.core.config import UserInterests
from src.data.paper_models import TrendingPaper, CodeRepository, EngagementMetrics, TrendingReason


class TestDiscoveryConfig:
    """Test discovery configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DiscoveryConfig()
        
        assert config.use_papers_with_code is True
        assert config.use_github_trending is True
        assert config.days_back == 7
        assert config.max_papers_per_source == 50
        assert config.engagement_weight == 0.5
        assert config.interest_weight == 0.3
        assert config.code_quality_weight == 0.2
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = DiscoveryConfig(
            use_papers_with_code=False,
            github_token="test_token",
            days_back=14,
            max_total_papers=200,
            engagement_weight=0.6
        )
        
        assert config.use_papers_with_code is False
        assert config.github_token == "test_token"
        assert config.days_back == 14
        assert config.max_total_papers == 200
        assert config.engagement_weight == 0.6


class TestPaperInterestMatcher:
    """Test paper interest matching."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_interests = UserInterests(
            research_areas=["machine learning", "computer vision"],
            categories=["cs.LG", "cs.CV"],
            keywords=["neural networks", "deep learning"]
        )
        self.matcher = PaperInterestMatcher(self.user_interests)
    
    def test_calculate_interest_score_high_match(self):
        """Test high interest score calculation."""
        paper = TrendingPaper(
            title="Deep Learning for Computer Vision",
            abstract="This paper presents neural networks for computer vision tasks using machine learning techniques.",
            authors=["Author 1"],
            categories=["cs.CV", "cs.LG"]
        )
        
        score = self.matcher.calculate_interest_score(paper)
        
        assert score > 0.7  # Should be high match
        assert paper.interest_match_score == score
        assert len(paper.matched_interests) > 0
    
    def test_calculate_interest_score_low_match(self):
        """Test low interest score calculation."""
        paper = TrendingPaper(
            title="Quantum Computing Algorithms",
            abstract="This paper discusses quantum algorithms for optimization problems.",
            authors=["Author 1"],
            categories=["quant-ph"]
        )
        
        score = self.matcher.calculate_interest_score(paper)
        
        assert score < 0.3  # Should be low match
        assert paper.interest_match_score == score
    
    def test_calculate_interest_score_no_preferences(self):
        """Test scoring with no user preferences."""
        empty_interests = UserInterests(
            research_areas=[],
            categories=[],
            keywords=[]
        )
        matcher = PaperInterestMatcher(empty_interests)
        
        paper = TrendingPaper(
            title="Any Paper",
            abstract="Any content",
            authors=["Author 1"]
        )
        
        score = matcher.calculate_interest_score(paper)
        
        assert score == 0.5  # Should be neutral
    
    def test_match_research_areas(self):
        """Test research area matching."""
        paper = TrendingPaper(
            title="Machine Learning Advances",
            abstract="Recent advances in machine learning",
            authors=["Author 1"]
        )
        
        score = self.matcher._match_research_areas(paper)
        assert score > 0  # Should find "machine learning"
    
    def test_match_categories(self):
        """Test category matching."""
        paper = TrendingPaper(
            title="Test Paper",
            abstract="Test abstract",
            authors=["Author 1"],
            categories=["cs.LG", "cs.AI"]
        )
        
        score = self.matcher._match_categories(paper)
        assert score > 0  # Should match cs.LG
    
    def test_match_keywords(self):
        """Test keyword matching."""
        paper = TrendingPaper(
            title="Neural Networks for Classification",
            abstract="Deep learning approaches using neural networks",
            authors=["Author 1"]
        )
        
        score = self.matcher._match_keywords(paper)
        assert score > 0  # Should match "neural networks" and "deep learning"
    
    def test_get_matched_interests(self):
        """Test getting matched interests."""
        paper = TrendingPaper(
            title="Computer Vision with Neural Networks",
            abstract="Machine learning paper about computer vision using neural networks",
            authors=["Author 1"],
            categories=["cs.CV"]
        )
        
        matched = self.matcher._get_matched_interests(paper)
        
        expected_matches = {"computer vision", "machine learning", "neural networks", "cs.CV"}
        assert set(matched) == expected_matches


class TestPaperDeduplicator:
    """Test paper deduplication."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.deduplicator = PaperDeduplicator()
    
    def test_deduplicate_papers_empty_list(self):
        """Test deduplication with empty list."""
        result = self.deduplicator.deduplicate_papers([])
        assert result == []
    
    def test_deduplicate_papers_arxiv_duplicates(self):
        """Test removing papers with same arXiv ID."""
        paper1 = TrendingPaper(
            title="Paper A",
            abstract="Abstract A",
            authors=["Author 1"],
            arxiv_id="2024.1234",
            trending_score=80.0
        )
        
        paper2 = TrendingPaper(
            title="Paper A - Implementation",
            abstract="Implementation of Paper A",
            authors=["Author 2"],
            arxiv_id="2024.1234",  # Same arXiv ID
            trending_score=90.0  # Higher score
        )
        
        papers = [paper1, paper2]
        result = self.deduplicator.deduplicate_papers(papers)
        
        assert len(result) == 1
        assert result[0] == paper2  # Should keep higher scoring one
    
    def test_deduplicate_papers_title_similarity(self):
        """Test removing papers with similar titles."""
        paper1 = TrendingPaper(
            title="Attention is All You Need",
            abstract="Transformer paper",
            authors=["Author 1"],
            trending_score=80.0
        )
        
        paper2 = TrendingPaper(
            title="Attention Is All You Need",  # Very similar title
            abstract="Different abstract",
            authors=["Author 2"],
            trending_score=90.0
        )
        
        papers = [paper1, paper2]
        result = self.deduplicator.deduplicate_papers(papers)
        
        assert len(result) == 1
        assert result[0] == paper2  # Should keep higher scoring one
    
    def test_deduplicate_papers_no_duplicates(self):
        """Test with no duplicates."""
        paper1 = TrendingPaper(
            title="Paper A",
            abstract="Abstract A",
            authors=["Author 1"],
            trending_score=80.0
        )
        
        paper2 = TrendingPaper(
            title="Paper B",
            abstract="Abstract B",
            authors=["Author 2"],
            trending_score=90.0
        )
        
        papers = [paper1, paper2]
        result = self.deduplicator.deduplicate_papers(papers)
        
        assert len(result) == 2
        assert result[0] == paper2  # Should be sorted by score
        assert result[1] == paper1
    
    def test_titles_similar_exact_match(self):
        """Test exact title matching after normalization."""
        title1 = "Attention Is All You Need!"
        title2 = "attention is all you need"
        
        assert self.deduplicator._titles_similar(title1, title2) is True
    
    def test_titles_similar_word_overlap(self):
        """Test title similarity based on word overlap."""
        title1 = "Deep Learning for Computer Vision"
        title2 = "Computer Vision with Deep Learning Networks"
        
        # Word overlap: {"deep", "learning", "computer", "vision"} = 4 words
        # Max word count: max(5, 6) = 6, so similarity = 4/6 = 0.67
        # With default threshold 0.8, this should be False
        similarity_result = self.deduplicator._titles_similar(title1, title2)
        assert similarity_result is False
        
        # Test with lower threshold
        low_threshold_deduplicator = PaperDeduplicator(title_threshold=0.6)
        assert low_threshold_deduplicator._titles_similar(title1, title2) is True
    
    def test_titles_not_similar(self):
        """Test dissimilar titles."""
        title1 = "Attention Is All You Need"
        title2 = "Quantum Computing Algorithms"
        
        assert self.deduplicator._titles_similar(title1, title2) is False
    
    def test_titles_similar_empty_titles(self):
        """Test with empty titles."""
        assert self.deduplicator._titles_similar("", "anything") is False
        assert self.deduplicator._titles_similar("anything", "") is False


class TestPaperDiscoveryService:
    """Test the main paper discovery service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.user_interests = UserInterests(
            research_areas=["machine learning"],
            categories=["cs.LG"],
            keywords=["neural networks"]
        )
        self.config = DiscoveryConfig(max_total_papers=10)
        self.service = PaperDiscoveryService(self.config, self.user_interests)
    
    def create_sample_paper(self, title: str, score: float = 50.0, arxiv_id: str = None) -> TrendingPaper:
        """Create a sample paper for testing."""
        return TrendingPaper(
            title=title,
            abstract="Sample abstract for testing",
            authors=["Test Author"],
            arxiv_id=arxiv_id,
            engagement=EngagementMetrics(github_stars=100),
            trending_score=score
        )
    
    @patch('src.services.paper_discovery.discover_trending_papers')
    @patch('src.services.paper_discovery.discover_trending_papers_from_github')
    def test_discover_papers_success(self, mock_github, mock_pwc):
        """Test successful paper discovery."""
        # Mock Papers with Code response
        pwc_papers = [
            self.create_sample_paper("PWC Paper 1", 80.0),
            self.create_sample_paper("PWC Paper 2", 70.0)
        ]
        mock_pwc.return_value = pwc_papers
        
        # Mock GitHub response
        github_papers = [
            self.create_sample_paper("GitHub Paper 1", 75.0),
        ]
        mock_github.return_value = github_papers
        
        with patch('src.services.paper_discovery.logger') as mock_logger:
            result = self.service.discover_papers()
        
        # Verify result structure
        assert isinstance(result, DiscoveryResult)
        assert len(result.papers) == 3
        assert result.source_stats["papers_with_code"] == 2
        assert result.source_stats["github_trending"] == 1
        assert result.total_discovered == 3
        assert result.discovery_time_seconds > 0
        assert result.errors == []
        
        # Verify papers are sorted by score
        scores = [p.trending_score for p in result.papers]
        assert scores == sorted(scores, reverse=True)
    
    @patch('src.services.paper_discovery.discover_trending_papers')
    @patch('src.services.paper_discovery.discover_trending_papers_from_github')
    def test_discover_papers_with_errors(self, mock_github, mock_pwc):
        """Test discovery with source errors."""
        # Papers with Code succeeds
        mock_pwc.return_value = [self.create_sample_paper("PWC Paper", 80.0)]
        
        # GitHub fails
        mock_github.side_effect = Exception("GitHub API error")
        
        result = self.service.discover_papers()
        
        assert len(result.papers) == 1
        assert result.source_stats["papers_with_code"] == 1
        assert result.source_stats["github_trending"] == 0
        assert len(result.errors) == 1
        assert "GitHub Trending error" in result.errors[0]
    
    @patch('src.services.paper_discovery.discover_trending_papers')
    @patch('src.services.paper_discovery.discover_trending_papers_from_github')
    def test_discover_papers_deduplication(self, mock_github, mock_pwc):
        """Test paper deduplication."""
        # Create duplicate papers (same arXiv ID)
        paper1 = self.create_sample_paper("Paper A", 80.0, "2024.1234")
        paper2 = self.create_sample_paper("Paper A - Implementation", 90.0, "2024.1234")
        
        mock_pwc.return_value = [paper1]
        mock_github.return_value = [paper2]
        
        result = self.service.discover_papers()
        
        # Should have only one paper after deduplication
        assert result.total_discovered == 2
        assert result.total_after_deduplication == 1
        assert len(result.papers) == 1
        assert result.papers[0].title == "Paper A - Implementation"  # Higher scoring one
    
    @patch('src.services.paper_discovery.discover_trending_papers')
    @patch('src.services.paper_discovery.discover_trending_papers_from_github')
    def test_discover_papers_filtering(self, mock_github, mock_pwc):
        """Test filtering by minimum engagement score."""
        # Create papers with different engagement scores
        low_engagement_paper = TrendingPaper(
            title="Low Engagement Paper",
            abstract="Abstract",
            authors=["Author"],
            engagement=EngagementMetrics(github_stars=5)  # Very low engagement
        )
        
        high_engagement_paper = TrendingPaper(
            title="High Engagement Paper", 
            abstract="Abstract",
            authors=["Author"],
            engagement=EngagementMetrics(github_stars=500)  # High engagement
        )
        
        mock_pwc.return_value = [low_engagement_paper, high_engagement_paper]
        mock_github.return_value = []
        
        result = self.service.discover_papers()
        
        assert result.total_discovered == 2
        # Both papers pass the default 10.0 minimum engagement score since they have non-zero stars
        assert result.total_after_filtering == 2
        assert len(result.papers) == 2
        # Papers should be sorted by score, highest first
        assert result.papers[0].title == "High Engagement Paper"
    
    def test_calculate_final_score(self):
        """Test final score calculation."""
        paper = TrendingPaper(
            title="Test Paper",
            abstract="machine learning neural networks",  # Matches user interests
            authors=["Author"],
            engagement=EngagementMetrics(github_stars=200),
            primary_repository=CodeRepository(
                url="https://github.com/test/repo",
                name="repo",
                description="Test",
                stars=200,
                forks=50,
                has_documentation=True,
                has_tests=True,
                has_examples=True,
                license_type="MIT"
            ),
            interest_match_score=0.8  # High interest match
        )
        
        score = self.service._calculate_final_score(paper)
        
        # Should be a combination of engagement, interest, and code quality
        assert score > 0
        assert isinstance(score, float)
    
    def test_get_discovery_summary(self):
        """Test discovery summary generation."""
        papers = [
            self.create_sample_paper("Paper 1", 90.0),
            self.create_sample_paper("Paper 2", 80.0)
        ]
        
        result = DiscoveryResult(
            papers=papers,
            source_stats={"papers_with_code": 2, "github_trending": 1},
            total_discovered=3,
            total_after_deduplication=2,
            total_after_filtering=2,
            discovery_time_seconds=1.5,
            errors=["Test error"]
        )
        
        summary = self.service.get_discovery_summary(result)
        
        assert "Paper Discovery Summary" in summary
        assert "Total papers found: 3" in summary
        assert "After deduplication: 2" in summary
        assert "papers_with_code: 2" in summary
        assert "Test error" in summary
        assert "Paper 1" in summary  # Top paper listed
    
    def test_service_disabled_sources(self):
        """Test with disabled sources."""
        config = DiscoveryConfig(
            use_papers_with_code=False,
            use_github_trending=False
        )
        service = PaperDiscoveryService(config, self.user_interests)
        
        result = service.discover_papers()
        
        assert len(result.papers) == 0
        assert result.source_stats == {}
        assert result.total_discovered == 0


def test_create_discovery_service():
    """Test discovery service factory function."""
    user_interests = UserInterests(
        research_areas=["machine learning"],
        categories=["cs.LG"],
        keywords=["neural networks"]
    )
    
    service = create_discovery_service(
        user_interests=user_interests,
        github_token="test_token",
        days_back=14,
        max_papers=100
    )
    
    assert isinstance(service, PaperDiscoveryService)
    assert service.config.github_token == "test_token"
    assert service.config.days_back == 14
    assert service.config.max_total_papers == 100
    assert service.user_interests == user_interests


if __name__ == "__main__":
    pytest.main([__file__]) 