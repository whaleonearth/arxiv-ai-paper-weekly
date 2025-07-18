"""Unified paper discovery service.

This service coordinates multiple paper discovery sources and provides
ranking, deduplication, and user interest matching to deliver the best
trending papers to users.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from loguru import logger

from ..core.config import UserInterests
from ..data.paper_models import TrendingPaper, TrendingReason
from ..integrations.papers_with_code import discover_trending_papers
from ..integrations.github_trending import discover_trending_papers_from_github
from ..integrations.arxiv_api import discover_recent_papers
from ..integrations.semantic_scholar_api import discover_impactful_papers
from ..integrations.papers_enrichment import enrich_papers_with_code_data


@dataclass
class DiscoveryConfig:
    """Configuration for paper discovery."""
    
    # Primary source configuration (fast, reliable)
    use_arxiv_api: bool = True
    use_semantic_scholar: bool = True
    
    # Legacy/supplementary source configuration
    use_papers_with_code: bool = False  # Now used for enrichment only
    use_github_trending: bool = True
    
    # Enrichment configuration
    enrich_with_papers_with_code: bool = True  # Add GitHub repo data
    
    # API tokens
    github_token: Optional[str] = None
    
    # Discovery parameters
    days_back: int = 7
    max_papers_per_source: int = 50
    max_total_papers: int = 100
    
    # Ranking parameters
    min_engagement_score: float = 5.0  # Lower threshold to ensure papers are found
    engagement_weight: float = 0.5
    interest_weight: float = 0.3
    code_quality_weight: float = 0.2
    
    # Deduplication parameters
    title_similarity_threshold: float = 0.8
    arxiv_id_match: bool = True
    
    @classmethod
    def from_user_interests(cls, user_interests: UserInterests, **kwargs) -> 'DiscoveryConfig':
        """Create DiscoveryConfig from UserInterests configuration.
        
        Args:
            user_interests: User interests configuration
            **kwargs: Additional override parameters
            
        Returns:
            DiscoveryConfig instance
        """
        sources = user_interests.sources
        
        return cls(
            use_arxiv_api=getattr(sources, 'arxiv_api', True),
            use_semantic_scholar=getattr(sources, 'semantic_scholar', True),
            use_papers_with_code=getattr(sources, 'papers_with_code', False),
            use_github_trending=getattr(sources, 'github_trending', True),
            enrich_with_papers_with_code=getattr(sources, 'enrich_with_papers_with_code', True),
            min_engagement_score=getattr(user_interests.filters, 'min_engagement_score', 5.0),
            **kwargs
        )


@dataclass
class DiscoveryResult:
    """Result from paper discovery process."""
    
    papers: List[TrendingPaper]
    source_stats: Dict[str, int]
    total_discovered: int
    total_after_deduplication: int
    total_after_filtering: int
    discovery_time_seconds: float
    errors: List[str]


class PaperInterestMatcher:
    """Matches papers against user interests."""
    
    def __init__(self, user_interests: UserInterests):
        """Initialize interest matcher.
        
        Args:
            user_interests: User's research interests
        """
        self.user_interests = user_interests
    
    def calculate_interest_score(self, paper: TrendingPaper) -> float:
        """Calculate how well a paper matches user interests.
        
        Args:
            paper: Paper to evaluate
            
        Returns:
            Interest score from 0.0 to 1.0
        """
        # Calculate scores for different criteria
        area_score = self._match_research_areas(paper)
        category_score = self._match_categories(paper)
        keyword_score = self._match_keywords(paper)
        
        # Weighted combination
        total_score = (area_score * 0.4 + category_score * 0.4 + keyword_score * 0.2)
        
        # Update paper with matching details
        paper.interest_match_score = total_score
        paper.matched_interests = self._get_matched_interests(paper)
        
        return total_score
    
    def _match_research_areas(self, paper: TrendingPaper) -> float:
        """Match against research areas."""
        if not self.user_interests.research_areas:
            return 0.5  # Neutral score if no preferences
            
        search_text = f"{paper.title} {paper.abstract}".lower()
        matches = 0
        
        for area in self.user_interests.research_areas:
            if area.lower() in search_text:
                matches += 1
                
        return min(1.0, matches / len(self.user_interests.research_areas))
    
    def _match_categories(self, paper: TrendingPaper) -> float:
        """Match against arXiv categories."""
        if not self.user_interests.categories:
            return 0.5  # Neutral score if no preferences
            
        if not paper.categories:
            return 0.3  # Lower score for papers without categories
            
        matches = len(set(paper.categories) & set(self.user_interests.categories))
        return min(1.0, matches / len(self.user_interests.categories))
    
    def _match_keywords(self, paper: TrendingPaper) -> float:
        """Match against keywords."""
        if not self.user_interests.keywords:
            return 0.5  # Neutral score if no preferences
            
        search_text = f"{paper.title} {paper.abstract}".lower()
        matches = 0
        
        for keyword in self.user_interests.keywords:
            if keyword.lower() in search_text:
                matches += 1
                
        return min(1.0, matches / len(self.user_interests.keywords))
    
    def _get_matched_interests(self, paper: TrendingPaper) -> List[str]:
        """Get list of user interests that match this paper."""
        matched = []
        search_text = f"{paper.title} {paper.abstract}".lower()
        
        # Check research areas
        for area in self.user_interests.research_areas:
            if area.lower() in search_text:
                matched.append(area)
                
        # Check categories
        matched.extend(set(paper.categories) & set(self.user_interests.categories))
        
        # Check keywords
        for keyword in self.user_interests.keywords:
            if keyword.lower() in search_text:
                matched.append(keyword)
                
        return list(set(matched))


class PaperDeduplicator:
    """Removes duplicate papers from discovery results."""
    
    def __init__(self, title_threshold: float = 0.8, check_arxiv_ids: bool = True):
        """Initialize deduplicator.
        
        Args:
            title_threshold: Similarity threshold for title matching
            check_arxiv_ids: Whether to check for matching arXiv IDs
        """
        self.title_threshold = title_threshold
        self.check_arxiv_ids = check_arxiv_ids
    
    def deduplicate_papers(self, papers: List[TrendingPaper]) -> List[TrendingPaper]:
        """Remove duplicate papers.
        
        Args:
            papers: List of papers to deduplicate
            
        Returns:
            List with duplicates removed, keeping highest scoring versions
        """
        if not papers:
            return []
            
        # Sort by trending score (highest first) to keep best versions
        sorted_papers = sorted(papers, key=lambda p: p.trending_score, reverse=True)
        
        unique_papers = []
        seen_arxiv_ids = set()
        seen_titles = []
        
        for paper in sorted_papers:
            is_duplicate = False
            
            # Check arXiv ID duplicates
            if self.check_arxiv_ids and paper.arxiv_id:
                if paper.arxiv_id in seen_arxiv_ids:
                    is_duplicate = True
                else:
                    seen_arxiv_ids.add(paper.arxiv_id)
            
            # Check title similarity
            if not is_duplicate:
                for existing_title in seen_titles:
                    if self._titles_similar(paper.title, existing_title):
                        is_duplicate = True
                        break
                        
                if not is_duplicate:
                    seen_titles.append(paper.title)
            
            if not is_duplicate:
                unique_papers.append(paper)
                
        logger.info(f"Deduplication: {len(papers)} -> {len(unique_papers)} papers")
        return unique_papers
    
    def _titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough to be considered duplicates.
        
        Args:
            title1: First title
            title2: Second title
            
        Returns:
            True if titles are similar
        """
        # Simple similarity check - normalize and compare
        def normalize_title(title: str) -> str:
            return ''.join(c.lower() for c in title if c.isalnum() or c.isspace()).strip()
        
        norm1 = normalize_title(title1)
        norm2 = normalize_title(title2)
        
        # Check for exact match after normalization
        if norm1 == norm2:
            return True
            
        # Check for substantial overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            return False
            
        overlap = len(words1 & words2)
        similarity = overlap / max(len(words1), len(words2))
        
        return similarity >= self.title_threshold


class PaperDiscoveryService:
    """Main service for discovering trending papers from multiple sources."""
    
    def __init__(self, config: DiscoveryConfig, user_interests: UserInterests):
        """Initialize discovery service.
        
        Args:
            config: Discovery configuration
            user_interests: User's research interests
        """
        self.config = config
        self.user_interests = user_interests
        self.interest_matcher = PaperInterestMatcher(user_interests)
        self.deduplicator = PaperDeduplicator(
            title_threshold=config.title_similarity_threshold,
            check_arxiv_ids=config.arxiv_id_match
        )
    
    def discover_papers(self) -> DiscoveryResult:
        """Discover trending papers from all configured sources.
        
        Returns:
            Discovery result with ranked papers and statistics
        """
        start_time = datetime.now()
        all_papers = []
        source_stats = {}
        errors = []
        
        logger.info("Starting paper discovery with arXiv + Semantic Scholar + Papers with Code enrichment...")
        
        # Primary sources: arXiv API (recent papers)
        if self.config.use_arxiv_api:
            try:
                arxiv_papers = discover_recent_papers(
                    user_interests=self.user_interests,
                    days_back=max(self.config.days_back, 14),  # Minimum 14 days for arXiv to ensure papers found
                    max_papers=self.config.max_papers_per_source
                )
                all_papers.extend(arxiv_papers)
                source_stats["arxiv_api"] = len(arxiv_papers)
                logger.info(f"arXiv API: {len(arxiv_papers)} papers")
            except Exception as e:
                error_msg = f"arXiv API error: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                source_stats["arxiv_api"] = 0
        
        # Primary sources: Semantic Scholar (impactful papers)
        if self.config.use_semantic_scholar:
            try:
                semantic_papers = discover_impactful_papers(
                    user_interests=self.user_interests,
                    days_back=min(self.config.days_back * 8, 60),  # Much longer period for citations (up to 60 days)
                    max_papers=self.config.max_papers_per_source
                )
                all_papers.extend(semantic_papers)
                source_stats["semantic_scholar"] = len(semantic_papers)
                logger.info(f"Semantic Scholar: {len(semantic_papers)} papers")
            except Exception as e:
                error_msg = f"Semantic Scholar error: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                source_stats["semantic_scholar"] = 0
        
        # Legacy source: Papers with Code (only if enabled)
        if self.config.use_papers_with_code:
            try:
                pwc_papers = discover_trending_papers(
                    days_back=self.config.days_back,
                    max_papers=self.config.max_papers_per_source
                )
                all_papers.extend(pwc_papers)
                source_stats["papers_with_code"] = len(pwc_papers)
                logger.info(f"Papers with Code: {len(pwc_papers)} papers")
            except Exception as e:
                error_msg = f"Papers with Code error: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                source_stats["papers_with_code"] = 0
        
        # Supplementary source: GitHub Trending
        if self.config.use_github_trending:
            try:
                github_papers = discover_trending_papers_from_github(
                    github_token=self.config.github_token,
                    days_back=self.config.days_back,
                    max_papers=self.config.max_papers_per_source
                )
                all_papers.extend(github_papers)
                source_stats["github_trending"] = len(github_papers)
                logger.info(f"GitHub Trending: {len(github_papers)} papers")
            except Exception as e:
                error_msg = f"GitHub Trending error: {e}"
                errors.append(error_msg)
                logger.error(error_msg)
                source_stats["github_trending"] = 0
        
        total_discovered = len(all_papers)
        logger.info(f"Total papers discovered: {total_discovered}")
        
        # Deduplicate papers
        unique_papers = self.deduplicator.deduplicate_papers(all_papers)
        total_after_deduplication = len(unique_papers)
        
        # Enrich papers with Papers with Code repository data
        if self.config.enrich_with_papers_with_code and unique_papers:
            try:
                logger.info("Enriching papers with GitHub repository data...")
                unique_papers = enrich_papers_with_code_data(unique_papers)
                enriched_count = sum(1 for p in unique_papers if p.primary_repository is not None)
                logger.info(f"Successfully enriched {enriched_count}/{len(unique_papers)} papers with code repositories")
            except Exception as e:
                error_msg = f"Papers with Code enrichment error: {e}"
                errors.append(error_msg)
                logger.warning(error_msg)
        
        # Calculate interest scores for all papers
        for paper in unique_papers:
            self.interest_matcher.calculate_interest_score(paper)
        
        # Filter by minimum engagement score
        filtered_papers = [
            p for p in unique_papers 
            if p.engagement.calculate_engagement_score() >= self.config.min_engagement_score
        ]
        total_after_filtering = len(filtered_papers)
        
        # Calculate final scores and rank papers
        for paper in filtered_papers:
            paper.trending_score = self._calculate_final_score(paper)
        
        # Sort by final score and limit results
        ranked_papers = sorted(filtered_papers, key=lambda p: p.trending_score, reverse=True)
        final_papers = ranked_papers[:self.config.max_total_papers]
        
        # Calculate discovery time
        discovery_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Discovery complete: {len(final_papers)} papers in {discovery_time:.2f}s")
        
        return DiscoveryResult(
            papers=final_papers,
            source_stats=source_stats,
            total_discovered=total_discovered,
            total_after_deduplication=total_after_deduplication,
            total_after_filtering=total_after_filtering,
            discovery_time_seconds=discovery_time,
            errors=errors
        )
    
    def _calculate_final_score(self, paper: TrendingPaper) -> float:
        """Calculate final ranking score for a paper.
        
        Args:
            paper: Paper to score
            
        Returns:
            Final score for ranking
        """
        # Get component scores
        engagement_score = paper.engagement.calculate_engagement_score()
        interest_score = paper.interest_match_score * 100  # Scale to 0-100
        
        # Code quality score
        code_score = 0.0
        if paper.primary_repository:
            code_score = paper.primary_repository.calculate_quality_score() * 10  # Scale to 0-100
        
        # Weighted combination
        final_score = (
            engagement_score * self.config.engagement_weight +
            interest_score * self.config.interest_weight +
            code_score * self.config.code_quality_weight
        )
        
        return final_score
    
    def get_discovery_summary(self, result: DiscoveryResult) -> str:
        """Generate human-readable summary of discovery results.
        
        Args:
            result: Discovery result
            
        Returns:
            Formatted summary string
        """
        summary_lines = [
            f"Paper Discovery Summary",
            f"======================",
            f"Total papers found: {result.total_discovered}",
            f"After deduplication: {result.total_after_deduplication}",
            f"After filtering: {result.total_after_filtering}",
            f"Final selection: {len(result.papers)}",
            f"Discovery time: {result.discovery_time_seconds:.2f}s",
            f"",
            f"Source breakdown:"
        ]
        
        for source, count in result.source_stats.items():
            summary_lines.append(f"  {source}: {count} papers")
        
        if result.errors:
            summary_lines.extend([
                f"",
                f"Errors encountered:",
                *[f"  - {error}" for error in result.errors]
            ])
        
        if result.papers:
            summary_lines.extend([
                f"",
                f"Top trending papers:",
                *[f"  {i+1}. {paper.title} (score: {paper.trending_score:.1f})" 
                  for i, paper in enumerate(result.papers[:5])]
            ])
        
        return "\n".join(summary_lines)


def create_discovery_service(
    user_interests: UserInterests,
    github_token: Optional[str] = None,
    days_back: int = 7,
    max_papers: int = 50
) -> PaperDiscoveryService:
    """Create a configured paper discovery service.
    
    Args:
        user_interests: User's research interests
        github_token: GitHub API token (optional)
        days_back: Number of days to look back
        max_papers: Maximum papers to return
        
    Returns:
        Configured discovery service
    """
    config = DiscoveryConfig.from_user_interests(
        user_interests,
        github_token=github_token,
        days_back=days_back,
        max_total_papers=max_papers
    )
    
    return PaperDiscoveryService(config, user_interests) 