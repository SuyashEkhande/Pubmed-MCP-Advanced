"""MCP Tool modules for PubMed MCP Server."""

from .search_tools import (
    pubmed_search,
    pmc_search,
    mesh_term_search,
    advanced_search,
    global_search,
)
from .retrieval_tools import (
    fetch_article_summary,
    fetch_full_article,
    fetch_bioc_article,
    batch_fetch_articles,
)
from .linking_tools import (
    find_related_articles,
    link_to_databases,
    find_citations_by_authors,
)
from .id_conversion_tools import (
    convert_article_ids,
    resolve_article_identifier,
)
from .advanced_tools import (
    build_search_pipeline,
    batch_process_articles,
)

__all__ = [
    # Search tools
    "pubmed_search",
    "pmc_search",
    "mesh_term_search",
    "advanced_search",
    "global_search",
    # Retrieval tools
    "fetch_article_summary",
    "fetch_full_article",
    "fetch_bioc_article",
    "batch_fetch_articles",
    # Linking tools
    "find_related_articles",
    "link_to_databases",
    "find_citations_by_authors",
    # ID conversion tools
    "convert_article_ids",
    "resolve_article_identifier",
    # Advanced tools
    "build_search_pipeline",
    "batch_process_articles",
]
