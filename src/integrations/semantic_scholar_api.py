"""Semantic Scholar API integration for discovering impactful papers.

This module integrates with the Semantic Scholar API to discover papers
with high citation velocity, impact, and engagement. Semantic Scholar provides
excellent academic metadata and citation information.
"""

import requests
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger
import time

from ..data.paper_models import (
    TrendingPaper, 
    EngagementMetrics, 
    TrendingReason
)
from ..core.config import UserInterests


@dataclass
class SemanticScholarConfig:
    """Configuration for Semantic Scholar API integration."""
    base_url: str = "https://api.semanticscholar.org/graph/v1"
    request_timeout: int = 30
    max_retries: int = 3
    papers_per_request: int = 100
    rate_limit_delay: float = 1.0  # Conservative rate limiting to avoid 429 errors
    fields: List[str] = None
    
    def __post_init__(self):
        if self.fields is None:
            # Only use fields that are valid for the search endpoint
            self.fields = [
                'paperId', 'title', 'abstract', 'authors', 'year', 'publicationDate',
                'citationCount', 'referenceCount', 'influentialCitationCount',
                'fieldsOfStudy', 'venue', 'externalIds', 'openAccessPdf', 'url'
            ]


class SemanticScholarAPI:
    """Client for Semantic Scholar Academic Graph API."""
    
    def __init__(self, config: Optional[SemanticScholarConfig] = None):
        """Initialize Semantic Scholar API client.
        
        Args:
            config: Configuration for the API client
        """
        import os
        self.config = config or SemanticScholarConfig()
        # Allow environment variable override for rate limiting
        env_delay = os.getenv('SEMANTIC_SCHOLAR_RATE_LIMIT_DELAY')
        if env_delay:
            self.config.rate_limit_delay = float(env_delay)
        
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
    
    def search_papers(
        self, 
        user_interests: UserInterests,
        days_back: int = 30,  # Semantic Scholar works better with longer periods
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for papers based on user interests.
        
        Args:
            user_interests: User's research interests
            days_back: Number of days to look back
            max_results: Maximum number of papers to return
            
        Returns:
            List of paper data from Semantic Scholar API
        """
        papers = []
        
        # Build queries based on user interests
        queries = self._build_queries(user_interests)
        
        for query in queries:
            try:
                logger.debug(f"Searching Semantic Scholar with query: {query[:100]}...")
                
                query_papers = self._search_query(query, max_results // len(queries))
                papers.extend(query_papers)
                
                logger.debug(f"Found {len(query_papers)} papers for query")
                
                # Rate limiting
                if self.config.rate_limit_delay > 0:
                    time.sleep(self.config.rate_limit_delay)
                    
            except Exception as e:
                logger.error(f"Error searching Semantic Scholar with query '{query[:50]}...': {e}")
                continue
        
        # Filter by publication date and remove duplicates
        cutoff_date = datetime.now() - timedelta(days=days_back)
        unique_papers = self._filter_and_deduplicate(papers, cutoff_date)
        
        logger.info(f"Found {len(unique_papers)} unique papers from Semantic Scholar")
        return unique_papers[:max_results]
    
    def _search_query(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Execute a single search query.
        
        Args:
            query: Search query string
            limit: Maximum results for this query
            
        Returns:
            List of paper data
        """
        url = f"{self.config.base_url}/paper/search"
        params = {
            'query': query,
            'limit': min(limit, self.config.papers_per_request),
            'fields': ','.join(self.config.fields)
        }
        
                # Add retry logic with exponential backoff for rate limiting
        max_retries = 3
        base_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.config.request_timeout
                )
                response.raise_for_status()
                
                data = response.json()
                return data.get('data', [])
                
            except requests.HTTPError as e:
                if e.response.status_code == 429 and attempt < max_retries - 1:
                    # Rate limited - wait and retry with exponential backoff
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Rate limited by Semantic Scholar, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    raise  # Re-raise if not rate limited or out of retries
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Request failed, retrying in {delay:.1f}s: {e}")
                    time.sleep(delay)
                    continue
                else:
                    raise  # Re-raise if out of retries
        
        return []  # Fallback if all retries failed
    
    def _build_queries(self, user_interests: UserInterests) -> List[str]:
        """Build search queries from user interests.
        
        Args:
            user_interests: User's research interests
            
        Returns:
            List of search query strings
        """
        queries = []
        
        # Research area queries
        if user_interests.research_areas:
            for area in user_interests.research_areas[:3]:  # Limit queries
                queries.append(area)
        
        # Keyword queries - combine related keywords
        if user_interests.keywords:
            # Group keywords for more effective search
            keyword_groups = self._group_keywords(user_interests.keywords)
            for keyword_group in keyword_groups:
                query = " OR ".join(keyword_group)
                queries.append(query)
        
        # Fallback queries for AI/ML
        if not queries:
            queries.extend([
                "machine learning",
                "artificial intelligence", 
                "deep learning",
                "computer vision",
                "natural language processing"
            ])
        
        return queries[:5]  # Limit to 5 queries for performance
    
    def _group_keywords(self, keywords: List[str]) -> List[List[str]]:
        """Group keywords into logical query groups.
        
        Args:
            keywords: List of keywords
            
        Returns:
            List of keyword groups
        """
        # Group related keywords together
        groups = []
        current_group = []
        
        for keyword in keywords:
            current_group.append(keyword)
            # Create groups of 2-3 keywords for effective OR queries
            if len(current_group) >= 3:
                groups.append(current_group)
                current_group = []
        
        if current_group:
            groups.append(current_group)
            
        return groups
    
    def _filter_and_deduplicate(
        self, 
        papers: List[Dict[str, Any]], 
        cutoff_date: datetime
    ) -> List[Dict[str, Any]]:
        """Filter papers by date and remove duplicates.
        
        Args:
            papers: List of papers to filter
            cutoff_date: Minimum publication date
            
        Returns:
            Filtered and deduplicated papers
        """
        seen_ids = set()
        unique_papers = []
        
        for paper in papers:
            # Check publication date
            pub_date = self._parse_publication_date(paper)
            if pub_date and pub_date < cutoff_date:
                continue
            
            # Remove duplicates based on paper ID
            paper_id = paper.get('paperId')
            if not paper_id or paper_id in seen_ids:
                continue
                
            seen_ids.add(paper_id)
            unique_papers.append(paper)
        
        return unique_papers
    
    def _parse_publication_date(self, paper: Dict[str, Any]) -> Optional[datetime]:
        """Parse publication date from paper data.
        
        Args:
            paper: Paper data from Semantic Scholar
            
        Returns:
            Publication date or None if not available
        """
        # Try publication date first
        pub_date_str = paper.get('publicationDate')
        if pub_date_str:
            try:
                return datetime.strptime(pub_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        # Fall back to year
        year = paper.get('year')
        if year:
            try:
                return datetime(year, 1, 1)
            except (ValueError, TypeError):
                pass
        
        return None


class SemanticScholarConverter:
    """Convert Semantic Scholar papers to TrendingPaper format."""
    
    def convert_paper(self, ss_data: Dict[str, Any]) -> Optional[TrendingPaper]:
        """Convert Semantic Scholar paper data to TrendingPaper.
        
        Args:
            ss_data: Paper data from Semantic Scholar API
            
        Returns:
            TrendingPaper object or None if conversion fails
        """
        try:
            # Extract basic information
            title = ss_data.get('title', '').strip()
            abstract = ss_data.get('abstract', '').strip()
            
            if not title:
                return None
            
            # Extract authors
            authors = []
            for author in ss_data.get('authors', []):
                name = author.get('name')
                if name:
                    authors.append(name)
            
            # Extract arXiv ID if available
            arxiv_id = None
            external_ids = ss_data.get('externalIds', {})
            if external_ids:
                arxiv_id = external_ids.get('ArXiv')
            
            # Create engagement metrics from Semantic Scholar data
            citation_count = ss_data.get('citationCount', 0) or 0
            influential_citations = ss_data.get('influentialCitationCount', 0) or 0
            reference_count = ss_data.get('referenceCount', 0) or 0
            
            engagement = EngagementMetrics(
                github_stars=0,  # Will be enriched by Papers with Code later
                github_forks=0,
                citation_count=citation_count,
                                  # reference_count and recent_activity_score are not valid EngagementMetrics fields
            )
            
            # Extract publication date
            pub_date = self._parse_publication_date(ss_data)
            
            # Extract categories
            categories = []
            fields_of_study = ss_data.get('fieldsOfStudy', [])
            if fields_of_study:
                categories.extend(fields_of_study)
            
            # Determine trending reasons
            trending_reasons = [TrendingReason.CITATION_VELOCITY]
            if influential_citations > 10:
                trending_reasons.append(TrendingReason.COMMUNITY_INTEREST)
            
            # Create trending paper
            paper = TrendingPaper(
                title=title,
                abstract=abstract,
                authors=authors,
                arxiv_id=arxiv_id,
                arxiv_url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
                pdf_url=self._extract_pdf_url(ss_data),
                publication_date=pub_date,
                categories=categories,
                engagement=engagement,
                trending_reasons=trending_reasons,
                discovery_source="semantic_scholar",
                trending_score=engagement.calculate_engagement_score()
            )
            
            return paper
            
        except Exception as e:
            logger.error(f"Error converting Semantic Scholar paper: {e}")
            return None
    
    def _parse_publication_date(self, paper: Dict[str, Any]) -> Optional[datetime]:
        """Parse publication date from paper data."""
        pub_date_str = paper.get('publicationDate')
        if pub_date_str:
            try:
                return datetime.strptime(pub_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        year = paper.get('year')
        if year:
            try:
                return datetime(year, 1, 1)
            except (ValueError, TypeError):
                pass
        
        return None
    
    def _extract_pdf_url(self, paper: Dict[str, Any]) -> Optional[str]:
        """Extract PDF URL from paper data."""
        open_access_pdf = paper.get('openAccessPdf')
        if open_access_pdf and isinstance(open_access_pdf, dict):
            return open_access_pdf.get('url')
        return None
    
    def _calculate_impact_score(self, citations: int, influential_citations: int) -> float:
        """Calculate impact score based on citation metrics.
        
        Args:
            citations: Total citation count
            influential_citations: Influential citation count
            
        Returns:
            Impact score (0-100)
        """
        # Weight influential citations more heavily
        weighted_score = citations + (influential_citations * 3)
        
        # Apply logarithmic scaling for large citation counts
        if weighted_score == 0:
            return 0.0
        elif weighted_score < 10:
            return min(weighted_score * 5, 50.0)  # Linear for small counts
        else:
            # Logarithmic scaling for high citation papers
            import math
            return min(50 + math.log10(weighted_score) * 10, 100.0)


def discover_impactful_papers(
    user_interests: UserInterests,
    config: Optional[SemanticScholarConfig] = None,
    days_back: int = 30,
    max_papers: int = 100
) -> List[TrendingPaper]:
    """Discover impactful papers from Semantic Scholar.
    
    Args:
        user_interests: User's research interests
        config: Semantic Scholar API configuration
        days_back: Days to look back for papers (longer periods work better)
        max_papers: Maximum number of papers to return
        
    Returns:
        List of trending papers sorted by impact and citations
    """
    api = SemanticScholarAPI(config)
    converter = SemanticScholarConverter()
    
    # Get papers from Semantic Scholar
    ss_papers = api.search_papers(user_interests, days_back, max_papers)
    
    # Convert to TrendingPaper format
    trending_papers = []
    for ss_data in ss_papers:
        paper = converter.convert_paper(ss_data)
        if paper:
            trending_papers.append(paper)
    
    # Sort by trending score (impact-based for Semantic Scholar)
    trending_papers.sort(key=lambda p: p.trending_score, reverse=True)
    
    logger.info(f"Discovered {len(trending_papers)} impactful papers from Semantic Scholar")
    return trending_papers 