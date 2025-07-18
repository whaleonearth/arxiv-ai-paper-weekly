<p align="center">
  <a href="" rel="noopener">
 <img width=200px height=200px src="assets/logo.svg" alt="logo"></a>
</p>

<h3 align="center">ArXiv Weekly Popular - Engagement-Based Discovery</h3>

<div align="center">

  [![Status](https://img.shields.io/badge/status-active-success.svg)]()
  [![GitHub Stars](https://img.shields.io/github/stars/whaleOnearth/arxiv-weekly-popular?style=flat)](https://github.com/whaleOnearth/arxiv-weekly-popular/stargazers)
  [![GitHub Issues](https://img.shields.io/github/issues/whaleOnearth/arxiv-weekly-popular)](https://github.com/whaleOnearth/arxiv-weekly-popular/issues)
  [![GitHub Pull Requests](https://img.shields.io/github/issues-pr/whaleOnearth/arxiv-weekly-popular)](https://github.com/whaleOnearth/arxiv-weekly-popular/pulls)
  [![License](https://img.shields.io/github/license/whaleOnearth/arxiv-weekly-popular)](/LICENSE)
  [![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
  [![API Strategy](https://img.shields.io/badge/API%20Strategy-3--Tier%20Pipeline-orange.svg)]()
  [![Performance](https://img.shields.io/badge/Performance-30s%20vs%201h+-green.svg)]()
  [![AI Powered](https://img.shields.io/badge/AI%20Powered-Local%20%26%20Cloud%20LLM-purple.svg)]()
  [![Free Operation](https://img.shields.io/badge/100%25%20FREE-Local%20Models-success.svg)]()

</div>

---

<p align="center"> 🚀 <strong>Next-Generation Research Discovery</strong> - Advanced AI system that finds trending papers using engagement analytics, code quality assessment, and personalized interest matching. <strong>30x faster than traditional approaches!</strong>
    <br> 
</p>

> [!NOTE]
> **Engagement-Based Discovery**: This system discovers papers using GitHub activity, citations, code quality, and community buzz. No app installation required - just fork and configure!

> [!TIP]
> **🆓 100% FREE Operation**: Download any local LLM model and run everything locally! No API costs, no data sharing, complete privacy. Auto-detects GGUF and HuggingFace models - just drop files in `models/` folder and set `USE_LOCAL_MODEL=1`.

> [!IMPORTANT]
> **⚡ Performance Breakthrough**: Our 3-tier API strategy delivers **30-second discovery vs 1+ hour** with traditional approaches. **Advanced ranking algorithm** processes ~300 papers → top 10-20 highly relevant results using **engagement metrics (50%) + interest matching (30%) + code quality (20%)**.

## 🧐 About <a name = "about"></a>

> Find trending research papers that matter - papers with active code implementations, high GitHub engagement, and growing community interest!

**ArXiv Weekly Popular** discovers papers using multiple engagement signals:
- **GitHub Activity**: Stars, forks, and code quality metrics
- **Citation Velocity**: How quickly papers are being cited
- **Code Availability**: Papers with working implementations
- **Community Buzz**: Social mentions and discussions
- **Your Interests**: Personalized matching based on research areas and keywords

## 🏗️ How It Works

> **🚀 Sophisticated 3-Tier Discovery Pipeline** - From raw paper discovery to intelligent ranking

```mermaid
flowchart TD
    A["📅 Past Few Days<br/>(default: 7 days)"] --> B["🔍 Multi-Source Discovery"]
    
    B --> C["🚀 arXiv API<br/>(Recent Papers)"]
    B --> D["🎓 Semantic Scholar<br/>(High-Impact Papers)"]
    B --> E["📈 GitHub Trending<br/>(Trending Repos)"]
    
    C --> F["📝 All Discovered Papers<br/>(~150-300 papers)"]
    D --> F
    E --> F
    
    F --> G["🔄 Deduplication<br/>(Remove duplicates by arXiv ID & title)"]
    
    G --> H["🎯 Interest Filtering<br/>(Match against user interests)"]
    
    H --> I["🔗 Enrichment Layer<br/>(Papers with Code - GitHub repos)"]
    
    I --> J["📊 Engagement Filtering<br/>(min_engagement_score > 10.0)"]
    
    J --> K["🏆 Final Ranking Formula"]
    
    K --> L["📧 Top Papers<br/>(50-100 papers)"]
    
    K1["⚡ Engagement Score<br/>(50% weight)<br/>• GitHub stars/forks<br/>• Citations & velocity<br/>• Social mentions<br/>• Recency bonus"] --> K
    K2["🎯 Interest Match<br/>(30% weight)<br/>• Research areas<br/>• arXiv categories<br/>• Keywords"] --> K
    K3["💻 Code Quality<br/>(20% weight)<br/>• Documentation<br/>• Tests & examples<br/>• License<br/>• Recent commits"] --> K
    
    style A fill:#e1f5fe
    style K fill:#fff3e0
    style L fill:#e8f5e8
    style K1 fill:#ffebee
    style K2 fill:#f3e5f5
    style K3 fill:#e0f2f1
```

### 🎯 **What Makes This Special?**

**📊 Advanced Ranking Algorithm**: Unlike simple keyword searches, this system uses a **weighted scoring formula** that combines:
- **Engagement Metrics (50%)**: GitHub activity, citation velocity, social buzz
- **Interest Matching (30%)**: Relevance to your research areas and keywords  
- **Code Quality (20%)**: Documentation, tests, licensing, and maintenance

**🚀 Lightning-Fast Performance**: Our **three-tier API strategy** delivers results in **30 seconds vs 1+ hours** with traditional approaches:
- **Primary Sources**: arXiv API + Semantic Scholar for reliable, fast discovery
- **Enrichment Layer**: Papers with Code adds GitHub repository data
- **Smart Filtering**: Only process papers that match your interests

**🎯 Precision Targeting**: From **~300 raw papers** down to **top 10-20 highly relevant papers** through intelligent filtering and ranking

### 🆚 **Why Choose This Over Alternatives?**

| Feature | **ArXiv Weekly Popular** | Traditional RSS/Alerts | Basic arXiv Scrapers |
|---------|--------------------------|-------------------------|---------------------|
| **Discovery Speed** | 🚀 **30 seconds** | ⏰ Manual browsing | 🐌 1+ hours |
| **Intelligence** | 🧠 **AI-powered ranking** | 📝 Keyword matching | 🔍 Simple search |
| **Code Focus** | 💻 **GitHub integration** | ❌ No code info | ❌ No implementation details |
| **Personalization** | 🎯 **Multi-factor scoring** | 📧 Basic filtering | ❌ No personalization |
| **Quality Assessment** | ⭐ **Engagement metrics** | ❌ No quality signals | ❌ Chronological only |
| **Cost** | 💰 **100% FREE** | 💸 Often paid | 💸 Server costs |

## ✨ Key Features

###  **Engagement-Based Discovery** 
- **Multi-Signal Trending**: Combines GitHub stars, citations, social buzz, and code quality
- **Real-Time Analysis**: Live GitHub API integration for up-to-date metrics
- **Code-First Approach**: Prioritizes papers with quality implementations

###  **Personalized Recommendations**
- **Dynamic Keywords**: Set research interests directly in GitHub Actions
- **Smart Matching**: Papers ranked by relevance to your specific interests
- **Flexible Configuration**: Easy updates without file editing

###  **AI-Powered Summaries (100% FREE)**
- **Local Models**: Download any LLM and run completely offline - no API costs!
- **Privacy First**: Your data never leaves your computer
- **Auto-Detection**: Supports GGUF and HuggingFace models - just drop and go
- **Cloud Option**: Optional OpenAI/Anthropic APIs for premium quality
- **Intelligent TL;DR**: Context-aware summaries explaining why papers are trending

###  **Rich Email Reports**
- **Trending Badges**: Visual indicators of why papers are popular
- **Engagement Metrics**: GitHub stats, citations, and code quality scores
- **Multiple Code Links**: Primary repository plus additional implementations
- **Interest Matching**: See exactly which of your interests each paper matches

## 📷 Email Preview

![Email Screenshot](./assets/screenshot.png)

*Rich email format shows engagement metrics, trending reasons, AI summaries, and code quality scores*

## 🚀 Quick Start

### 1. Create Your Repository

**Option A: Use This Template**
1. Click **"Use this template"** button above
2. Name your repository (e.g., `arxiv-weekly-popular`)
3. Make it public or private as preferred

**Option B: Fork and Customize**
1. Fork this repository to your GitHub account
2. Rename it in Settings if desired
3. Update the README badges with your username/repo name

> [!IMPORTANT]
> ** Want 100% FREE operation?** Just set up email settings below, then add a local model to `models/` folder and set `USE_LOCAL_MODEL=1`. No API costs, complete privacy!

### 2. Complete Configuration Guide

#### Required Setup Locations

**Secrets:** Go to **Settings** → **Secrets and variables** → **Actions** → **Secrets**

![Secrets Configuration](./assets/secrets.png)

**Variables:** Go to **Settings** → **Secrets and variables** → **Actions** → **Variables**

![Repository Variables](./assets/repo_var.png)

#### Complete Configuration Table

**🔐 SECRETS** (Settings → Secrets and variables → Actions → Secrets)

| Configuration | Required | Description | Example/Default |
|---------------|----------|-------------|-----------------|
| **EMAIL SETTINGS** |
| `SMTP_SERVER` | ✅ | Your email provider's SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | ✅ | SMTP port (investigate your email port) | `465` |
| `SENDER` | ✅ | Email address to send from | `your.email@gmail.com` |
| `SENDER_PASSWORD` | ✅ | Email password or app password | `your_app_password` |
| `RECEIVER` | ✅ | Email address to receive reports | `your.email@gmail.com` |
| **AI SUMMARIZATION** |
| `USE_LOCAL_MODEL` | ⚠️ | **Auto-detect local models (1=yes, 0=no)** | `0` |
| `USE_LLM_API` | ⚠️ | Use cloud API for summaries (1=yes, 0=no) | `0` |
| `OPENAI_API_KEY` | ⚠️ | OpenAI API key for cloud summaries | `sk-xxxxxxxxxxxx` |
| `OPENAI_API_BASE` | ⚠️ | OpenAI API endpoint (for custom endpoints) | `https://api.openai.com/v1` |
| `MODEL_NAME` | ⚠️ | LLM model name for cloud summaries | `gpt-4o` |
| **DISCOVERY SETTINGS** |
| `MAX_PAPER_NUM` | ⚠️ | Maximum papers per email | `50` |
| `GH_TOKEN` | ⚠️ | GitHub Personal Access Token (better API limits) | `ghp_xxxxxxxxxxxx` |

**📋 VARIABLES** (Settings → Secrets and variables → Actions → Variables)

| Configuration | Required | Description | Example/Default |
|---------------|----------|-------------|-----------------|
| **RESEARCH INTERESTS** |
| `RESEARCH_AREAS` | ⚠️ | Default research areas (comma-separated) | `machine learning,computer vision,natural language processing` |
| `CATEGORIES` | ⚠️ | Default arXiv categories (comma-separated) | `cs.LG,cs.CV,cs.CL,cs.AI` |
| `KEYWORDS` | ⚠️ | Default keywords (comma-separated) | `neural networks,deep learning,transformers` |
| **SYSTEM SETTINGS** |
| `DAYS_BACK` | ⚠️ | Days to look back for trending papers | `7` |
| `LANGUAGE` | ⚠️ | Language for AI summaries | `English` |

**Legend:**
- ✅ **Required**: Must be set for basic functionality
- ⚠️ **Optional**: Enhances functionality or provides defaults

### 3. Configure Your Research Interests

**Recommended: Use GitHub Actions Interface**
1. Go to **Actions** tab in your repository
2. Click **"Test workflow"** 
3. Click **"Run workflow"** and fill in your interests:

   ![GitHub Actions Interface](./assets/test.png)

   Example inputs:
   ```yaml
   Research Areas: machine learning, computer vision, robotics
   Categories: cs.LG, cs.CV, cs.AI, cs.RO  
   Keywords: neural networks, transformers, diffusion models
   Max Papers: 5
   ```

**Alternative: Edit Configuration File**
1. Edit `config/user_interests.yml` in your repository
2. Add your research areas, categories, and keywords
3. Commit the changes



### 4. Test Your Setup

1. Go to **Actions** → **"Test workflow"**
2. Click **"Run workflow"** 
3. Customize your interests for this test run
4. Check the workflow logs and your email!

   ![Test Results](./assets/test.png)

### 5. Enable Daily Reports

The system automatically runs daily at 22:00 UTC. You can:
- Modify the schedule in `.github/workflows/main.yml`
- Run manually anytime using **"Send emails daily"** workflow
- Customize interests for each run using the workflow interface

## 🔧 Advanced Features

### GitHub Actions Parameters

When running workflows manually, you can override your default interests:

```yaml
Research Areas: "machine learning, computer vision, robotics"
Categories: "cs.LG, cs.CV, cs.RO, cs.AI"  
Keywords: "neural networks, transformers, diffusion models, SLAM"
Max Papers: 20
Days Back: 5
```

### AI Summary Configuration

**🤖 Local Models (Privacy & Cost-Free)**
```bash
# 1. Download a model to the models/ directory
mkdir models
cd models
wget https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf

# 2. Enable local model mode
USE_LOCAL_MODEL=1
```

💰 **Cost Comparison**: OpenAI GPT-4o costs ~$0.10-0.30 per email (5-15 papers) vs **$0.00 with local models**

**☁️ Cloud API (Premium Quality)**
```bash
# Use cloud APIs for higher quality summaries (costs ~$0.10-0.30 per email)
USE_LLM_API=1
OPENAI_API_KEY=sk-your-api-key
OPENAI_API_BASE=https://api.openai.com/v1  # Optional: custom endpoint
MODEL_NAME=gpt-4o  # Optional: specific model
```

**🔄 Configuration Priority**
1. **USE_LOCAL_MODEL=1**: Auto-detect local models → Fallback to API if none found
2. **USE_LLM_API=1**: Use cloud API (OpenAI, Anthropic, etc.)  
3. **Default**: Use built-in Qwen model (downloads automatically)

**📁 Supported Local Models**
- **GGUF Models**: Fast, low memory (recommended)
- **HuggingFace Models**: Full compatibility with transformers library
- **Auto-Detection**: Just drop files in `models/` folder

See `models/README.md` for detailed local model setup instructions.

### Discovery Sources

The system uses a **three-tier discovery strategy** for optimal performance:

**🚀 Primary Sources (Fast & Reliable)**
- **arXiv API**: Recent papers from arXiv with 1-3 second response times
- **Semantic Scholar**: High-impact papers with citation and influence metrics

**🔗 Enrichment Layer**
- **Papers with Code**: Adds GitHub repository links and code implementation data to discovered papers

**📈 Supplementary Sources**
- **GitHub Trending**: Trending ML repositories linked to papers

### Engagement Scoring

Papers are ranked using:
- **Engagement Metrics (50%)**: GitHub activity, citations, social buzz
- **Interest Matching (30%)**: Relevance to your research areas and keywords
- **Code Quality (20%)**: Documentation, tests, examples, license

## 📈 How It Works

1. **Discovery**: Scans Papers with Code and GitHub trending repositories
2. **Analysis**: Extracts engagement metrics, paper references, and code quality
3. **Matching**: Scores papers against your research interests
4. **Ranking**: Combines engagement, relevance, and code quality scores
5. **Summarization**: Generates AI summaries for top papers
6. **Delivery**: Sends beautifully formatted email with rich metadata

## 🎯 Email Content

Your daily email includes:

### 📊 **Paper Overview**
- Trending score with star rating
- Why the paper is trending (badges)
- Engagement metrics (GitHub stars, forks, citations)
- Code quality assessment

### 🤖 **AI-Generated Summary**
- Concise TL;DR of key contributions
- Practical implications and applications
- Why it's relevant to your interests

### 💻 **Code & Resources**
- Primary repository with quality score
- Additional implementations
- PDF and arXiv links
- Documentation and example availability

### 🎯 **Personalization**
- Interest matching indicators
- Relevance to your research areas
- Customized paper selection

## 🔧 Local Development

```bash
# Clone the repository
git clone https://github.com/whaleOnearth/arxiv-weekly-popular.git
cd arxiv-weekly-popular

# Install dependencies
uv sync

# Optional: Install transformers for advanced local models
uv pip install transformers torch accelerate

# Set environment variables
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT="587"
export SENDER="your.email@gmail.com"
export SENDER_PASSWORD="your_password"
export RECEIVER="your.email@gmail.com"

# Run discovery
uv run main.py

# Run with debug mode
uv run main.py --debug

# Run dry-run (no email sent)
uv run main.py --dry-run

# Use local model (place model files in models/ directory)
export USE_LOCAL_MODEL=1
uv run main.py
```

## 🛠️ Troubleshooting

### Common Issues

**Q: No papers found**
- Check your research interests are not too narrow
- Verify Papers with Code and GitHub APIs are accessible
- Try increasing `DAYS_BACK` parameter

**Q: Email not received**
- Verify SMTP settings and credentials
- Check spam/junk folder
- Test with "Test workflow" first

**Q: AI summaries not generated**
- Ensure `OPENAI_API_KEY` is set (or uses local LLM)
- Check API quota and billing
- Verify model name is correct

**Q: Low-quality results**
- Add more specific keywords to your interests
- Adjust `min_engagement_score` in configuration
- Consider narrowing research areas

### Email Configuration Examples

**Gmail:**
```
SMTP_SERVER: smtp.gmail.com
SMTP_PORT: 587
SENDER_PASSWORD: (use App Password, not account password)
```

**Outlook:**
```
SMTP_SERVER: smtp-mail.outlook.com  
SMTP_PORT: 587
```

**Other providers:** Check your email provider's SMTP settings

## 🏗️ Architecture

```mermaid
graph TD
    A[User Interests] --> B[Paper Discovery Service]
    C[Papers with Code API] --> B
    D[GitHub Trending API] --> B
    
    B --> E[Interest Matcher]
    B --> F[Deduplicator] 
    B --> G[Engagement Filter]
    
    E --> H[Ranked Papers]
    F --> H
    G --> H
    
    H --> I[AI Summarization]
    I --> J[Enhanced Email Report]
    
    K[GitHub Actions] --> L[Dynamic Configuration]
    L --> A
```

## 🗺️ Roadmap

### 🎯 **Next Release (v0.5.0)**
- [ ] **GitHub Pages Website**: Daily-updated web dashboard instead of email-only
- [ ] **One-Click Setup**: Template repository with pre-configured workflows
- [ ] **Mobile-Responsive**: Better email templates and web interface
- [ ] **Research Templates**: Pre-configured interest profiles (ML, CV, NLP, Robotics)

### 🚀 **Upcoming Features** 
- [ ] **Web Configuration**: GUI for research interests (no more GitHub settings)
- [ ] **Multi-Channel Notifications**: Slack, Discord, Teams integration
- [ ] **Paper Bookmarking**: Save and organize favorite papers
- [ ] **Historical Archive**: Browse past discoveries and research trends
- [ ] **RSS/JSON Feeds**: Machine-readable outputs for other tools

### 💡 **Future Vision**
- [ ] **Collaborative Research**: Team accounts with shared interests  
- [ ] **Integration Hub**: Zotero, Notion, Obsidian connectors
- [ ] **Research Analytics**: Personal insights and field trend analysis
- [ ] **Progressive Web App**: Offline access and mobile experience

*Want to contribute? Pick a feature and let's build the future of research discovery together!*

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Areas for contribution:**
- Additional discovery sources (Semantic Scholar, arXiv direct)
- Enhanced AI summarization techniques
- Better engagement metric algorithms
- UI improvements for configuration
- Mobile-friendly email templates

## 📃 License

Distributed under the AGPLv3 License. See `LICENSE` for details.

## 🙏 Acknowledgements

- **Papers with Code** for providing excellent API access to academic papers
- **GitHub** for trending repository data and free Actions
- **OpenAI** for AI summarization capabilities
- **Research Community** for inspiration and feedback
- **Contributors** who helped build this engagement-based system

---

<div align="center">

**🌟 Star this repository if you find it useful!**

*Built with ❤️ for the research community*

</div>
