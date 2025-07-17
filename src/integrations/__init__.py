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

__all__ = [
    "PapersWithCodeAPI",
    "PapersWithCodeConverter", 
    "discover_trending_papers",
    "GitHubTrendingAPI",
    "GitHubPaperExtractor",
    "GitHubTrendingConverter",
    "discover_trending_papers_from_github"
] 