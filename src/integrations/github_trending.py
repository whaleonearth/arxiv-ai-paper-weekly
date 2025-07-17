"""GitHub trending repository analysis for paper discovery.

This module analyzes trending GitHub repositories to discover related research papers.
It focuses on repositories with academic papers, research implementations, and
high-quality code that might indicate trending research areas.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timedelta
import requests
import re
import time
from urllib.parse import urljoin, urlparse
from loguru import logger

from ..data.paper_models import TrendingPaper, CodeRepository, EngagementMetrics, TrendingReason


@dataclass
class GitHubRepository:
    """GitHub repository information."""
    full_name: str
    name: str
    description: Optional[str]
    html_url: str
    clone_url: str
    stars: int
    forks: int
    language: Optional[str]
    topics: List[str]
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    open_issues: int
    has_wiki: bool
    has_pages: bool
    license_name: Optional[str]
    
    # Paper-related fields
    arxiv_links: List[str]
    paper_references: List[str]
    readme_content: Optional[str] = None


class GitHubTrendingAPI:
    """GitHub API client for discovering trending repositories."""
    
    def __init__(self, token: Optional[str] = None, rate_limit_delay: float = 1.0):
        """Initialize GitHub API client.
        
        Args:
            token: GitHub personal access token (optional but recommended)
            rate_limit_delay: Delay between API calls in seconds
        """
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.rate_limit_delay = rate_limit_delay
        
        # Set up authentication if token provided
        if token:
            self.session.headers.update({
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            })
        else:
            logger.warning("No GitHub token provided - API rate limits will be more restrictive")
    
    def search_repositories(
        self,
        query: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 30,
        created_since_days: int = 30
    ) -> List[GitHubRepository]:
        """Search for repositories matching criteria.
        
        Args:
            query: Search query (e.g., "machine learning", "computer vision")
            sort: Sort criteria (stars, forks, updated)
            order: Sort order (asc, desc)
            per_page: Results per page (max 100)
            created_since_days: Only repos created in last N days
            
        Returns:
            List of GitHubRepository objects
        """
        since_date = (datetime.now() - timedelta(days=created_since_days)).strftime("%Y-%m-%d")
        
        # Build search query with filters
        search_query = f"{query} created:>{since_date}"
        
        params = {
            "q": search_query,
            "sort": sort,
            "order": order,
            "per_page": per_page
        }
        
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(f"{self.base_url}/search/repositories", params=params)
            response.raise_for_status()
            
            data = response.json()
            repositories = []
            
            for item in data.get("items", []):
                repo = self._parse_repository(item)
                if repo:
                    repositories.append(repo)
                    
            logger.info(f"Found {len(repositories)} repositories for query: {query}")
            return repositories
            
        except requests.RequestException as e:
            logger.error(f"GitHub API error for query '{query}': {e}")
            return []
    
    def get_trending_ml_repositories(self, days_back: int = 7) -> List[GitHubRepository]:
        """Get trending machine learning repositories.
        
        Args:
            days_back: Look for repos trending in last N days
            
        Returns:
            List of trending ML repositories
        """
        ml_queries = [
            "machine learning",
            "deep learning", 
            "neural networks",
            "computer vision",
            "natural language processing",
            "artificial intelligence",
            "reinforcement learning",
            "transformers",
            "diffusion models"
        ]
        
        all_repos = []
        for query in ml_queries:
            repos = self.search_repositories(
                query=query,
                created_since_days=days_back,
                per_page=20
            )
            all_repos.extend(repos)
            
        # Remove duplicates and sort by engagement
        unique_repos = self._remove_duplicate_repos(all_repos)
        return sorted(unique_repos, key=lambda r: r.stars + r.forks, reverse=True)
    
    def fetch_readme_content(self, repo: GitHubRepository) -> Optional[str]:
        """Fetch README content for a repository.
        
        Args:
            repo: Repository to fetch README for
            
        Returns:
            README content as string, or None if not found
        """
        readme_files = ["README.md", "README.rst", "README.txt", "README"]
        
        for readme_file in readme_files:
            try:
                time.sleep(self.rate_limit_delay)
                url = f"{self.base_url}/repos/{repo.full_name}/contents/{readme_file}"
                response = self.session.get(url)
                
                if response.status_code == 200:
                    content_data = response.json()
                    if content_data.get("encoding") == "base64":
                        import base64
                        content = base64.b64decode(content_data["content"]).decode("utf-8")
                        repo.readme_content = content
                        return content
                        
            except (requests.RequestException, UnicodeDecodeError) as e:
                logger.debug(f"Could not fetch {readme_file} for {repo.full_name}: {e}")
                continue
                
        return None
    
    def _parse_repository(self, item: Dict[str, Any]) -> Optional[GitHubRepository]:
        """Parse repository data from GitHub API response.
        
        Args:
            item: Repository item from GitHub API
            
        Returns:
            GitHubRepository object or None if parsing fails
        """
        try:
            # Parse dates
            created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            updated_at = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
            pushed_at = datetime.fromisoformat(item["pushed_at"].replace("Z", "+00:00"))
            
            # Extract license info
            license_name = None
            if item.get("license") and item["license"]:
                license_name = item["license"].get("name")
            
            repo = GitHubRepository(
                full_name=item["full_name"],
                name=item["name"],
                description=item.get("description"),
                html_url=item["html_url"],
                clone_url=item["clone_url"],
                stars=item["stargazers_count"],
                forks=item["forks_count"],
                language=item.get("language"),
                topics=item.get("topics", []),
                created_at=created_at,
                updated_at=updated_at,
                pushed_at=pushed_at,
                open_issues=item["open_issues_count"],
                has_wiki=item["has_wiki"],
                has_pages=item["has_pages"],
                license_name=license_name,
                arxiv_links=[],
                paper_references=[]
            )
            
            return repo
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing repository data: {e}")
            return None
    
    def _remove_duplicate_repos(self, repos: List[GitHubRepository]) -> List[GitHubRepository]:
        """Remove duplicate repositories based on full_name.
        
        Args:
            repos: List of repositories
            
        Returns:
            List with duplicates removed
        """
        seen = set()
        unique_repos = []
        
        for repo in repos:
            if repo.full_name not in seen:
                seen.add(repo.full_name)
                unique_repos.append(repo)
                
        return unique_repos


class GitHubPaperExtractor:
    """Extract paper references from GitHub repositories."""
    
    # Regex patterns for finding arXiv links
    ARXIV_PATTERNS = [
        r'https?://arxiv\.org/abs/(\d{4}\.\d{4,5})',
        r'https?://arxiv\.org/pdf/(\d{4}\.\d{4,5})\.pdf',
        r'arXiv:(\d{4}\.\d{4,5})',
        r'arxiv\.org/abs/(\d{4}\.\d{4,5})',
    ]
    
    # Patterns for paper references in README
    PAPER_REFERENCE_PATTERNS = [
        r'\[([^\]]*paper[^\]]*)\]\s*\([^)]*\)',  # [Paper] (link)
        r'(?:paper|publication|article):\s*([^\n]+)',  # Paper: Title
        r'based on the paper[:\s]*"([^"]+)"',  # Based on the paper "Title"
        r'implements[:\s]*"([^"]+)"',  # Implements "Title"
    ]
    
    def extract_arxiv_references(self, repo: GitHubRepository) -> List[str]:
        """Extract arXiv paper IDs from repository.
        
        Args:
            repo: Repository to analyze
            
        Returns:
            List of arXiv IDs found
        """
        arxiv_ids = set()
        search_text = ""
        
        # Search in description
        if repo.description:
            search_text += repo.description + " "
            
        # Search in README if available  
        if repo.readme_content:
            search_text += repo.readme_content + " "
            
        # Search in topics
        search_text += " ".join(repo.topics)
        
        # Find arXiv links
        for pattern in self.ARXIV_PATTERNS:
            matches = re.finditer(pattern, search_text, re.IGNORECASE)
            for match in matches:
                arxiv_ids.add(match.group(1))
                
        repo.arxiv_links = list(arxiv_ids)
        return list(arxiv_ids)
    
    def extract_paper_references(self, repo: GitHubRepository) -> List[str]:
        """Extract general paper references from repository.
        
        Args:
            repo: Repository to analyze
            
        Returns:
            List of paper titles/references found
        """
        references = set()
        search_text = repo.readme_content or ""
        
        for pattern in self.PAPER_REFERENCE_PATTERNS:
            matches = re.finditer(pattern, search_text, re.IGNORECASE)
            for match in matches:
                title = match.group(1).strip()
                if len(title) > 10:  # Filter out short matches
                    references.add(title)
                    
        repo.paper_references = list(references)
        return list(references)


class GitHubTrendingConverter:
    """Convert GitHub repositories to TrendingPaper objects."""
    
    def __init__(self, github_api: GitHubTrendingAPI, paper_extractor: GitHubPaperExtractor):
        """Initialize converter.
        
        Args:
            github_api: GitHub API client
            paper_extractor: Paper reference extractor
        """
        self.github_api = github_api
        self.paper_extractor = paper_extractor
    
    def repository_to_trending_paper(
        self,
        repo: GitHubRepository,
        arxiv_api_client = None
    ) -> Optional[TrendingPaper]:
        """Convert GitHub repository to TrendingPaper.
        
        Args:
            repo: GitHub repository
            arxiv_api_client: Optional arXiv API client for fetching paper details
            
        Returns:
            TrendingPaper object or None if no papers found
        """
        # Fetch README if not already loaded
        if not repo.readme_content:
            self.github_api.fetch_readme_content(repo)
            
        # Extract paper references
        arxiv_ids = self.paper_extractor.extract_arxiv_references(repo)
        paper_refs = self.paper_extractor.extract_paper_references(repo)
        
        # Skip if no paper connections found
        if not arxiv_ids and not paper_refs:
            return None
            
        # Create CodeRepository object
        code_repo = CodeRepository(
            url=repo.html_url,
            name=repo.name,
            description=repo.description or "",
            stars=repo.stars,
            forks=repo.forks,
            primary_language=repo.language,
            license_type=repo.license_name,
            last_commit_date=repo.pushed_at,
            has_documentation=bool(repo.readme_content and len(repo.readme_content) > 500),
            has_tests=self._has_tests(repo),
            has_examples=self._has_examples(repo),
        )
        
        # Create engagement metrics
        engagement = EngagementMetrics(
            github_stars=repo.stars,
            github_forks=repo.forks,
            github_issues=repo.open_issues,
            days_since_publication=max(1, (datetime.now() - repo.created_at).days),
            last_activity_date=repo.pushed_at
        )
        
        # Determine trending reasons
        trending_reasons = []
        if repo.stars > 100:
            trending_reasons.append(TrendingReason.HIGH_GITHUB_ACTIVITY)
        if (datetime.now() - repo.created_at).days <= 30:
            trending_reasons.append(TrendingReason.RECENT_PUBLICATION)
        if code_repo.calculate_quality_score() >= 7:
            trending_reasons.append(TrendingReason.CODE_QUALITY)
            
        # Create paper title and abstract from repository info
        title = repo.name.replace("-", " ").replace("_", " ").title()
        if repo.description:
            title = f"{title}: {repo.description}"
            
        abstract = f"Repository implementing: {repo.description or repo.name}"
        if paper_refs:
            abstract += f"\n\nRelated papers: {'; '.join(paper_refs[:3])}"
            
        # Use first arXiv ID if available
        arxiv_id = arxiv_ids[0] if arxiv_ids else None
        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None
        
        paper = TrendingPaper(
            title=title,
            abstract=abstract,
            authors=[],  # Would need to fetch from arXiv API
            arxiv_id=arxiv_id,
            arxiv_url=arxiv_url,
            primary_repository=code_repo,
            engagement=engagement,
            trending_reasons=trending_reasons,
            discovery_source="github_trending",
            categories=self._extract_categories(repo),
            publication_date=repo.created_at
        )
        
        # Calculate scores
        paper.trending_score = paper.calculate_overall_score()
        
        return paper
    
    def _has_tests(self, repo: GitHubRepository) -> bool:
        """Check if repository likely has tests."""
        indicators = [
            "test" in repo.name.lower(),
            "pytest" in (repo.readme_content or "").lower(),
            "unittest" in (repo.readme_content or "").lower(),
            "testing" in (repo.readme_content or "").lower(),
            any("test" in topic for topic in repo.topics)
        ]
        return any(indicators)
    
    def _has_examples(self, repo: GitHubRepository) -> bool:
        """Check if repository likely has examples."""
        indicators = [
            "example" in (repo.readme_content or "").lower(),
            "demo" in (repo.readme_content or "").lower(),
            "tutorial" in (repo.readme_content or "").lower(),
            any("example" in topic for topic in repo.topics)
        ]
        return any(indicators)
    
    def _extract_categories(self, repo: GitHubRepository) -> List[str]:
        """Extract likely arXiv categories from repository."""
        category_mapping = {
            "machine learning": ["cs.LG"],
            "computer vision": ["cs.CV"],
            "natural language": ["cs.CL"],
            "nlp": ["cs.CL"],
            "robotics": ["cs.RO"],
            "ai": ["cs.AI"],
            "artificial intelligence": ["cs.AI"],
        }
        
        categories = []
        search_text = f"{repo.name} {repo.description or ''} {' '.join(repo.topics)}".lower()
        
        for keyword, cats in category_mapping.items():
            if keyword in search_text:
                categories.extend(cats)
                
        return list(set(categories))


def discover_trending_papers_from_github(
    github_token: Optional[str] = None,
    days_back: int = 7,
    max_papers: int = 50
) -> List[TrendingPaper]:
    """Discover trending papers from GitHub repositories.
    
    Args:
        github_token: GitHub personal access token
        days_back: Look for repos trending in last N days
        max_papers: Maximum number of papers to return
        
    Returns:
        List of TrendingPaper objects sorted by trending score
    """
    try:
        # Initialize components
        github_api = GitHubTrendingAPI(token=github_token)
        paper_extractor = GitHubPaperExtractor()
        converter = GitHubTrendingConverter(github_api, paper_extractor)
        
        # Get trending repositories
        trending_repos = github_api.get_trending_ml_repositories(days_back=days_back)
        logger.info(f"Found {len(trending_repos)} trending ML repositories")
        
        # Convert to papers
        papers = []
        for repo in trending_repos:
            paper = converter.repository_to_trending_paper(repo)
            if paper:
                papers.append(paper)
                
        # Sort by trending score and limit results
        papers.sort(key=lambda p: p.trending_score, reverse=True)
        result = papers[:max_papers]
        
        logger.info(f"Discovered {len(result)} trending papers from GitHub")
        return result
        
    except Exception as e:
        logger.error(f"Error discovering papers from GitHub: {e}")
        return [] 