"""Enhanced paper data models with engagement metrics.

This module defines the data structures for papers with engagement-based trending signals
instead of Zotero library similarity. Papers are ranked by multiple engagement signals
like GitHub stars, citations, social mentions, and code quality.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TrendingReason(Enum):
    """Reasons why a paper is trending."""
    HIGH_GITHUB_ACTIVITY = "high_github_activity"
    CITATION_VELOCITY = "citation_velocity"
    SOCIAL_BUZZ = "social_buzz"
    CODE_QUALITY = "code_quality"
    RECENT_PUBLICATION = "recent_publication"
    COMMUNITY_INTEREST = "community_interest"


@dataclass
class CodeRepository:
    """Information about a code repository associated with a paper."""
    url: str
    name: str
    description: Optional[str] = None
    stars: int = 0
    forks: int = 0
    issues_count: int = 0
    pull_requests_count: int = 0
    last_commit_date: Optional[datetime] = None
    primary_language: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    has_documentation: bool = False
    has_tests: bool = False
    has_examples: bool = False
    license_type: Optional[str] = None
    
    def calculate_quality_score(self) -> float:
        """Calculate code quality score based on repository characteristics.
        
        Returns:
            Float score between 0.0 and 10.0, higher means better quality
        """
        score = 0.0
        
        # Documentation bonus
        if self.has_documentation:
            score += 2.0
            
        # Tests bonus
        if self.has_tests:
            score += 2.0
            
        # Examples bonus  
        if self.has_examples:
            score += 1.0
            
        # License bonus
        if self.license_type:
            score += 1.0
            
        # Activity score based on stars and recent commits
        if self.stars > 0:
            # Logarithmic scaling for stars
            import math
            star_score = min(3.0, math.log10(self.stars + 1))
            score += star_score
            
        # Recent activity bonus
        if self.last_commit_date:
            days_since_commit = (datetime.now() - self.last_commit_date).days
            if days_since_commit <= 30:
                score += 1.0
            elif days_since_commit <= 90:
                score += 0.5
                
        return min(10.0, score)
    
    def calculate_activity_score(self) -> float:
        """Calculate repository activity score.
        
        Returns:
            Float score representing recent activity level
        """
        if not self.last_commit_date:
            return 0.0
            
        days_since_commit = (datetime.now() - self.last_commit_date).days
        
        # More recent commits get higher scores
        if days_since_commit <= 7:
            return 10.0
        elif days_since_commit <= 30:
            return 7.0
        elif days_since_commit <= 90:
            return 4.0
        elif days_since_commit <= 365:
            return 2.0
        else:
            return 1.0


@dataclass
class EngagementMetrics:
    """Engagement metrics for measuring paper popularity and trending status."""
    github_stars: int = 0
    github_forks: int = 0
    github_issues: int = 0
    citation_count: int = 0
    citation_velocity: float = 0.0  # Citations per day since publication
    arxiv_views: Optional[int] = None
    social_mentions: int = 0  # Twitter, Reddit, HN mentions
    download_count: Optional[int] = None
    
    # Time-based metrics
    days_since_publication: int = 0
    last_activity_date: Optional[datetime] = None
    
    # Derived scores
    viral_score: float = 0.0  # How quickly it's spreading
    impact_score: float = 0.0  # Overall impact potential
    
    def calculate_engagement_score(self) -> float:
        """Calculate overall engagement score from all metrics.
        
        Returns:
            Float score between 0.0 and 100.0, higher means more engaging
        """
        score = 0.0
        
        # GitHub engagement (40% weight)
        if self.github_stars > 0:
            import math
            # Logarithmic scaling for stars to prevent dominance of mega-repos
            star_score = min(25.0, math.log10(self.github_stars + 1) * 5)
            score += star_score
            
        # Fork ratio bonus (engagement indicator)
        if self.github_stars > 0 and self.github_forks > 0:
            fork_ratio = self.github_forks / self.github_stars
            if 0.1 <= fork_ratio <= 0.3:  # Healthy fork ratio
                score += 5.0
                
        # Citation metrics (30% weight)
        if self.citation_count > 0:
            citation_score = min(20.0, math.log10(self.citation_count + 1) * 4)
            score += citation_score
            
        # Citation velocity bonus (trending indicator)
        if self.citation_velocity > 0:
            velocity_score = min(10.0, self.citation_velocity * 2)
            score += velocity_score
            
        # Social buzz (20% weight)
        if self.social_mentions > 0:
            social_score = min(15.0, math.log10(self.social_mentions + 1) * 3)
            score += social_score
            
        # Recency bonus (10% weight) - newer papers get boost
        if self.days_since_publication <= 7:
            score += 10.0
        elif self.days_since_publication <= 30:
            score += 5.0
        elif self.days_since_publication <= 90:
            score += 2.0
            
        return min(100.0, score)
    
    def calculate_trending_velocity(self) -> float:
        """Calculate how fast this paper is trending.
        
        Returns:
            Velocity score indicating rate of engagement growth
        """
        if self.days_since_publication == 0:
            return 0.0
            
        # Simple velocity calculation
        daily_engagement = (self.github_stars + self.social_mentions) / max(1, self.days_since_publication)
        
        # Boost for very recent activity
        if self.last_activity_date:
            hours_since_activity = (datetime.now() - self.last_activity_date).total_seconds() / 3600
            if hours_since_activity <= 24:
                daily_engagement *= 2.0
                
        return daily_engagement


@dataclass
class TrendingPaper:
    """Enhanced paper model with engagement metrics and trending signals."""
    
    # Basic paper information
    title: str
    abstract: str
    authors: List[str]
    arxiv_id: Optional[str] = None
    arxiv_url: Optional[str] = None
    pdf_url: Optional[str] = None
    publication_date: Optional[datetime] = None
    categories: List[str] = field(default_factory=list)
    
    # Code and repositories
    primary_repository: Optional[CodeRepository] = None
    additional_repositories: List[CodeRepository] = field(default_factory=list)
    
    # Engagement metrics
    engagement: EngagementMetrics = field(default_factory=EngagementMetrics)
    
    # Trending information
    trending_score: float = 0.0
    trending_reasons: List[TrendingReason] = field(default_factory=list)
    discovery_source: str = "unknown"  # papers_with_code, github_trending, etc.
    
    # AI-generated content
    tldr_summary: Optional[str] = None
    impact_analysis: Optional[str] = None
    
    # User interest matching
    interest_match_score: float = 0.0
    matched_interests: List[str] = field(default_factory=list)
    
    def calculate_overall_score(self) -> float:
        """Calculate overall paper score combining engagement and user interest.
        
        Returns:
            Combined score for ranking papers
        """
        # Base engagement score (70% weight)
        base_score = self.engagement.calculate_engagement_score() * 0.7
        
        # User interest match (20% weight)
        interest_score = self.interest_match_score * 0.2 * 100
        
        # Code quality bonus (10% weight)
        code_score = 0.0
        if self.primary_repository:
            code_score = self.primary_repository.calculate_quality_score() * 0.1 * 100
            
        return base_score + interest_score + code_score
    
    def get_all_repositories(self) -> List[CodeRepository]:
        """Get all repositories associated with this paper.
        
        Returns:
            List of all repositories (primary + additional)
        """
        repos = []
        if self.primary_repository:
            repos.append(self.primary_repository)
        repos.extend(self.additional_repositories)
        return repos
    
    def get_trending_summary(self) -> str:
        """Get a human-readable summary of why this paper is trending.
        
        Returns:
            String describing trending reasons
        """
        if not self.trending_reasons:
            return "General interest"
            
        reason_descriptions = {
            TrendingReason.HIGH_GITHUB_ACTIVITY: "High GitHub activity",
            TrendingReason.CITATION_VELOCITY: "Rapidly gaining citations", 
            TrendingReason.SOCIAL_BUZZ: "Social media buzz",
            TrendingReason.CODE_QUALITY: "High-quality implementation",
            TrendingReason.RECENT_PUBLICATION: "Recently published",
            TrendingReason.COMMUNITY_INTEREST: "Strong community interest"
        }
        
        descriptions = [reason_descriptions.get(reason, str(reason)) for reason in self.trending_reasons]
        
        if len(descriptions) == 1:
            return descriptions[0]
        elif len(descriptions) == 2:
            return f"{descriptions[0]} and {descriptions[1]}"
        else:
            return f"{', '.join(descriptions[:-1])}, and {descriptions[-1]}"
    
    def has_quality_code(self) -> bool:
        """Check if this paper has high-quality code implementation.
        
        Returns:
            True if paper has quality code repositories
        """
        repos = self.get_all_repositories()
        if not repos:
            return False
            
        return any(repo.calculate_quality_score() >= 7.0 for repo in repos)
    
    def days_since_publication(self) -> int:
        """Calculate days since publication.
        
        Returns:
            Number of days since publication, or 0 if unknown
        """
        if not self.publication_date:
            return 0
            
        return (datetime.now() - self.publication_date).days
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert paper to dictionary for serialization.
        
        Returns:
            Dictionary representation of the paper
        """
        return {
            'title': self.title,
            'abstract': self.abstract,
            'authors': self.authors,
            'arxiv_id': self.arxiv_id,
            'arxiv_url': self.arxiv_url,
            'pdf_url': self.pdf_url,
            'publication_date': self.publication_date.isoformat() if self.publication_date else None,
            'categories': self.categories,
            'trending_score': self.trending_score,
            'engagement_score': self.engagement.calculate_engagement_score(),
            'code_quality_score': self.primary_repository.calculate_quality_score() if self.primary_repository else 0.0,
            'trending_reasons': [reason.value for reason in self.trending_reasons],
            'discovery_source': self.discovery_source,
            'tldr_summary': self.tldr_summary,
            'github_stars': self.engagement.github_stars,
            'citation_count': self.engagement.citation_count,
            'has_quality_code': self.has_quality_code()
        }


def create_example_trending_paper() -> TrendingPaper:
    """Create an example trending paper for testing and documentation.
    
    Returns:
        Example TrendingPaper instance
    """
    # Example repository
    repo = CodeRepository(
        url="https://github.com/example/transformer-implementation",
        name="transformer-implementation", 
        description="Clean implementation of Transformer architecture",
        stars=1250,
        forks=180,
        issues_count=15,
        primary_language="Python",
        topics=["transformers", "attention", "nlp"],
        has_documentation=True,
        has_tests=True,
        has_examples=True,
        license_type="MIT",
        last_commit_date=datetime.now()
    )
    
    # Example engagement metrics
    engagement = EngagementMetrics(
        github_stars=1250,
        github_forks=180,
        citation_count=45,
        citation_velocity=0.5,  # 0.5 citations per day
        social_mentions=12,
        days_since_publication=90,
        last_activity_date=datetime.now()
    )
    
    # Create the paper
    paper = TrendingPaper(
        title="Attention Is All You Need: A Comprehensive Implementation",
        abstract="This paper presents a comprehensive and clean implementation of the Transformer architecture...",
        authors=["Jane Smith", "John Doe", "Alice Johnson"],
        arxiv_id="2401.12345",
        arxiv_url="https://arxiv.org/abs/2401.12345",
        pdf_url="https://arxiv.org/pdf/2401.12345.pdf",
        publication_date=datetime.now(),
        categories=["cs.AI", "cs.LG", "cs.CL"],
        primary_repository=repo,
        engagement=engagement,
        trending_reasons=[TrendingReason.HIGH_GITHUB_ACTIVITY, TrendingReason.CODE_QUALITY],
        discovery_source="papers_with_code",
        tldr_summary="Clean, well-documented implementation of Transformers with comprehensive examples and tests."
    )
    
    # Calculate scores
    paper.trending_score = paper.calculate_overall_score()
    
    return paper 