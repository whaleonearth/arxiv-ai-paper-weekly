"""Papers with Code enrichment service.

This module uses the Papers with Code API to enrich papers discovered from
other sources (arXiv, Semantic Scholar) with GitHub repository information,
code implementations, and additional engagement metrics.
"""

import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from loguru import logger
import time

from ..data.paper_models import (
    TrendingPaper, 
    CodeRepository,
    EngagementMetrics,
    TrendingReason
)


@dataclass
class PapersWithCodeEnrichmentConfig:
    """Configuration for Papers with Code enrichment."""
    base_url: str = "https://paperswithcode.com/api/v1"
    request_timeout: int = 15  # Shorter timeout for enrichment
    max_retries: int = 2  # Fewer retries for supplementary data
    rate_limit_delay: float = 0.5  # Conservative rate limiting
    batch_size: int = 10  # Process papers in small batches


class PapersWithCodeEnricher:
    """Enrich papers with GitHub repository and code implementation data."""
    
    def __init__(self, config: Optional[PapersWithCodeEnrichmentConfig] = None):
        """Initialize Papers with Code enricher.
        
        Args:
            config: Configuration for the enricher
        """
        import os
        self.config = config or PapersWithCodeEnrichmentConfig()
        # Allow environment variable override for rate limiting
        env_delay = os.getenv('PAPERS_WITH_CODE_RATE_LIMIT_DELAY')
        if env_delay:
            self.config.rate_limit_delay = float(env_delay)
        
        self.session = requests.Session()
        
        # Set up retry strategy (more conservative for enrichment)
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def enrich_papers(self, papers: List[TrendingPaper]) -> List[TrendingPaper]:
        """Enrich papers with Papers with Code data.
        
        Args:
            papers: List of papers to enrich
            
        Returns:
            List of enriched papers
        """
        if not papers:
            return papers
        
        logger.info(f"Enriching {len(papers)} papers with Papers with Code data...")
        
        enriched_papers = []
        processed = 0
        
        # Process in batches to be respectful of API limits
        for i in range(0, len(papers), self.config.batch_size):
            batch = papers[i:i + self.config.batch_size]
            
            for paper in batch:
                try:
                    enriched_paper = self._enrich_single_paper(paper)
                    enriched_papers.append(enriched_paper)
                    processed += 1
                    
                    # Rate limiting between papers
                    if self.config.rate_limit_delay > 0:
                        time.sleep(self.config.rate_limit_delay)
                        
                except Exception as e:
                    logger.warning(f"Failed to enrich paper '{paper.title[:50]}...': {e}")
                    # Add the original paper if enrichment fails
                    enriched_papers.append(paper)
                    processed += 1
            
            # Progress logging
            if i % (self.config.batch_size * 2) == 0:
                logger.debug(f"Enriched {processed}/{len(papers)} papers...")
        
        success_count = sum(1 for p in enriched_papers if p.primary_repository is not None)
        logger.info(f"Successfully enriched {success_count}/{len(papers)} papers with code repositories")
        
        return enriched_papers
    
    def _enrich_single_paper(self, paper: TrendingPaper) -> TrendingPaper:
        """Enrich a single paper with Papers with Code data.
        
        Args:
            paper: Paper to enrich
            
        Returns:
            Enriched paper (or original if enrichment fails)
        """
        # Try to find the paper on Papers with Code
        pwc_paper_data = self._find_paper_by_arxiv_id(paper.arxiv_id) if paper.arxiv_id else None
        
        if not pwc_paper_data:
            # Try by title if arXiv ID search fails
            pwc_paper_data = self._find_paper_by_title(paper.title)
        
        if not pwc_paper_data:
            # No enrichment possible, return original paper
            return paper
        
        # Get repository information
        repositories = self._get_paper_repositories(pwc_paper_data['id'])
        
        if not repositories:
            # No repositories found, but mark as available on Papers with Code
            paper.trending_reasons.append(TrendingReason.CODE_QUALITY)
            return paper
        
        # Select primary repository (highest stars)
        primary_repo = max(repositories, key=lambda r: r.stars)
        additional_repos = [r for r in repositories if r != primary_repo]
        
        # Update paper with repository information
        enriched_paper = TrendingPaper(
            # Copy all existing fields
            title=paper.title,
            abstract=paper.abstract,
            authors=paper.authors,
            arxiv_id=paper.arxiv_id,
            arxiv_url=paper.arxiv_url,
            pdf_url=paper.pdf_url,
            publication_date=paper.publication_date,
            categories=paper.categories,
            
            # Add repository information
            primary_repository=primary_repo,
            additional_repositories=additional_repos,
            
            # Update engagement metrics with GitHub data
            engagement=self._update_engagement_metrics(paper.engagement, primary_repo),
            
            # Add trending reasons
                            trending_reasons=paper.trending_reasons + [TrendingReason.HIGH_GITHUB_ACTIVITY],
            
            # Keep other fields
            discovery_source=paper.discovery_source,
            tldr_summary=paper.tldr_summary,
            impact_analysis=paper.impact_analysis,
            interest_match_score=paper.interest_match_score,
            matched_interests=paper.matched_interests,
            
            # Recalculate trending score with new engagement data
            trending_score=0.0  # Will be recalculated
        )
        
        # Recalculate trending score with enriched data
        enriched_paper.trending_score = enriched_paper.engagement.calculate_engagement_score()
        
        return enriched_paper
    
    def _find_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Find paper by arXiv ID.
        
        Args:
            arxiv_id: arXiv paper ID
            
        Returns:
            Paper data from Papers with Code or None if not found
        """
        if not arxiv_id:
            return None
        
        try:
            url = f"{self.config.base_url}/papers/"
            params = {'arxiv_id': arxiv_id}
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.request_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                papers = data.get('results', [])
                return papers[0] if papers else None
            
            return None
            
        except Exception as e:
            logger.debug(f"Error searching by arXiv ID {arxiv_id}: {e}")
            return None
    
    def _find_paper_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Find paper by title search.
        
        Args:
            title: Paper title
            
        Returns:
            Paper data from Papers with Code or None if not found
        """
        if not title or len(title) < 10:
            return None
        
        try:
            # Clean title for search
            search_title = title.lower().strip()
            # Remove common words that might interfere
            for word in ['via', 'using', 'with', 'for', 'on', 'in', 'a', 'an', 'the']:
                search_title = search_title.replace(f' {word} ', ' ')
            
            url = f"{self.config.base_url}/papers/"
            params = {'q': search_title[:100]}  # Limit query length
            
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.request_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                papers = data.get('results', [])
                
                # Find best title match
                for paper_data in papers[:5]:  # Check top 5 results
                    pwc_title = paper_data.get('title', '').lower()
                    if self._titles_similar(title.lower(), pwc_title):
                        return paper_data
            
            return None
            
        except Exception as e:
            logger.debug(f"Error searching by title '{title[:30]}...': {e}")
            return None
    
    def _titles_similar(self, title1: str, title2: str, threshold: float = 0.7) -> bool:
        """Check if two titles are similar enough to be the same paper.
        
        Args:
            title1: First title
            title2: Second title
            threshold: Similarity threshold
            
        Returns:
            True if titles are similar
        """
        # Simple word overlap similarity
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        
        # Remove common stop words
        stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold
    
    def _get_paper_repositories(self, paper_id: str) -> List[CodeRepository]:
        """Get repositories for a paper.
        
        Args:
            paper_id: Papers with Code paper ID
            
        Returns:
            List of code repositories
        """
        try:
            url = f"{self.config.base_url}/papers/{paper_id}/repositories/"
            
            response = self.session.get(
                url,
                timeout=self.config.request_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                repos_data = data.get('results', [])
                
                repositories = []
                for repo_data in repos_data:
                    repo = self._convert_repository_data(repo_data)
                    if repo:
                        repositories.append(repo)
                
                return repositories
            
            return []
            
        except Exception as e:
            logger.debug(f"Error getting repositories for paper {paper_id}: {e}")
            return []
    
    def _convert_repository_data(self, repo_data: Dict[str, Any]) -> Optional[CodeRepository]:
        """Convert Papers with Code repository data to CodeRepository.
        
        Args:
            repo_data: Repository data from Papers with Code API
            
        Returns:
            CodeRepository object or None if conversion fails
        """
        try:
            url = repo_data.get('url', '')
            if not url:
                return None
            
            # Extract owner and name from URL
            # Handle both github.com and other git hosts
            import re
            match = re.search(r'github\.com/([^/]+)/([^/]+)', url)
            if match:
                owner = match.group(1)
                name = match.group(2)
                if name.endswith('.git'):
                    name = name[:-4]
            else:
                # Fall back to parsing from URL
                parts = url.rstrip('/').split('/')
                if len(parts) >= 2:
                    owner = parts[-2]
                    name = parts[-1]
                else:
                    return None
            
            repository = CodeRepository(
                url=url,
                name=name,
                description=repo_data.get('description', ''),
                stars=repo_data.get('stars', 0) or 0,
                forks=repo_data.get('forks', 0) or 0,
                primary_language=repo_data.get('language', ''),
                # Note: Papers with Code doesn't provide detailed GitHub data
                # Issues, PRs, commit dates, etc. would need GitHub API integration
                issues_count=0,  # Not available from Papers with Code
                pull_requests_count=0,  # Not available from Papers with Code  
                last_commit_date=None,  # Not available from Papers with Code
                topics=[],  # Not available from Papers with Code
                has_documentation=False,  # Would need to check README/docs
                has_tests=False,  # Would need to check for test files
                has_examples=False,  # Would need to check for example files
                license_type=None  # Not available from Papers with Code
            )
            
            return repository
            
        except Exception as e:
            logger.debug(f"Error converting repository data: {e}")
            return None
    
    def _update_engagement_metrics(
        self, 
        original_engagement: EngagementMetrics,
        repository: CodeRepository
    ) -> EngagementMetrics:
        """Update engagement metrics with GitHub repository data.
        
        Args:
            original_engagement: Original engagement metrics
            repository: Primary repository
            
        Returns:
            Updated engagement metrics
        """
        return EngagementMetrics(
            github_stars=repository.stars,
            github_forks=repository.forks,
            citation_count=original_engagement.citation_count,
                                          social_mentions=original_engagement.social_mentions
        )


def enrich_papers_with_code_data(
    papers: List[TrendingPaper],
    config: Optional[PapersWithCodeEnrichmentConfig] = None
) -> List[TrendingPaper]:
    """Enrich papers with Papers with Code repository and implementation data.
    
    Args:
        papers: List of papers to enrich
        config: Enrichment configuration
        
    Returns:
        List of enriched papers with GitHub repository information
    """
    if not papers:
        return papers
    
    enricher = PapersWithCodeEnricher(config)
    return enricher.enrich_papers(papers) 