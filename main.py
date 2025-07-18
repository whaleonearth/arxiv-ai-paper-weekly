"""ArXiv Weekly Popular - Engagement-Based Paper Discovery System.

This is the new main entry point that uses engagement-based paper discovery
instead of the old Zotero library similarity approach. It discovers trending
papers from multiple sources and sends personalized email reports.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from loguru import logger
from src.core.config import load_user_interests
from src.services.paper_discovery import create_discovery_service
from src.data.paper_models import TrendingPaper
from construct_email import render_email, send_email
from llm import set_global_llm


def setup_logging(debug: bool = False) -> None:
    """Set up logging configuration.
    
    Args:
        debug: Whether to enable debug logging
    """
    logger.remove()
    level = "DEBUG" if debug else "INFO"
    logger.add(sys.stdout, level=level)
    
    if debug:
        logger.debug("Debug mode enabled")


def load_configuration() -> tuple[dict, dict]:
    """Load configuration from environment variables and config files.
    
    Returns:
        Tuple of (environment config, user interests config)
    """
    # Required environment variables
    required_env_vars = [
        "SMTP_SERVER", "SMTP_PORT", "SENDER", "SENDER_PASSWORD", "RECEIVER"
    ]
    
    env_config = {}
    missing_vars = []
    
    # Load required variables
    for var in required_env_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        env_config[var] = value
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    # Load optional variables with defaults
    env_config.update({
        "MAX_PAPER_NUM": int(os.getenv("MAX_PAPER_NUM", "50")),
        "SEND_EMPTY": os.getenv("SEND_EMPTY", "false").lower() == "true",
        "DAYS_BACK": int(os.getenv("DAYS_BACK", "7")),
        "GITHUB_TOKEN": os.getenv("GH_TOKEN"),
        "USE_LOCAL_MODEL": os.getenv("USE_LOCAL_MODEL", "false").lower() == "true",
        "USE_LLM_API": os.getenv("USE_LLM_API", "false").lower() == "true",
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "OPENAI_API_BASE": os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
        "MODEL_NAME": os.getenv("MODEL_NAME", "gpt-4o"),
        "LANGUAGE": os.getenv("LANGUAGE", "English"),
    })
    
    # Validate SMTP port
    try:
        smtp_port = int(env_config["SMTP_PORT"])
        if not (1 <= smtp_port <= 65535):
            raise ValueError(f"SMTP_PORT must be between 1 and 65535, got {smtp_port}")
        env_config["SMTP_PORT"] = smtp_port
    except ValueError as e:
        raise ValueError(f"Invalid SMTP_PORT: {e}")
    
    # Load user interests configuration
    try:
        user_interests = load_user_interests()
        logger.info(f"Loaded user interests: {len(user_interests.research_areas)} areas, "
                   f"{len(user_interests.categories)} categories, {len(user_interests.keywords)} keywords")
    except Exception as e:
        logger.error(f"Failed to load user interests configuration: {e}")
        raise
    
    return env_config, user_interests


def setup_llm(env_config: dict) -> None:
    """Set up the LLM for paper summarization.
    
    Args:
        env_config: Environment configuration
    """
    if env_config["USE_LOCAL_MODEL"]:
        logger.info("Local model mode enabled - auto-detecting models...")
        try:
            set_global_llm(
                api_key=env_config["OPENAI_API_KEY"],  # Fallback if no local model
                base_url=env_config["OPENAI_API_BASE"],
                model=env_config["MODEL_NAME"],
                lang=env_config["LANGUAGE"],
                use_local_model=True
            )
        except ValueError as e:
            logger.error(f"Local model setup failed: {e}")
            if not env_config["OPENAI_API_KEY"]:
                logger.error("No local model found and no API key provided")
                raise ValueError("Cannot initialize LLM: no local model found and no API key provided")
            raise
            
    elif env_config["USE_LLM_API"]:
        if not env_config["OPENAI_API_KEY"]:
            raise ValueError("OPENAI_API_KEY required when USE_LLM_API is true")
        
        logger.info("Using cloud LLM API for paper summarization")
        set_global_llm(
            api_key=env_config["OPENAI_API_KEY"],
            base_url=env_config["OPENAI_API_BASE"],
            model=env_config["MODEL_NAME"],
            lang=env_config["LANGUAGE"]
        )
    else:
        logger.info("Using default local LLM for paper summarization")
        set_global_llm(lang=env_config["LANGUAGE"])


def discover_trending_papers(env_config: dict, user_interests) -> List[TrendingPaper]:
    """Discover trending papers using the engagement-based system.
    
    Args:
        env_config: Environment configuration
        user_interests: User's research interests
        
    Returns:
        List of trending papers sorted by relevance
    """
    logger.info("Starting engagement-based paper discovery...")
    
    # Create discovery service
    discovery_service = create_discovery_service(
        user_interests=user_interests,
        github_token=env_config["GITHUB_TOKEN"],
        days_back=env_config["DAYS_BACK"],
        max_papers=env_config["MAX_PAPER_NUM"]
    )
    
    # Discover papers
    try:
        result = discovery_service.discover_papers()
        
        # Log discovery summary
        summary = discovery_service.get_discovery_summary(result)
        logger.info("Discovery completed successfully")
        logger.debug(f"Discovery summary:\n{summary}")
        
        if result.errors:
            logger.warning(f"Discovery completed with {len(result.errors)} errors:")
            for error in result.errors:
                logger.warning(f"  - {error}")
        
        return result.papers
        
    except Exception as e:
        logger.error(f"Paper discovery failed: {e}")
        raise


def generate_paper_summaries(papers: List[TrendingPaper], max_summaries: int = 5, env_config: dict = None) -> None:
    """Generate AI summaries for top papers that don't have them.
    
    Args:
        papers: List of papers to process (should be sorted by relevance)
        max_summaries: Maximum number of papers to generate summaries for
        env_config: Environment configuration (unused, kept for compatibility)
    """
    if not papers:
        return
        
    logger.info(f"Generating AI summaries for top {max_summaries} papers...")
    
    # Get top papers that need summaries
    papers_needing_summaries = [p for p in papers[:max_summaries] if not p.tldr_summary]
    
    if not papers_needing_summaries:
        logger.info("Top papers already have summaries")
        return
    
    logger.info(f"Generating summaries for {len(papers_needing_summaries)} top papers...")
    
    try:
        from llm import GLOBAL_LLM
        
        if GLOBAL_LLM is None:
            logger.warning("LLM not initialized. Skipping summary generation.")
            return
        
        for i, paper in enumerate(papers_needing_summaries, 1):
            try:
                logger.info(f"Generating summary {i}/{len(papers_needing_summaries)}: {paper.title[:60]}...")
                
                # Prepare prompt for LLM
                prompt_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are an AI research assistant. Generate a concise, informative TL;DR "
                            "summary of the given research paper. Focus on key contributions, methods, "
                            "and practical implications. Keep it under 150 words and accessible to "
                            "both technical and non-technical readers."
                        )
                    },
                    {
                        "role": "user", 
                        "content": (
                            f"Paper Title: {paper.title}\n\n"
                            f"Abstract: {paper.abstract}\n\n"
                            f"Authors: {', '.join(paper.authors) if paper.authors else 'Not specified'}\n\n"
                            f"Categories: {', '.join(paper.categories) if paper.categories else 'Not specified'}\n\n"
                            f"Why it's trending: {', '.join([r.value for r in paper.trending_reasons]) if paper.trending_reasons else 'High engagement metrics'}\n\n"
                            f"Code availability: {'Yes' if paper.primary_repository else 'No'}"
                            f"{f' ({paper.primary_repository.url})' if paper.primary_repository else ''}\n\n"
                            "Please provide a TL;DR summary:"
                        )
                    }
                ]
                
                # Generate summary
                summary = GLOBAL_LLM.generate(prompt_messages)
                
                if summary and len(summary.strip()) > 10:
                    paper.tldr_summary = summary.strip()
                    logger.success(f"Generated summary for: {paper.title[:60]}...")
                else:
                    logger.warning(f"Generated empty summary for: {paper.title[:60]}...")
                    
            except Exception as e:
                logger.error(f"Failed to generate summary for paper {i}: {e}")
                continue
                
        successful_summaries = len([p for p in papers_needing_summaries if p.tldr_summary])
        logger.success(f"Successfully generated {successful_summaries}/{len(papers_needing_summaries)} summaries")
        
    except ImportError:
        logger.error("LLM module not available. Cannot generate summaries.")
    except Exception as e:
        logger.error(f"Error in summary generation: {e}")


def send_email_report(papers: List[TrendingPaper], env_config: dict) -> None:
    """Send email report with discovered papers.
    
    Args:
        papers: List of papers to include in report
        env_config: Environment configuration
    """
    if not papers and not env_config["SEND_EMPTY"]:
        logger.info("No papers found and SEND_EMPTY is false. Skipping email.")
        return
    
    logger.info(f"Preparing email report with {len(papers)} papers...")
    
    try:
        # Generate HTML email content
        html_content = render_email(papers)
        
        # Send email
        send_email(
            sender=env_config["SENDER"],
            receiver=env_config["RECEIVER"],
            password=env_config["SENDER_PASSWORD"],
            smtp_server=env_config["SMTP_SERVER"],
            smtp_port=env_config["SMTP_PORT"],
            html_content=html_content
        )
        
        logger.success("Email sent successfully!")
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise


def main() -> None:
    """Main entry point for the ArXiv Weekly Popular system."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Discover and email trending AI/ML papers based on engagement metrics"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run discovery but don't send email"
    )
    parser.add_argument(
        "--config-path",
        type=str,
        help="Path to user interests configuration file"
    )
    
    args = parser.parse_args()
    
    try:
        # Set up logging
        setup_logging(debug=args.debug)
        logger.info("Starting ArXiv Weekly Popular - Engagement-Based Discovery")
        
        # Load configuration
        logger.info("Loading configuration...")
        env_config, user_interests = load_configuration()
        
        # Set up LLM if papers need summarization
        if env_config["USE_LLM_API"] or True:  # Always set up for potential use
            setup_llm(env_config)
        
        # Discover trending papers
        papers = discover_trending_papers(env_config, user_interests)
        
        if not papers:
            logger.info("No trending papers found matching your interests")
            if env_config["SEND_EMPTY"]:
                logger.info("Sending empty report as requested")
                send_email_report([], env_config)
            return
        
        logger.success(f"Found {len(papers)} trending papers!")
        
        # Log top papers
        logger.info("Top trending papers:")
        for i, paper in enumerate(papers[:5], 1):
            score = paper.trending_score
            sources = ", ".join(paper.trending_reasons) if paper.trending_reasons else "general"
            logger.info(f"  {i}. {paper.title} (score: {score:.1f}, reasons: {sources})")
        
        # Generate AI summaries for top papers
        top_paper_count = min(5, len(papers))  # Summarize top 5 papers
        generate_paper_summaries(papers, max_summaries=top_paper_count, env_config=env_config)
        
        # Send email report
        if not args.dry_run:
            send_email_report(papers, env_config)
        else:
            logger.info("Dry run mode: Email not sent")
            
        logger.success("ArXiv Weekly Popular completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        if args.debug:
            logger.exception("Full error traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main() 