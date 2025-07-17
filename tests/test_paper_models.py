"""Tests for enhanced paper data models.

This module tests the engagement-based paper models including scoring algorithms,
data structures, and business logic for trending paper discovery.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.data.paper_models import (
    TrendingPaper,
    CodeRepository, 
    EngagementMetrics,
    TrendingReason,
    create_example_trending_paper
)


class TestCodeRepository:
    """Test CodeRepository data model and scoring."""
    
    def setup_method(self):
        """Setup test data before each test."""
        self.basic_repo = CodeRepository(
            url="https://github.com/test/repo",
            name="test-repo",
            description="Test repository",
            stars=100,
            forks=20
        )
        
        self.quality_repo = CodeRepository(
            url="https://github.com/quality/repo",
            name="quality-repo", 
            description="High quality repository",
            stars=500,
            forks=75,
            has_documentation=True,
            has_tests=True,
            has_examples=True,
            license_type="MIT",
            last_commit_date=datetime.now() - timedelta(days=5)
        )
    
    def test_basic_repository_creation(self):
        """Test creating a basic repository."""
        repo = CodeRepository(
            url="https://github.com/test/basic",
            name="basic-repo"
        )
        
        assert repo.url == "https://github.com/test/basic"
        assert repo.name == "basic-repo"
        assert repo.description is None
        assert repo.stars == 0
        assert repo.forks == 0
        assert repo.has_documentation is False
        assert repo.has_tests is False
        assert repo.has_examples is False
    
    def test_calculate_quality_score_basic_repo(self):
        """Test quality score calculation for basic repository."""
        score = self.basic_repo.calculate_quality_score()
        
        # Should get points for stars (log10(101) ≈ 2.0, capped at 3.0)
        # No documentation, tests, examples, license, or recent activity
        assert 1.5 <= score <= 2.5  # Approximately log10(101) * 1
    
    def test_calculate_quality_score_quality_repo(self):
        """Test quality score calculation for high-quality repository."""
        score = self.quality_repo.calculate_quality_score()
        
        # Should get full points: 2 (docs) + 2 (tests) + 1 (examples) + 1 (license) + ~2.7 (stars) + 1 (recent activity)
        assert score >= 8.0  # High quality repo should score well
        assert score <= 10.0  # Max score is 10.0
    
    def test_calculate_quality_score_no_stars(self):
        """Test quality score with no stars but good practices."""
        repo = CodeRepository(
            url="https://github.com/test/no-stars",
            name="no-stars",
            stars=0,
            has_documentation=True,
            has_tests=True,
            has_examples=True,
            license_type="Apache-2.0"
        )
        
        score = repo.calculate_quality_score()
        # Should get 2 + 2 + 1 + 1 = 6 points
        assert score == 6.0
    
    def test_calculate_activity_score_recent_commit(self):
        """Test activity score with recent commit."""
        repo = CodeRepository(
            url="https://github.com/test/active",
            name="active-repo",
            last_commit_date=datetime.now() - timedelta(days=3)
        )
        
        score = repo.calculate_activity_score()
        assert score == 10.0  # Within 7 days
    
    def test_calculate_activity_score_old_commit(self):
        """Test activity score with old commit."""
        repo = CodeRepository(
            url="https://github.com/test/old",
            name="old-repo",
            last_commit_date=datetime.now() - timedelta(days=400)
        )
        
        score = repo.calculate_activity_score()
        assert score == 1.0  # Over 365 days
    
    def test_calculate_activity_score_no_commit_date(self):
        """Test activity score with no commit date."""
        repo = CodeRepository(
            url="https://github.com/test/no-date",
            name="no-date-repo"
        )
        
        score = repo.calculate_activity_score()
        assert score == 0.0


class TestEngagementMetrics:
    """Test EngagementMetrics data model and scoring."""
    
    def setup_method(self):
        """Setup test data before each test."""
        self.basic_metrics = EngagementMetrics(
            github_stars=50,
            github_forks=10,
            citation_count=5,
            social_mentions=3,
            days_since_publication=30
        )
        
        self.high_engagement = EngagementMetrics(
            github_stars=2000,
            github_forks=300,
            citation_count=150,
            citation_velocity=2.5,
            social_mentions=50,
            days_since_publication=7,
            last_activity_date=datetime.now()
        )
    
    def test_basic_metrics_creation(self):
        """Test creating basic engagement metrics."""
        metrics = EngagementMetrics()
        
        assert metrics.github_stars == 0
        assert metrics.github_forks == 0
        assert metrics.citation_count == 0
        assert metrics.citation_velocity == 0.0
        assert metrics.social_mentions == 0
        assert metrics.days_since_publication == 0
    
    def test_calculate_engagement_score_basic(self):
        """Test engagement score calculation for basic metrics."""
        score = self.basic_metrics.calculate_engagement_score()
        
        # Should get some points but not maximum
        assert 0.0 < score < 50.0
        assert isinstance(score, float)
    
    def test_calculate_engagement_score_high(self):
        """Test engagement score calculation for high engagement."""
        score = self.high_engagement.calculate_engagement_score()
        
        # Should get high score due to many factors
        assert score > 50.0
        assert score <= 100.0  # Max score
    
    def test_calculate_engagement_score_new_paper_bonus(self):
        """Test that new papers get engagement bonus."""
        new_metrics = EngagementMetrics(
            github_stars=100,
            days_since_publication=5  # Very recent
        )
        
        old_metrics = EngagementMetrics(
            github_stars=100, 
            days_since_publication=200  # Old
        )
        
        new_score = new_metrics.calculate_engagement_score()
        old_score = old_metrics.calculate_engagement_score()
        
        # New paper should score higher due to recency bonus
        assert new_score > old_score
    
    def test_calculate_engagement_score_fork_ratio_bonus(self):
        """Test that healthy fork ratio gives bonus."""
        good_ratio = EngagementMetrics(
            github_stars=100,
            github_forks=20  # 0.2 ratio - healthy
        )
        
        bad_ratio = EngagementMetrics(
            github_stars=100,
            github_forks=50  # 0.5 ratio - too high
        )
        
        good_score = good_ratio.calculate_engagement_score()
        bad_score = bad_ratio.calculate_engagement_score()
        
        # Good ratio should score higher
        assert good_score > bad_score
    
    def test_calculate_trending_velocity_basic(self):
        """Test trending velocity calculation."""
        velocity = self.basic_metrics.calculate_trending_velocity()
        
        # (50 stars + 3 mentions) / 30 days = 1.77 per day
        expected = (50 + 3) / 30
        assert abs(velocity - expected) < 0.01
    
    def test_calculate_trending_velocity_recent_activity_boost(self):
        """Test trending velocity gets boost for recent activity."""
        recent_metrics = EngagementMetrics(
            github_stars=100,
            social_mentions=10,
            days_since_publication=10,
            last_activity_date=datetime.now() - timedelta(hours=12)
        )
        
        old_metrics = EngagementMetrics(
            github_stars=100,
            social_mentions=10,
            days_since_publication=10,
            last_activity_date=datetime.now() - timedelta(days=5)
        )
        
        recent_velocity = recent_metrics.calculate_trending_velocity()
        old_velocity = old_metrics.calculate_trending_velocity()
        
        # Recent activity should boost velocity
        assert recent_velocity > old_velocity
    
    def test_calculate_trending_velocity_zero_days(self):
        """Test trending velocity with zero days since publication."""
        metrics = EngagementMetrics(
            github_stars=100,
            days_since_publication=0
        )
        
        velocity = metrics.calculate_trending_velocity()
        assert velocity == 0.0


class TestTrendingPaper:
    """Test TrendingPaper data model and business logic."""
    
    def setup_method(self):
        """Setup test data before each test."""
        self.repo = CodeRepository(
            url="https://github.com/test/paper-repo",
            name="paper-repo",
            stars=200,
            has_documentation=True,
            has_tests=True
        )
        
        self.engagement = EngagementMetrics(
            github_stars=200,
            github_forks=30,
            citation_count=20,
            social_mentions=5,
            days_since_publication=14
        )
        
        self.paper = TrendingPaper(
            title="Test Paper: Novel Approach",
            abstract="This paper presents a novel approach to testing...",
            authors=["Alice Smith", "Bob Jones"],
            arxiv_id="2401.12345",
            primary_repository=self.repo,
            engagement=self.engagement,
            trending_reasons=[TrendingReason.HIGH_GITHUB_ACTIVITY],
            discovery_source="papers_with_code"
        )
    
    def test_basic_paper_creation(self):
        """Test creating a basic trending paper."""
        paper = TrendingPaper(
            title="Simple Paper",
            abstract="Simple abstract",
            authors=["Author One"]
        )
        
        assert paper.title == "Simple Paper"
        assert paper.abstract == "Simple abstract" 
        assert paper.authors == ["Author One"]
        assert paper.arxiv_id is None
        assert paper.primary_repository is None
        assert isinstance(paper.engagement, EngagementMetrics)
        assert paper.trending_score == 0.0
        assert paper.trending_reasons == []
    
    def test_calculate_overall_score(self):
        """Test overall score calculation."""
        score = self.paper.calculate_overall_score()
        
        # Should combine engagement (70%) + interest (20%) + code quality (10%)
        assert score > 0.0
        assert isinstance(score, float)
        
        # Score should be influenced by all factors
        engagement_score = self.engagement.calculate_engagement_score()
        code_score = self.repo.calculate_quality_score()
        
        # At minimum should get 70% of engagement score + 10% of code score
        min_expected = engagement_score * 0.7 + code_score * 0.1 * 100
        assert score >= min_expected * 0.9  # Allow some floating point variance
    
    def test_calculate_overall_score_with_interest_match(self):
        """Test overall score with user interest matching."""
        self.paper.interest_match_score = 0.8
        
        score = self.paper.calculate_overall_score()
        
        # Should include interest bonus
        engagement_part = self.engagement.calculate_engagement_score() * 0.7
        interest_part = 0.8 * 0.2 * 100  # 16 points
        code_part = self.repo.calculate_quality_score() * 0.1 * 100
        
        expected = engagement_part + interest_part + code_part
        assert abs(score - expected) < 1.0  # Allow small variance
    
    def test_get_all_repositories(self):
        """Test getting all repositories."""
        additional_repo = CodeRepository(
            url="https://github.com/test/additional",
            name="additional-repo"
        )
        
        self.paper.additional_repositories = [additional_repo]
        
        all_repos = self.paper.get_all_repositories()
        assert len(all_repos) == 2
        assert self.repo in all_repos
        assert additional_repo in all_repos
    
    def test_get_all_repositories_no_primary(self):
        """Test getting repositories when no primary repository."""
        paper = TrendingPaper(
            title="No Repo Paper",
            abstract="Abstract",
            authors=["Author"]
        )
        
        additional_repo = CodeRepository(
            url="https://github.com/test/only-additional",
            name="only-additional"
        )
        paper.additional_repositories = [additional_repo]
        
        all_repos = paper.get_all_repositories()
        assert len(all_repos) == 1
        assert additional_repo in all_repos
    
    def test_get_trending_summary_single_reason(self):
        """Test trending summary with single reason."""
        self.paper.trending_reasons = [TrendingReason.CODE_QUALITY]
        
        summary = self.paper.get_trending_summary()
        assert summary == "High-quality implementation"
    
    def test_get_trending_summary_multiple_reasons(self):
        """Test trending summary with multiple reasons."""
        self.paper.trending_reasons = [
            TrendingReason.HIGH_GITHUB_ACTIVITY,
            TrendingReason.SOCIAL_BUZZ,
            TrendingReason.RECENT_PUBLICATION
        ]
        
        summary = self.paper.get_trending_summary()
        expected = "High GitHub activity, Social media buzz, and Recently published"
        assert summary == expected
    
    def test_get_trending_summary_no_reasons(self):
        """Test trending summary with no reasons."""
        self.paper.trending_reasons = []
        
        summary = self.paper.get_trending_summary()
        assert summary == "General interest"
    
    def test_has_quality_code_true(self):
        """Test has_quality_code returns True for quality repositories."""
        # Make repo high quality
        self.repo.has_documentation = True
        self.repo.has_tests = True
        self.repo.has_examples = True
        self.repo.license_type = "MIT"
        self.repo.stars = 1000
        
        assert self.paper.has_quality_code() is True
    
    def test_has_quality_code_false(self):
        """Test has_quality_code returns False for low quality."""
        # Make repo low quality
        self.repo.has_documentation = False
        self.repo.has_tests = False
        self.repo.has_examples = False
        self.repo.license_type = None
        self.repo.stars = 5
        
        assert self.paper.has_quality_code() is False
    
    def test_has_quality_code_no_repo(self):
        """Test has_quality_code with no repositories."""
        paper = TrendingPaper(
            title="No Code Paper",
            abstract="Abstract",
            authors=["Author"]
        )
        
        assert paper.has_quality_code() is False
    
    def test_days_since_publication(self):
        """Test days since publication calculation."""
        pub_date = datetime.now() - timedelta(days=15)
        self.paper.publication_date = pub_date
        
        days = self.paper.days_since_publication()
        assert days == 15
    
    def test_days_since_publication_no_date(self):
        """Test days since publication with no date."""
        self.paper.publication_date = None
        
        days = self.paper.days_since_publication()
        assert days == 0
    
    def test_to_dict(self):
        """Test converting paper to dictionary."""
        self.paper.publication_date = datetime(2024, 1, 15, 12, 0, 0)
        self.paper.trending_score = 75.5
        self.paper.tldr_summary = "Test summary"
        
        paper_dict = self.paper.to_dict()
        
        # Check required fields
        assert paper_dict['title'] == "Test Paper: Novel Approach"
        assert paper_dict['authors'] == ["Alice Smith", "Bob Jones"]
        assert paper_dict['arxiv_id'] == "2401.12345"
        assert paper_dict['publication_date'] == "2024-01-15T12:00:00"
        assert paper_dict['trending_score'] == 75.5
        assert paper_dict['discovery_source'] == "papers_with_code"
        assert paper_dict['tldr_summary'] == "Test summary"
        assert paper_dict['github_stars'] == 200
        assert paper_dict['citation_count'] == 20
        
        # Check calculated fields
        assert 'engagement_score' in paper_dict
        assert 'code_quality_score' in paper_dict
        assert 'trending_reasons' in paper_dict
        assert isinstance(paper_dict['has_quality_code'], bool)


class TestCreateExampleTrendingPaper:
    """Test the example paper creation function."""
    
    def test_create_example_paper(self):
        """Test creating example trending paper."""
        paper = create_example_trending_paper()
        
        # Check basic properties
        assert isinstance(paper, TrendingPaper)
        assert paper.title is not None
        assert paper.abstract is not None
        assert len(paper.authors) > 0
        assert paper.arxiv_id is not None
        
        # Check has repository
        assert paper.primary_repository is not None
        assert paper.primary_repository.has_documentation is True
        assert paper.primary_repository.has_tests is True
        
        # Check has engagement metrics
        assert paper.engagement.github_stars > 0
        assert paper.engagement.citation_count > 0
        
        # Check trending information
        assert len(paper.trending_reasons) > 0
        assert paper.discovery_source == "papers_with_code"
        assert paper.tldr_summary is not None
        
        # Check score calculation
        assert paper.trending_score > 0.0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_engagement_score_with_zero_values(self):
        """Test engagement score calculation with all zero values."""
        metrics = EngagementMetrics(
            days_since_publication=365  # Old paper, no recency bonus
        )
        score = metrics.calculate_engagement_score()
        assert score == 0.0
        
        # Test that new paper with zero engagement still gets recency bonus
        new_metrics = EngagementMetrics(
            days_since_publication=5  # Very recent
        )
        new_score = new_metrics.calculate_engagement_score()
        assert new_score == 10.0  # Should get recency bonus
    
    def test_quality_score_with_massive_stars(self):
        """Test quality score doesn't break with very large star counts."""
        repo = CodeRepository(
            url="https://github.com/test/huge",
            name="huge-repo",
            stars=1000000  # 1 million stars
        )
        
        score = repo.calculate_quality_score()
        assert 0.0 <= score <= 10.0  # Should be capped
    
    def test_paper_with_none_values(self):
        """Test paper handles None values gracefully."""
        paper = TrendingPaper(
            title="Test",
            abstract="Test",
            authors=[]
        )
        
        # Should not crash
        score = paper.calculate_overall_score()
        assert score >= 0.0
        
        paper_dict = paper.to_dict()
        assert isinstance(paper_dict, dict)
    
    def test_trending_velocity_edge_cases(self):
        """Test trending velocity with edge case values."""
        # Very large values
        metrics = EngagementMetrics(
            github_stars=999999,
            social_mentions=999999,
            days_since_publication=1
        )
        
        velocity = metrics.calculate_trending_velocity()
        assert velocity > 0.0
        assert isinstance(velocity, float)
        
        # Very small values
        metrics = EngagementMetrics(
            github_stars=1,
            social_mentions=0,
            days_since_publication=365
        )
        
        velocity = metrics.calculate_trending_velocity()
        assert velocity > 0.0 