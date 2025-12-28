# 🧬 PubMed Advanced MCP Server

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.0+-green.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![NCBI E-utilities](https://img.shields.io/badge/NCBI-E--utilities-orange.svg)](https://www.ncbi.nlm.nih.gov/books/NBK25501/)

**A comprehensive Model Context Protocol (MCP) server that exposes PubMed and PubMed Central research literature APIs as intelligent tools for LLM applications.**

Built with ❤️ by [Suyash Ekhande](https://www.linkedin.com/in/suyashekhande/)

[Features](#-features) • [Quick Start](#-quick-start) • [Tools](#-available-tools) • [Examples](#-usage-examples) • [Architecture](#-architecture) 

</div>



https://github.com/user-attachments/assets/892978f7-88d8-4b26-992e-41ba87c1b1cf



---

## 🌟 Features

- **16 Intelligent Tools** organized into 5 categories for comprehensive biomedical literature access
- **34M+ PubMed Articles** - Search across the world's largest biomedical abstract database
- **7M+ PMC Full-Text Articles** - Access complete article content from PubMed Central
- **Smart Rate Limiting** - Automatic compliance with NCBI rate limits (3-10 req/sec)
- **Cross-Database Linking** - Connect articles to genes, proteins, clinical variants, and more
- **ID Conversion** - Seamlessly convert between PMID, PMCID, DOI, and Manuscript IDs
- **BioC Format Support** - Pre-parsed text for NLP and text mining applications
- **Pipeline Operations** - Build complex multi-step queries using Entrez History Server
- **Batch Processing** - Efficiently handle 10K+ articles with chunked operations

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager

### Install from source

```bash
# Clone the repository
git clone https://github.com/yourusername/pubmed-advanced-mcp.git
cd pubmed-advanced-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

### Configure API Key (Recommended)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your NCBI API key
# Get one at: https://www.ncbi.nlm.nih.gov/account/
```

> **Note:** Without an API key, you're limited to 3 requests/second. With an API key, you get 10 requests/second.

## 🚀 Quick Start

### Run the MCP Server

```bash
# Using Python directly (Streamable HTTP on port 8000)
python -m src.server

# With custom host/port
MCP_HOST=127.0.0.1 MCP_PORT=9000 python -m src.server
```

> **Transport:** This server uses **Streamable HTTP** as the only transport protocol. It runs on `http://0.0.0.0:8000/mcp` by default.

### Run with Docker

```bash
# Build the image
docker build -t pubmed-mcp .

# Run the container
docker run -d -p 8000:8000 --name pubmed-mcp pubmed-mcp

# Run with NCBI API key for higher rate limits
docker run -d -p 8000:8000 -e NCBI_API_KEY=your-api-key pubmed-mcp
```


## 🛠 Available Tools

### Category 1: Search & Discovery (5 tools)

| Tool | Description | Example Use Case |
|------|-------------|------------------|
| `pubmed_search` | Search 34M+ PubMed abstracts | Find reviews on CAR-T therapy |
| `pmc_search` | Full-text search in PMC | Search methods sections for protocols |
| `mesh_term_search` | MeSH controlled vocabulary search | Find all cancer therapy articles |
| `advanced_search` | Multi-field Boolean queries | Complex author + topic + date searches |
| `global_search` | Cross-database hit counts | Discover data across NCBI |

### Category 2: Document Retrieval (4 tools)

| Tool | Description | Example Use Case |
|------|-------------|------------------|
| `fetch_article_summary` | Get article metadata | Retrieve author and abstract info |
| `fetch_full_article` | Get complete article content | Download full PMC articles |
| `fetch_bioc_article` | BioC format for NLP | Text mining and NER tasks |
| `batch_fetch_articles` | Bulk article retrieval | Download 1000+ articles efficiently |

### Category 3: Cross-Reference & Linking (3 tools)

| Tool | Description | Example Use Case |
|------|-------------|------------------|
| `find_related_articles` | Citation/similarity links | Build citation networks |
| `link_to_databases` | Cross-link to Gene, Protein, etc. | Find genes mentioned in articles |
| `find_citations_by_authors` | Author publication history | Track researcher output |

### Category 4: ID Conversion (2 tools)

| Tool | Description | Example Use Case |
|------|-------------|------------------|
| `convert_article_ids` | Batch ID conversion | Convert DOIs to PMIDs |
| `resolve_article_identifier` | Single ID resolution | Look up article by any ID type |

### Category 5: Advanced Operations (2 tools)

| Tool | Description | Example Use Case |
|------|-------------|------------------|
| `build_search_pipeline` | Multi-step query pipelines | Complex research workflows |
| `batch_process_articles` | Large-scale processing | Process 10K+ articles |

## 📖 Usage Examples

### Basic Search

```
User: Find recent reviews about CRISPR gene editing in cancer

AI uses: pubmed_search(
    query="CRISPR gene editing cancer",
    filters={"publication_types": ["Review"], "publication_date_start": "2023"},
    max_results=10
)
```

### MeSH-Based Search

```
User: Find all articles about breast cancer treatment using MeSH terms

AI uses: mesh_term_search(
    mesh_term="Breast Neoplasms",
    qualifiers=["therapy", "drug therapy"],
    explode=True,
    max_results=50
)
```

### Find Related Articles

```
User: What articles are similar to PMID 37000000?

AI uses: find_related_articles(
    pmid="37000000",
    relationship_type="similar",
    max_results=20
)
```

### Convert Article IDs

```
User: Convert these DOIs to PMIDs: 10.1038/nature12373, 10.1126/science.1225829

AI uses: convert_article_ids(
    ids=["10.1038/nature12373", "10.1126/science.1225829"],
    from_type="auto"
)
```

### Build a Research Pipeline

```
User: Find diabetes review articles that are linked to HLA genes

AI uses: build_search_pipeline(
    steps=[
        {"operation": "search", "database": "pubmed", 
         "parameters": {"query": "diabetes[mh] AND review[pt]"}},
        {"operation": "link", "database": "gene",
         "parameters": {"from_db": "pubmed"}}
    ]
)
```

### Batch Processing

```
User: Get metadata for these 500 PMIDs for my literature review

AI uses: batch_fetch_articles(
    pmids=["12345678", "23456789", ...],  # 500 IDs
    include_metadata=True,
    include_abstract=True,
    batch_size=100
)
```

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LLM / AI Agent Client                           │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                        MCP Protocol (Streamable HTTP)
                                     │
┌────────────────────────────────────▼────────────────────────────────────┐
│                    FastMCP Server (Python)                              │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    16 MCP Tools                                    │ │
│  │  Search │ Retrieval │ Linking │ ID Conversion │ Advanced Ops      │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
│                                   │                                      │
│  ┌────────────────────────────────▼───────────────────────────────────┐ │
│  │              API Clients (with Rate Limiting)                      │ │
│  │  E-Utilities │ BioC API │ ID Converter │ Session Manager           │ │
│  └────────────────────────────────┬───────────────────────────────────┘ │
└────────────────────────────────────┼────────────────────────────────────┘
                                     │
                        HTTP/REST API Calls
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
┌─────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ NCBI E-Utilities│      │ BioC APIs        │      │ ID Converter     │
│ (34M+ articles) │      │ (29M+ articles)  │      │ (200 IDs/batch)  │
└─────────────────┘      └──────────────────┘      └──────────────────┘
```

## 📁 Project Structure

```
pubmed-advanced-mcp/
├── src/
│   ├── __init__.py
│   ├── server.py                 # FastMCP server with all 16 tools
│   ├── config.py                 # Configuration management
│   │
│   ├── clients/                  # API client modules
│   │   ├── base.py              # Base HTTP client with rate limiting
│   │   ├── eutilities.py        # NCBI E-Utilities client
│   │   ├── bioc_api.py          # BioC text mining API
│   │   ├── id_converter.py      # PMC ID Converter
│   │   └── session_manager.py   # Entrez History management
│   │
│   ├── tools/                    # MCP Tool implementations
│   │   ├── search_tools.py      # 5 search tools
│   │   ├── retrieval_tools.py   # 4 retrieval tools
│   │   ├── linking_tools.py     # 3 linking tools
│   │   ├── id_conversion_tools.py # 2 ID tools
│   │   └── advanced_tools.py    # 2 advanced tools
│   │
│   ├── schemas/                  # Pydantic models
│   │   └── tool_schemas.py      # Input/output schemas
│   │
│   └── utils/                    # Utilities
│       ├── rate_limiter.py      # Token bucket rate limiter
│       ├── query_builder.py     # E-utilities query builder
│       └── error_handler.py     # Custom exceptions
│
├── docs/
│   ├── implementation/          # Implementation documentation
│   └── *.md                     # Original requirements
│
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NCBI_API_KEY` | NCBI API key for higher rate limits | None (3 req/sec) |
| `TOOL_NAME` | Tool identifier for NCBI | `pubmed-mcp-server` |
| `TOOL_EMAIL` | Contact email (required by NCBI) | `pubmed-mcp@example.com` |

### Rate Limits

| Scenario | Rate Limit |
|----------|------------|
| Without API Key | 3 requests/second |
| With API Key | 10 requests/second |
| Violation | IP blocked for 24+ hours |

## 🔬 Sample Prompts for LLMs

Here are example prompts you can use with Claude or other LLM clients:

### Literature Review
```
"Find all systematic reviews about COVID-19 vaccine efficacy published in 2023-2024. 
Include the abstracts and MeSH terms."
```

### Gene-Disease Research
```
"Search for articles about TP53 mutations in breast cancer. Then link these articles 
to related gene records in NCBI Gene database."
```

### Author Analysis
```
"Find all publications by Jennifer Doudna in the last 5 years and summarize 
her research focus areas."
```

### ID Conversion
```
"I have these DOIs from my reference manager. Convert them to PMIDs so I can 
search for related articles: 10.1038/nature12373, 10.1126/science.1225829"
```

### Text Mining Pipeline
```
"Get the full text of PMC7611378 in BioC format. I need it for named entity 
recognition to extract drug names and disease mentions."
```

## 🧪 Testing

### Run Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_search_tools.py
```

## 📚 API Documentation

### E-Utilities Query Syntax

The server supports full E-utilities query syntax:

```
# Basic search
cancer

# Field-specific search
cancer[ti]                    # Title
CRISPR[ab]                    # Abstract
"Zhang F"[au]                 # Author
Nature[ta]                    # Journal

# Boolean operators (MUST be uppercase)
cancer AND therapy
cancer OR tumor
cancer NOT lung

# Date ranges
cancer AND 2023[dp]           # Year
cancer AND 2020:2024[dp]      # Range

# MeSH terms
"Breast Neoplasms"[mh]        # MeSH heading
"Neoplasms/therapy"[mh]       # With qualifier

# Publication types
review[pt]
clinical trial[pt]
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Acknowledgments

- [NCBI](https://www.ncbi.nlm.nih.gov/) for providing the E-utilities and related APIs
- [FastMCP](https://github.com/jlowin/fastmcp) for the excellent MCP framework
- The biomedical research community for their contributions to PubMed

---

<div align="center">

Made with ❤️ for the biomedical research community

Built by [Suyash Ekhande](https://www.linkedin.com/in/suyashekhande/)

</div>
