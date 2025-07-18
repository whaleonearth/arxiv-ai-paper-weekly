"""ArXiv API integration for discovering recent papers.

This module integrates with the arXiv API to discover recent papers
in AI/ML fields based on user interests and engagement metrics.
ArXiv is extremely fast and reliable with comprehensive AI/ML coverage.
"""

import arxiv
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
class ArxivConfig:
    """Configuration for arXiv API integration."""
    max_results_per_query: int = 100
    request_timeout: int = 30
    rate_limit_delay: float = 0.1  # arXiv allows 3 requests/second
    sort_order: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate


class ArxivAPI:
    """Client for arXiv API with optimized queries."""
    
    def __init__(self, config: Optional[ArxivConfig] = None):
        """Initialize arXiv API client.
        
        Args:
            config: Configuration for the API client
        """
        import os
        self.config = config or ArxivConfig()
        # Allow environment variable override for rate limiting
        env_delay = os.getenv('ARXIV_RATE_LIMIT_DELAY')
        if env_delay:
            self.config.rate_limit_delay = float(env_delay)
        
        self.client = arxiv.Client()
    
    def search_papers(
        self, 
        user_interests: UserInterests,
        days_back: int = 7,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for papers based on user interests.
        
        Args:
            user_interests: User's research interests
            days_back: Number of days to look back
            max_results: Maximum number of papers to return
            
        Returns:
            List of paper data from arXiv API
        """
        papers = []
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        # Build queries based on user interests
        queries = self._build_queries(user_interests)
        
        for query in queries:
            try:
                logger.debug(f"Searching arXiv with query: {query[:100]}...")
                
                search = arxiv.Search(
                    query=query,
                    max_results=min(self.config.max_results_per_query, max_results),
                    sort_by=self.config.sort_order
                )
                
                query_papers = []
                for result in self.client.results(search):
                    # Filter by publication date
                    if result.published.replace(tzinfo=None) < cutoff_date:
                        continue
                        
                    paper_data = self._convert_arxiv_result(result)
                    query_papers.append(paper_data)
                
                papers.extend(query_papers)
                logger.debug(f"Found {len(query_papers)} papers for query")
                
                # Rate limiting
                if self.config.rate_limit_delay > 0:
                    time.sleep(self.config.rate_limit_delay)
                    
            except Exception as e:
                logger.error(f"Error searching arXiv with query '{query[:50]}...': {e}")
                continue
        
        # Remove duplicates based on arXiv ID
        seen_ids = set()
        unique_papers = []
        for paper in papers:
            arxiv_id = paper.get('arxiv_id')
            if arxiv_id and arxiv_id not in seen_ids:
                seen_ids.add(arxiv_id)
                unique_papers.append(paper)
        
        logger.info(f"Found {len(unique_papers)} unique papers from arXiv")
        return unique_papers[:max_results]
    
    def _build_queries(self, user_interests: UserInterests) -> List[str]:
        """Build search queries from user interests.
        
        Args:
            user_interests: User's research interests
            
        Returns:
            List of search query strings
        """
        queries = []
        
        # Category-based queries (most reliable)
        if user_interests.categories:
            for category in user_interests.categories:
                queries.append(f"cat:{category}")
        
        # Research area queries combined with AI/ML categories
        ai_categories = ["cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.RO", "stat.ML"]
        if user_interests.research_areas:
            for area in user_interests.research_areas[:3]:  # Limit to avoid too many queries
                category_query = " OR ".join([f"cat:{cat}" for cat in ai_categories])
                queries.append(f"({category_query}) AND all:{area}")
        
        # Keyword-based queries with category constraints
        if user_interests.keywords:
            # Group keywords for efficient queries
            keyword_groups = self._group_keywords(user_interests.keywords)
            for keyword_group in keyword_groups:
                keyword_query = " OR ".join([f'all:"{kw}"' for kw in keyword_group])
                category_query = " OR ".join([f"cat:{cat}" for cat in ai_categories])
                queries.append(f"({category_query}) AND ({keyword_query})")
        
        # Fallback: general AI/ML query if no specific interests
        if not queries:
            queries.append("cat:cs.AI OR cat:cs.LG OR cat:cs.CV OR cat:cs.CL")
        
        return queries[:5]  # Limit to 5 queries for performance
    
    def _group_keywords(self, keywords: List[str]) -> List[List[str]]:
        """Group keywords into logical query groups.
        
        Args:
            keywords: List of keywords
            
        Returns:
            List of keyword groups
        """
        # Group similar keywords together
        groups = []
        current_group = []
        
        for keyword in keywords:
            current_group.append(keyword)
            # Limit group size to avoid overly complex queries
            if len(current_group) >= 3:
                groups.append(current_group)
                current_group = []
        
        if current_group:
            groups.append(current_group)
            
        return groups
    
    def _convert_arxiv_result(self, result: arxiv.Result) -> Dict[str, Any]:
        """Convert arXiv result to standardized format.
        
        Args:
            result: arXiv API result
            
        Returns:
            Standardized paper data dictionary
        """
        # Extract arXiv ID (remove version number)
        arxiv_id = result.get_short_id()
        if 'v' in arxiv_id:
            arxiv_id = arxiv_id.split('v')[0]
        
        return {
            'title': result.title,
            'abstract': result.summary,
            'authors': [str(author) for author in result.authors],
            'arxiv_id': arxiv_id,
            'arxiv_url': result.entry_id,
            'pdf_url': result.pdf_url,
            'publication_date': result.published.replace(tzinfo=None),
            'categories': [str(cat) for cat in result.categories],
            'primary_category': str(result.primary_category),
            'source': 'arxiv'
        }


class ArxivConverter:
    """Convert arXiv papers to TrendingPaper format."""
    
    def convert_paper(self, arxiv_data: Dict[str, Any]) -> Optional[TrendingPaper]:
        """Convert arXiv paper data to TrendingPaper.
        
        Args:
            arxiv_data: Paper data from arXiv API
            
        Returns:
            TrendingPaper object or None if conversion fails
        """
        try:
            # Create basic engagement metrics (arXiv doesn't provide stars/forks)
            engagement = EngagementMetrics(
                github_stars=0,  # Will be enriched by Papers with Code later
                github_forks=0,
                citation_count=0,  # Will be enriched by Semantic Scholar later
                                  # paper_mentions and recent_activity_score are not valid EngagementMetrics fields
            )
            
            # Create trending paper
            paper = TrendingPaper(
                title=arxiv_data['title'],
                abstract=arxiv_data['abstract'],
                authors=arxiv_data['authors'],
                arxiv_id=arxiv_data['arxiv_id'],
                arxiv_url=arxiv_data['arxiv_url'],
                pdf_url=arxiv_data['pdf_url'],
                publication_date=arxiv_data['publication_date'],
                categories=arxiv_data['categories'],
                engagement=engagement,
                trending_reasons=[TrendingReason.RECENT_PUBLICATION],
                discovery_source="arxiv",
                trending_score=engagement.calculate_engagement_score()
            )
            
            return paper
            
        except Exception as e:
            logger.error(f"Error converting arXiv paper: {e}")
            return None
    
    def _calculate_recency_score(self, pub_date: Optional[datetime]) -> float:
        """Calculate recency score based on publication date.
        
        Args:
            pub_date: Publication date
            
        Returns:
            Recency score (0-100)
        """
        if not pub_date:
            return 0.0
            
        days_ago = (datetime.now() - pub_date).days
        
        # Score decays exponentially with time
        # Recent papers (0-3 days) get high scores
        if days_ago <= 1:
            return 100.0
        elif days_ago <= 3:
            return 80.0
        elif days_ago <= 7:
            return 60.0
        elif days_ago <= 14:
            return 40.0
        elif days_ago <= 30:
            return 20.0
        else:
            return 5.0


def discover_recent_papers(
    user_interests: UserInterests,
    config: Optional[ArxivConfig] = None,
    days_back: int = 7,
    max_papers: int = 100
) -> List[TrendingPaper]:
    """Discover recent papers from arXiv.
    
    Args:
        user_interests: User's research interests
        config: arXiv API configuration
        days_back: Days to look back for papers
        max_papers: Maximum number of papers to return
        
    Returns:
        List of trending papers sorted by recency and relevance
    """
    api = ArxivAPI(config)
    converter = ArxivConverter()
    
    # Get papers from arXiv
    arxiv_papers = api.search_papers(user_interests, days_back, max_papers)
    
    # Convert to TrendingPaper format
    trending_papers = []
    for arxiv_data in arxiv_papers:
        paper = converter.convert_paper(arxiv_data)
        if paper:
            trending_papers.append(paper)
    
    # Sort by trending score (recency-based for arXiv)
    trending_papers.sort(key=lambda p: p.trending_score, reverse=True)
    
    logger.info(f"Discovered {len(trending_papers)} recent papers from arXiv")
    return trending_papers 