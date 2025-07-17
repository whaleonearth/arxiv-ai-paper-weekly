"""Papers with Code API integration for discovering trending papers.

This module integrates with the Papers with Code API to discover trending papers
based on GitHub engagement metrics like stars, forks, and recent activity.
Papers with Code provides excellent data linking academic papers to code implementations.
"""

import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger

from ..data.paper_models import (
    TrendingPaper, 
    CodeRepository, 
    EngagementMetrics, 
    TrendingReason
)


@dataclass
class PapersWithCodeConfig:
    """Configuration for Papers with Code API integration."""
    base_url: str = "https://paperswithcode.com/api/v1"
    request_timeout: int = 30
    max_retries: int = 3
    papers_per_request: int = 50
    rate_limit_delay: float = 1.0  # Seconds between requests


class PapersWithCodeAPI:
    """Client for Papers with Code API."""
    
    def __init__(self, config: Optional[PapersWithCodeConfig] = None):
        """Initialize Papers with Code API client.
        
        Args:
            config: Configuration for the API client
        """
        self.config = config or PapersWithCodeConfig()
        self.session = requests.Session()
        
        # Set up retry strategy
        from requests.adapters import HTTPAdapter
        from requests.packages.urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make a request to the Papers with Code API.
        
        Args:
            endpoint: API endpoint to call
            params: Query parameters
            
        Returns:
            JSON response data or None if request failed
        """
        url = f"{self.config.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch from Papers with Code API: {url}, Error: {e}")
            return None
    
    def get_trending_papers(self, days_back: int = 7, min_stars: int = 10) -> List[Dict[str, Any]]:
        """Get trending papers from Papers with Code.
        
        Args:
            days_back: How many days back to look for trending papers
            min_stars: Minimum GitHub stars required
            
        Returns:
            List of paper data dictionaries
        """
        papers = []
        page = 1
        
        while len(papers) < 100:  # Limit to avoid too many requests
            params = {
                'page': page,
                'ordering': '-github_stars',  # Sort by GitHub stars descending
                'page_size': self.config.papers_per_request
            }
            
            response = self._make_request('papers/', params)
            if not response or not response.get('results'):
                break
                
            page_papers = response['results']
            
            # Filter papers by criteria
            for paper in page_papers:
                if self._is_trending_paper(paper, days_back, min_stars):
                    papers.append(paper)
            
            # Check if we have more pages
            if not response.get('next'):
                break
                
            page += 1
            
            # Rate limiting
            import time
            time.sleep(self.config.rate_limit_delay)
        
        logger.info(f"Found {len(papers)} trending papers from Papers with Code")
        return papers
    
    def _is_trending_paper(self, paper: Dict[str, Any], days_back: int, min_stars: int) -> bool:
        """Check if a paper meets trending criteria.
        
        Args:
            paper: Paper data from API
            days_back: Days back to consider for trending
            min_stars: Minimum stars required
            
        Returns:
            True if paper is considered trending
        """
        # Check if paper has associated repositories
        repos = paper.get('repositories', [])
        if not repos:
            return False
        
        # Check if any repository meets criteria
        for repo in repos:
            stars = repo.get('stars', 0)
            if stars >= min_stars:
                return True
        
        # Additional criteria could be added here:
        # - Recent publication date
        # - Citation velocity
        # - Social media mentions
        
        return False
    
    def get_paper_details(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific paper.
        
        Args:
            paper_id: Papers with Code paper ID
            
        Returns:
            Detailed paper information or None if not found
        """
        return self._make_request(f'papers/{paper_id}/')
    
    def get_paper_repositories(self, paper_id: str) -> List[Dict[str, Any]]:
        """Get repositories associated with a paper.
        
        Args:
            paper_id: Papers with Code paper ID
            
        Returns:
            List of repository information
        """
        response = self._make_request(f'papers/{paper_id}/repositories/')
        if response and 'results' in response:
            return response['results']
        return []


class PapersWithCodeConverter:
    """Converts Papers with Code API data to our TrendingPaper format."""
    
    def convert_paper(self, pwc_paper: Dict[str, Any]) -> Optional[TrendingPaper]:
        """Convert Papers with Code paper data to TrendingPaper.
        
        Args:
            pwc_paper: Paper data from Papers with Code API
            
        Returns:
            TrendingPaper instance or None if conversion failed
        """
        try:
            # Extract basic paper information
            title = pwc_paper.get('title', '')
            abstract = pwc_paper.get('abstract', '')
            
            # Parse authors (Papers with Code sometimes has authors as string)
            authors_data = pwc_paper.get('authors', [])
            if isinstance(authors_data, str):
                authors = [authors_data]
            elif isinstance(authors_data, list):
                authors = [
                    author.get('name', str(author)) if isinstance(author, dict) else str(author)
                    for author in authors_data
                ]
            else:
                authors = []
            
            # Extract arXiv information if available
            arxiv_id = None
            arxiv_url = None
            pdf_url = None
            
            if 'arxiv_id' in pwc_paper:
                arxiv_id = pwc_paper['arxiv_id']
                arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            
            # Parse publication date
            publication_date = None
            if 'published' in pwc_paper:
                try:
                    publication_date = datetime.fromisoformat(
                        pwc_paper['published'].replace('Z', '+00:00')
                    )
                except (ValueError, TypeError):
                    pass
            
            # Convert repositories
            repositories = self._convert_repositories(pwc_paper.get('repositories', []))
            primary_repo = repositories[0] if repositories else None
            additional_repos = repositories[1:] if len(repositories) > 1 else []
            
            # Calculate engagement metrics
            engagement = self._calculate_engagement_metrics(pwc_paper, repositories)
            
            # Determine trending reasons
            trending_reasons = self._determine_trending_reasons(pwc_paper, repositories, engagement)
            
            # Create the trending paper
            paper = TrendingPaper(
                title=title,
                abstract=abstract,
                authors=authors,
                arxiv_id=arxiv_id,
                arxiv_url=arxiv_url,
                pdf_url=pdf_url,
                publication_date=publication_date,
                categories=pwc_paper.get('tasks', []),  # PWC uses tasks instead of categories
                primary_repository=primary_repo,
                additional_repositories=additional_repos,
                engagement=engagement,
                trending_reasons=trending_reasons,
                discovery_source="papers_with_code"
            )
            
            # Calculate overall trending score
            paper.trending_score = paper.calculate_overall_score()
            
            return paper
            
        except Exception as e:
            logger.error(f"Failed to convert Papers with Code paper: {e}")
            return None
    
    def _convert_repositories(self, pwc_repos: List[Dict[str, Any]]) -> List[CodeRepository]:
        """Convert Papers with Code repository data to CodeRepository objects.
        
        Args:
            pwc_repos: Repository data from Papers with Code
            
        Returns:
            List of CodeRepository objects
        """
        repositories = []
        
        for repo_data in pwc_repos:
            try:
                # Extract repository information
                url = repo_data.get('url', '')
                name = repo_data.get('name', url.split('/')[-1] if url else 'unknown')
                description = repo_data.get('description', '')
                stars = repo_data.get('stars', 0)
                forks = repo_data.get('forks', 0)
                
                # Parse additional metadata if available
                language = repo_data.get('language')
                license_info = repo_data.get('license', {})
                license_type = None
                if isinstance(license_info, dict):
                    license_type = license_info.get('name')
                elif isinstance(license_info, str):
                    license_type = license_info
                
                # Determine quality indicators (simplified heuristics)
                has_documentation = self._has_documentation(repo_data)
                has_tests = self._has_tests(repo_data)
                has_examples = self._has_examples(repo_data)
                
                repository = CodeRepository(
                    url=url,
                    name=name,
                    description=description,
                    stars=stars,
                    forks=forks,
                    primary_language=language,
                    license_type=license_type,
                    has_documentation=has_documentation,
                    has_tests=has_tests,
                    has_examples=has_examples,
                    last_commit_date=datetime.now()  # PWC doesn't provide this, use current time
                )
                
                repositories.append(repository)
                
            except Exception as e:
                logger.warning(f"Failed to convert repository data: {e}")
                continue
        
        # Sort by stars (highest first)
        repositories.sort(key=lambda r: r.stars, reverse=True)
        return repositories
    
    def _has_documentation(self, repo_data: Dict[str, Any]) -> bool:
        """Heuristic to determine if repository has documentation.
        
        Args:
            repo_data: Repository data from Papers with Code
            
        Returns:
            True if likely has documentation
        """
        description = repo_data.get('description', '').lower()
        name = repo_data.get('name', '').lower()
        
        # Simple heuristics
        doc_indicators = ['readme', 'documentation', 'docs', 'tutorial', 'guide']
        return any(indicator in description or indicator in name for indicator in doc_indicators)
    
    def _has_tests(self, repo_data: Dict[str, Any]) -> bool:
        """Heuristic to determine if repository has tests.
        
        Args:
            repo_data: Repository data from Papers with Code
            
        Returns:
            True if likely has tests
        """
        # This is a simplified heuristic since PWC doesn't provide detailed repo analysis
        # In a real implementation, we'd analyze the repository structure
        stars = repo_data.get('stars', 0)
        return stars > 100  # Assume popular repos are more likely to have tests
    
    def _has_examples(self, repo_data: Dict[str, Any]) -> bool:
        """Heuristic to determine if repository has examples.
        
        Args:
            repo_data: Repository data from Papers with Code
            
        Returns:
            True if likely has examples
        """
        description = repo_data.get('description', '').lower()
        example_indicators = ['example', 'demo', 'tutorial', 'sample', 'notebook']
        return any(indicator in description for indicator in example_indicators)
    
    def _calculate_engagement_metrics(
        self, 
        pwc_paper: Dict[str, Any], 
        repositories: List[CodeRepository]
    ) -> EngagementMetrics:
        """Calculate engagement metrics from Papers with Code data.
        
        Args:
            pwc_paper: Paper data from Papers with Code
            repositories: Associated repositories
            
        Returns:
            EngagementMetrics object
        """
        # Sum up GitHub metrics from all repositories
        total_stars = sum(repo.stars for repo in repositories)
        total_forks = sum(repo.forks for repo in repositories)
        
        # Calculate days since publication
        days_since_pub = 0
        if 'published' in pwc_paper:
            try:
                pub_date = datetime.fromisoformat(pwc_paper['published'].replace('Z', '+00:00'))
                days_since_pub = (datetime.now(pub_date.tzinfo) - pub_date).days
            except (ValueError, TypeError):
                pass
        
        # Estimate citation metrics (PWC doesn't always provide this)
        citation_count = pwc_paper.get('citations', 0)
        citation_velocity = citation_count / max(1, days_since_pub) if days_since_pub > 0 else 0
        
        return EngagementMetrics(
            github_stars=total_stars,
            github_forks=total_forks,
            citation_count=citation_count,
            citation_velocity=citation_velocity,
            days_since_publication=days_since_pub,
            last_activity_date=datetime.now()
        )
    
    def _determine_trending_reasons(
        self, 
        pwc_paper: Dict[str, Any], 
        repositories: List[CodeRepository],
        engagement: EngagementMetrics
    ) -> List[TrendingReason]:
        """Determine why this paper is trending.
        
        Args:
            pwc_paper: Paper data from Papers with Code
            repositories: Associated repositories
            engagement: Calculated engagement metrics
            
        Returns:
            List of trending reasons
        """
        reasons = []
        
        # High GitHub activity
        if engagement.github_stars > 500:
            reasons.append(TrendingReason.HIGH_GITHUB_ACTIVITY)
        
        # Citation velocity
        if engagement.citation_velocity > 1.0:
            reasons.append(TrendingReason.CITATION_VELOCITY)
        
        # Recent publication
        if engagement.days_since_publication <= 30:
            reasons.append(TrendingReason.RECENT_PUBLICATION)
        
        # Code quality
        if any(repo.calculate_quality_score() >= 7.0 for repo in repositories):
            reasons.append(TrendingReason.CODE_QUALITY)
        
        # Community interest (based on fork ratio)
        if engagement.github_stars > 0 and engagement.github_forks > 0:
            fork_ratio = engagement.github_forks / engagement.github_stars
            if 0.1 <= fork_ratio <= 0.3:
                reasons.append(TrendingReason.COMMUNITY_INTEREST)
        
        return reasons


def discover_trending_papers(
    config: Optional[PapersWithCodeConfig] = None,
    days_back: int = 7,
    min_stars: int = 10,
    max_papers: int = 50
) -> List[TrendingPaper]:
    """Discover trending papers from Papers with Code.
    
    Args:
        config: Papers with Code API configuration
        days_back: Days to look back for trending papers
        min_stars: Minimum GitHub stars required
        max_papers: Maximum number of papers to return
        
    Returns:
        List of trending papers sorted by engagement score
    """
    api = PapersWithCodeAPI(config)
    converter = PapersWithCodeConverter()
    
    # Get trending papers from API
    pwc_papers = api.get_trending_papers(days_back, min_stars)
    
    # Convert to our format
    trending_papers = []
    for pwc_paper in pwc_papers[:max_papers]:
        paper = converter.convert_paper(pwc_paper)
        if paper:
            trending_papers.append(paper)
    
    # Sort by trending score
    trending_papers.sort(key=lambda p: p.trending_score, reverse=True)
    
    logger.info(f"Discovered {len(trending_papers)} trending papers from Papers with Code")
    return trending_papers 