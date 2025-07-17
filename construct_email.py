from paper import ArxivPaper
import math
from tqdm import tqdm
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import smtplib
import datetime
from loguru import logger
from typing import List, Union

# Import TrendingPaper for type hints
try:
    from src.data.paper_models import TrendingPaper
except ImportError:
    # Fallback for when imports might not work
    TrendingPaper = None

framework = """
<!DOCTYPE HTML>
<html>
<head>
  <style>
    .star-wrapper {
      font-size: 1.3em; /* 调整星星大小 */
      line-height: 1; /* 确保垂直对齐 */
      display: inline-flex;
      align-items: center; /* 保持对齐 */
    }
    .half-star {
      display: inline-block;
      width: 0.5em; /* 半颗星的宽度 */
      overflow: hidden;
      white-space: nowrap;
      vertical-align: middle;
    }
    .full-star {
      vertical-align: middle;
    }
    .trending-badge {
      display: inline-block;
      background-color: #ff6b35;
      color: white;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: bold;
      margin: 2px;
    }
    .engagement-metrics {
      background-color: #e8f4fd;
      padding: 8px;
      border-radius: 4px;
      margin: 8px 0;
      border-left: 4px solid #2196f3;
    }
    .ai-summary {
      background-color: #f0f8f0;
      padding: 12px;
      border-radius: 6px;
      margin: 8px 0;
      border-left: 4px solid #4caf50;
      font-style: italic;
    }
    .code-quality {
      background-color: #fff3e0;
      padding: 6px;
      border-radius: 4px;
      margin: 4px 0;
      font-size: 12px;
    }
  </style>
</head>
<body>

<div>
    __CONTENT__
</div>

<br><br>
<div>
To unsubscribe, remove your email in your Github Action setting.
<br><small>Powered by Engagement-Based Discovery - Finding trending papers with active code implementations</small>
</div>

</body>
</html>
"""

def get_empty_html():
  block_template = """
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
  <tr>
    <td style="font-size: 20px; font-weight: bold; color: #333;">
        No Papers Today. Take a Rest!
    </td>
  </tr>
  </table>
  """
  return block_template

def get_block_html(title:str, authors:str, rate:str,arxiv_id:str, abstract:str, pdf_url:str, code_url:str=None, affiliations:str=None):
    code = f'<a href="{code_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #5bc0de; padding: 8px 16px; border-radius: 4px; margin-left: 8px;">Code</a>' if code_url else ''
    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #666; padding: 8px 0;">
            {authors}
            <br>
            <i>{affiliations}</i>
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Relevance:</strong> {rate}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>arXiv ID:</strong> {arxiv_id}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {abstract}
        </td>
    </tr>

    <tr>
        <td style="padding: 8px 0;">
            <a href="{pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #d9534f; padding: 8px 16px; border-radius: 4px;">PDF</a>
            {code}
        </td>
    </tr>
</table>
"""
    return block_template.format(title=title, authors=authors,rate=rate,arxiv_id=arxiv_id, abstract=abstract, pdf_url=pdf_url, code=code, affiliations=affiliations)

def get_trending_block_html(paper) -> str:
    """Create enhanced HTML block for TrendingPaper objects."""
    if TrendingPaper is None or not hasattr(paper, 'trending_score'):
        # Fallback to original format for ArxivPaper objects
        authors = [a.name for a in paper.authors[:5]] if hasattr(paper, 'authors') and paper.authors else []
        authors_str = ', '.join(authors)
        if hasattr(paper, 'authors') and len(paper.authors) > 5:
            authors_str += ', ...'
        return get_block_html(
            title=paper.title,
            authors=authors_str,
            rate=get_stars(getattr(paper, 'score', 0)),
            arxiv_id=getattr(paper, 'arxiv_id', 'N/A'),
            abstract=getattr(paper, 'tldr', getattr(paper, 'abstract', '')[:200] + '...'),
            pdf_url=getattr(paper, 'pdf_url', '#'),
            code_url=getattr(paper, 'code_url', None),
            affiliations=getattr(paper, 'affiliations', ['Unknown'])[0] if getattr(paper, 'affiliations', None) else 'Unknown'
        )
    
    # Enhanced rendering for TrendingPaper objects
    authors = ', '.join(paper.authors[:5]) if paper.authors else 'Not specified'
    if paper.authors and len(paper.authors) > 5:
        authors += ', ...'
    
    # Format trending score as stars
    rate_stars = get_engagement_stars(paper.trending_score)
    
    # Create trending reasons badges
    trending_badges = ''
    if paper.trending_reasons:
        for reason in paper.trending_reasons:
            trending_badges += f'<span class="trending-badge">{reason.value.replace("_", " ").title()}</span>'
    
    # Engagement metrics
    engagement_html = ''
    if paper.engagement:
        metrics = []
        if paper.engagement.github_stars > 0:
            metrics.append(f"⭐ {paper.engagement.github_stars} stars")
        if paper.engagement.github_forks > 0:
            metrics.append(f"🍴 {paper.engagement.github_forks} forks")
        if paper.engagement.citation_count > 0:
            metrics.append(f"📚 {paper.engagement.citation_count} citations")
        
        if metrics:
            engagement_html = f'<div class="engagement-metrics"><strong>Engagement:</strong> {" • ".join(metrics)}</div>'
    
    # Code quality info
    code_quality_html = ''
    code_links = ''
    if paper.primary_repository:
        quality_score = paper.primary_repository.calculate_quality_score()
        quality_features = []
        if paper.primary_repository.has_documentation:
            quality_features.append("📖 Docs")
        if paper.primary_repository.has_tests:
            quality_features.append("🧪 Tests")
        if paper.primary_repository.has_examples:
            quality_features.append("💡 Examples")
        if paper.primary_repository.license_type:
            quality_features.append(f"⚖️ {paper.primary_repository.license_type}")
            
        if quality_features:
            code_quality_html = f'<div class="code-quality"><strong>Code Quality ({quality_score:.1f}/10):</strong> {" • ".join(quality_features)}</div>'
        
        # Primary code link
        code_links += f'<a href="{paper.primary_repository.url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #28a745; padding: 8px 16px; border-radius: 4px; margin-right: 8px;">💻 Code</a>'
    
    # Additional repository links
    if paper.additional_repositories:
        for i, repo in enumerate(paper.additional_repositories[:2]):  # Max 2 additional
            code_links += f'<a href="{repo.url}" style="display: inline-block; text-decoration: none; font-size: 12px; font-weight: bold; color: #fff; background-color: #6c757d; padding: 6px 12px; border-radius: 4px; margin-right: 4px;">Code {i+2}</a>'
    
    # AI-generated summary
    summary_html = ''
    if paper.tldr_summary:
        summary_html = f'<div class="ai-summary"><strong>🤖 AI Summary:</strong> {paper.tldr_summary}</div>'
    
    # PDF link
    pdf_link = ''
    if paper.pdf_url:
        pdf_link = f'<a href="{paper.pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #dc3545; padding: 8px 16px; border-radius: 4px; margin-right: 8px;">📄 PDF</a>'
    elif paper.arxiv_url:
        pdf_link = f'<a href="{paper.arxiv_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #dc3545; padding: 8px 16px; border-radius: 4px; margin-right: 8px;">📄 arXiv</a>'
    
    # Matched interests
    interests_html = ''
    if hasattr(paper, 'matched_interests') and paper.matched_interests:
        interests_html = f'<div style="font-size: 12px; color: #666; margin-top: 8px;"><strong>Matches your interests:</strong> {", ".join(paper.matched_interests[:5])}</div>'
    
    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9; margin-bottom: 16px;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333; padding-bottom: 8px;">
            {title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #666; padding-bottom: 8px;">
            <strong>Authors:</strong> {authors}
            {trending_badges}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding-bottom: 8px;">
            <strong>Trending Score:</strong> {rate_stars} <span style="color: #666;">({trending_score:.1f}/100)</span>
        </td>
    </tr>
    {arxiv_info}
    {categories_info}
    {engagement_metrics}
    {code_quality}
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Abstract:</strong> {abstract}
        </td>
    </tr>
    {ai_summary}
    <tr>
        <td style="padding: 12px 0 8px 0;">
            {pdf_link}
            {code_links}
        </td>
    </tr>
    {interests_match}
    </table>
    """
    
    # Format arXiv info
    arxiv_info = ''
    if paper.arxiv_id:
        arxiv_info = f'<tr><td style="font-size: 14px; color: #333; padding-bottom: 4px;"><strong>arXiv ID:</strong> {paper.arxiv_id}</td></tr>'
    
    # Format categories
    categories_info = ''
    if paper.categories:
        categories_info = f'<tr><td style="font-size: 14px; color: #333; padding-bottom: 8px;"><strong>Categories:</strong> {", ".join(paper.categories[:3])}</td></tr>'
    
    return block_template.format(
        title=paper.title,
        authors=authors,
        trending_badges=trending_badges,
        rate_stars=rate_stars,
        trending_score=paper.trending_score,
        arxiv_info=arxiv_info,
        categories_info=categories_info,
        engagement_metrics=engagement_html,
        code_quality=code_quality_html,
        abstract=paper.abstract[:300] + ('...' if len(paper.abstract) > 300 else ''),
        ai_summary=summary_html,
        pdf_link=pdf_link,
        code_links=code_links,
        interests_match=interests_html
    )

def get_stars(score:float):
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'
    low = 6
    high = 8
    if score <= low:
        return ''
    elif score >= high:
        return full_star * 5
    else:
        interval = (high-low) / 10
        star_num = math.ceil((score-low) / interval)
        full_star_num = int(star_num/2)
        half_star_num = star_num - full_star_num * 2
        return '<div class="star-wrapper">'+full_star * full_star_num + half_star * half_star_num + '</div>'

def get_engagement_stars(score: float) -> str:
    """Generate star rating for engagement-based trending scores (0-100 scale)."""
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'
    
    # Map 0-100 score to 0-5 stars
    # 80-100: 5 stars, 60-80: 4 stars, 40-60: 3 stars, 20-40: 2 stars, 10-20: 1 star, <10: 0 stars
    if score >= 80:
        return full_star * 5
    elif score >= 60:
        return full_star * 4 + half_star * (1 if score >= 70 else 0)
    elif score >= 40:
        return full_star * 3 + half_star * (1 if score >= 50 else 0)
    elif score >= 20:
        return full_star * 2 + half_star * (1 if score >= 30 else 0)
    elif score >= 10:
        return full_star * 1
    else:
        return '<span style="color: #ccc;">No rating</span>'


def render_email(papers: Union[List[ArxivPaper], List]) -> str:
    """Render email HTML for papers.
    
    Args:
        papers: List of paper objects (ArxivPaper or TrendingPaper)
        
    Returns:
        Complete HTML email content
    """
    parts = []
    if len(papers) == 0:
        return framework.replace('__CONTENT__', get_empty_html())
    
    # Add header with discovery info
    header_html = f"""
    <div style="background-color: #e3f2fd; padding: 16px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #2196f3;">
        <h2 style="margin: 0; color: #1976d2;">📈 Your Daily Trending Papers</h2>
        <p style="margin: 8px 0 0 0; color: #666;">
            Found {len(papers)} trending papers with high engagement metrics and code availability
        </p>
    </div>
    """
    parts.append(header_html)
    
    for i, paper in enumerate(tqdm(papers, desc='Rendering Email'), 1):
        # Add paper number
        paper_header = f"""
        <div style="background-color: #f5f5f5; padding: 8px 16px; border-radius: 4px; margin: 16px 0 8px 0;">
            <strong style="color: #333;">#{i} Trending Paper</strong>
        </div>
        """
        parts.append(paper_header)
        
        # Render paper block
        if TrendingPaper is not None and hasattr(paper, 'trending_score'):
            parts.append(get_trending_block_html(paper))
        else:
            # Fallback for old ArxivPaper format
            rate = get_stars(getattr(paper, 'score', 0))
            authors = [a.name for a in paper.authors[:5]] if hasattr(paper, 'authors') and paper.authors else []
            authors_str = ', '.join(authors)
            if hasattr(paper, 'authors') and len(paper.authors) > 5:
                authors_str += ', ...'
            
            affiliations = 'Unknown Affiliation'
            if hasattr(paper, 'affiliations') and paper.affiliations:
                affiliations = ', '.join(paper.affiliations[:5])
                if len(paper.affiliations) > 5:
                    affiliations += ', ...'
                    
            parts.append(get_block_html(
                title=paper.title,
                authors=authors_str,
                rate=rate,
                arxiv_id=getattr(paper, 'arxiv_id', 'N/A'),
                abstract=getattr(paper, 'tldr', getattr(paper, 'abstract', '')[:200] + '...'),
                pdf_url=getattr(paper, 'pdf_url', '#'),
                code_url=getattr(paper, 'code_url', None),
                affiliations=affiliations
            ))

    content = ''.join(parts)
    return framework.replace('__CONTENT__', content)


def send_email(sender:str, receiver:str, password:str,smtp_server:str,smtp_port:int, html_content:str):
    """Send email with the provided HTML content.
    
    Args:
        sender: Sender email address
        receiver: Receiver email address  
        password: Sender email password
        smtp_server: SMTP server address
        smtp_port: SMTP server port
        html_content: HTML content to send
    """
    def _format_addr(s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, 'utf-8').encode(), addr))

    msg = MIMEText(html_content, 'html', 'utf-8')
    msg['From'] = _format_addr('ArXiv Weekly Popular <%s>' % sender)
    msg['To'] = _format_addr('You <%s>' % receiver)
    today = datetime.datetime.now().strftime('%Y/%m/%d')
    msg['Subject'] = Header(f'📈 Trending AI/ML Papers {today}', 'utf-8').encode()

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        logger.info(f"Connected to SMTP server {smtp_server}:{smtp_port} with TLS")
    except Exception as e:
        logger.warning(f"Failed to use TLS: {e}")
        logger.info("Attempting to use SSL connection...")
        try:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            logger.info(f"Connected to SMTP server {smtp_server}:{smtp_port} with SSL")
        except Exception as ssl_e:
            logger.error(f"Failed to connect with SSL: {ssl_e}")
            raise

    try:
        server.login(sender, password)
        logger.info("Successfully authenticated with SMTP server")
        
        server.sendmail(sender, [receiver], msg.as_string())
        logger.success(f"Email sent successfully from {sender} to {receiver}")
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise
    finally:
        server.quit()
        logger.info("SMTP connection closed")

# Backward compatibility
def render_email_legacy(papers:list[ArxivPaper]):
    """Legacy function for backward compatibility."""
    return render_email(papers)
