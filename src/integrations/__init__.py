"""External API integration modules."""

from .papers_with_code import (
    PapersWithCodeAPI,
    PapersWithCodeConverter,
    discover_trending_papers
)

from .github_trending import (
    GitHubTrendingAPI,
    GitHubPaperExtractor,
    GitHubTrendingConverter,
    discover_trending_papers_from_github
)

from .arxiv_api import (
    ArxivAPI,
    ArxivConverter,
    discover_recent_papers
)

from .semantic_scholar_api import (
    SemanticScholarAPI,
    SemanticScholarConverter,
    discover_impactful_papers
)

from .papers_enrichment import (
    PapersWithCodeEnricher,
    enrich_papers_with_code_data
)

__all__ = [
    # Papers with Code
    "PapersWithCodeAPI",
    "PapersWithCodeConverter", 
    "discover_trending_papers",
    
    # GitHub Trending
    "GitHubTrendingAPI",
    "GitHubPaperExtractor",
    "GitHubTrendingConverter",
    "discover_trending_papers_from_github",
    
    # arXiv API
    "ArxivAPI",
    "ArxivConverter",
    "discover_recent_papers",
    
    # Semantic Scholar
    "SemanticScholarAPI",
    "SemanticScholarConverter",
    "discover_impactful_papers",
    
    # Papers with Code Enrichment
    "PapersWithCodeEnricher",
    "enrich_papers_with_code_data"
] 