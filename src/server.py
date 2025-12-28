"""
PubMed Advanced MCP Server

A FastMCP-based server exposing comprehensive PubMed/PMC research literature
APIs as 16 intelligent tools for LLM applications.

Run with: python -m src.server
Or: fastmcp run src/server.py
"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP(
    name="PubMed Advanced MCP Server",
    instructions="""
    This MCP server provides comprehensive access to PubMed and PubMed Central (PMC) 
    biomedical literature databases. It offers 16 tools organized into 5 categories:

    1. **Search & Discovery** (5 tools): Find articles using keywords, MeSH terms, 
       Boolean queries, or cross-database searches.
    
    2. **Document Retrieval** (4 tools): Fetch article metadata, full text, 
       and text-mining-ready BioC format.
    
    3. **Cross-Reference & Linking** (3 tools): Discover citations, similar articles, 
       and links to genes, proteins, and other NCBI databases.
    
    4. **ID Conversion** (2 tools): Convert between PMID, PMCID, DOI, and Manuscript IDs.
    
    5. **Advanced Operations** (2 tools): Build multi-step query pipelines and 
       process large article sets.

    Use natural language queries or structured E-utilities syntax. The server 
    handles rate limiting (3 req/sec without API key, 10 with key) automatically.
    """
)


# =============================================================================
# Search & Discovery Tools (5)
# =============================================================================

@mcp.tool()
async def pubmed_search(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    sort_by: str = "relevance",
    max_results: int = 50,
    include_abstract: bool = True,
    use_history: bool = False
) -> Dict[str, Any]:
    """
    Search PubMed for biomedical literature.
    
    Searches 34M+ PubMed abstracts using natural language or E-utilities syntax.
    Returns publication metadata including titles, abstracts, authors, and MeSH terms.
    
    Args:
        query: Search query (e.g., "CRISPR gene therapy", "cancer AND 2023[dp]")
        filters: Optional filters:
            - publication_date_start/end: Date range (YYYY or YYYY-MM-DD)
            - publication_types: ["Review", "Clinical Trial", etc.]
            - language: "eng", "spa", etc.
            - free_full_text_only: Limit to free articles
        sort_by: "relevance", "pub_date", or "first_author"
        max_results: Number of results (1-10000)
        include_abstract: Include abstracts in results
        use_history: Store for pipeline chaining
        
    Examples:
        - "Find reviews on CAR-T therapy from 2020-2025"
        - "Search for meta-analyses on COVID-19 vaccines"
        - "diabetes AND clinical trial AND free full text"
    """
    from .tools.search_tools import pubmed_search as _pubmed_search
    return await _pubmed_search(
        query=query,
        filters=filters,
        sort_by=sort_by,
        max_results=max_results,
        include_abstract=include_abstract,
        use_history=use_history
    )


@mcp.tool()
async def pmc_search(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    has_full_text: bool = True,
    max_results: int = 50,
    use_history: bool = False
) -> Dict[str, Any]:
    """
    Search PMC for full-text articles.
    
    Searches 7M+ full-text articles in PubMed Central. Unlike PubMed (abstracts only),
    PMC searches the complete article text.
    
    Args:
        query: Search query
        filters: Optional filters (same as pubmed_search)
        has_full_text: Limit to articles with full text (default True)
        max_results: Number of results
        use_history: Store for pipeline chaining
    """
    from .tools.search_tools import pmc_search as _pmc_search
    return await _pmc_search(
        query=query,
        filters=filters,
        has_full_text=has_full_text,
        max_results=max_results,
        use_history=use_history
    )


@mcp.tool()
async def mesh_term_search(
    mesh_term: str,
    qualifiers: Optional[List[str]] = None,
    search_mode: str = "descendant",
    explode: bool = True,
    date_range_start: Optional[str] = None,
    date_range_end: Optional[str] = None,
    max_results: int = 50
) -> Dict[str, Any]:
    """
    Search using MeSH controlled vocabulary terms.
    
    MeSH (Medical Subject Headings) provides standardized, hierarchical indexing.
    Using MeSH ensures consistent retrieval across different terminologies.
    
    Args:
        mesh_term: MeSH descriptor (e.g., "Neoplasms", "Diabetes Mellitus")
        qualifiers: Subheadings (e.g., ["therapy", "prevention", "genetics"])
        search_mode: "exact" or "descendant" (include hierarchy)
        explode: Include all subtree terms (default True)
        date_range_start/end: Date filters
        max_results: Number of results
        
    Examples:
        - mesh_term="Breast Neoplasms", qualifiers=["therapy"]
        - mesh_term="Alzheimer Disease", explode=True
    """
    from .tools.search_tools import mesh_term_search as _mesh_term_search
    return await _mesh_term_search(
        mesh_term=mesh_term,
        qualifiers=qualifiers,
        search_mode=search_mode,
        explode=explode,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        max_results=max_results
    )


@mcp.tool()
async def advanced_search(
    query_builder: List[Dict[str, str]],
    date_range_start: Optional[str] = None,
    date_range_end: Optional[str] = None,
    date_field: str = "publication_date",
    max_results: int = 50
) -> Dict[str, Any]:
    """
    Build complex Boolean queries with field-specific search.
    
    Provides precise control over search logic with multiple terms,
    fields, and Boolean operators.
    
    Args:
        query_builder: List of search terms, each with:
            - field: "title", "abstract", "author", "journal", "all_fields", "mesh"
            - term: The search term
            - operator: "AND", "OR", "NOT"
        date_range_start/end: Date filters
        date_field: "publication_date" or "entry_date"
        max_results: Number of results
        
    Example:
        query_builder=[
            {"field": "title", "term": "CRISPR", "operator": "AND"},
            {"field": "mesh", "term": "Gene Therapy", "operator": "AND"},
            {"field": "author", "term": "Zhang F", "operator": "AND"}
        ]
    """
    from .tools.search_tools import advanced_search as _advanced_search
    return await _advanced_search(
        query_builder=query_builder,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        date_field=date_field,
        max_results=max_results
    )


@mcp.tool()
async def global_search(
    query: str,
    databases: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Search across all NCBI databases to find data availability.
    
    Returns hit counts for 38+ NCBI databases, helping identify
    which databases have relevant data for your query.
    
    Args:
        query: Search query
        databases: Specific databases to check (all if empty)
        
    Databases include: pubmed, pmc, gene, protein, structure, 
    clinvar, snp, biosystems, pubchem, and many more.
    """
    from .tools.search_tools import global_search as _global_search
    return await _global_search(query=query, databases=databases)


# =============================================================================
# Document Retrieval Tools (4)
# =============================================================================

@mcp.tool()
async def fetch_article_summary(
    pmid: str,
    database: str = "pubmed",
    include_full_metadata: bool = True
) -> Dict[str, Any]:
    """
    Fetch detailed article summary and metadata.
    
    Returns comprehensive information including title, authors, abstract,
    MeSH terms, journal details, DOI, and more.
    
    Args:
        pmid: PubMed ID (e.g., "37000000")
        database: "pubmed" or "pmc"
        include_full_metadata: Include all available metadata
    """
    from .tools.retrieval_tools import fetch_article_summary as _fetch
    return await _fetch(
        pmid=pmid,
        database=database,
        include_full_metadata=include_full_metadata
    )


@mcp.tool()
async def fetch_full_article(
    pmid: Optional[str] = None,
    pmcid: Optional[str] = None,
    format: str = "xml"
) -> Dict[str, Any]:
    """
    Fetch complete article content.
    
    For PubMed: Returns abstract and metadata (full text not available).
    For PMC: Returns full text if article is in PMC Open Access.
    
    Args:
        pmid: PubMed ID (for abstracts)
        pmcid: PMC ID (for full-text, e.g., "PMC7611378")
        format: "abstract", "medline", or "xml"
    """
    from .tools.retrieval_tools import fetch_full_article as _fetch
    return await _fetch(pmid=pmid, pmcid=pmcid, format=format)


@mcp.tool()
async def fetch_bioc_article(
    pmid: Optional[str] = None,
    pmcid: Optional[str] = None,
    format: str = "json"
) -> Dict[str, Any]:
    """
    Fetch article in BioC format for text mining.
    
    BioC provides pre-parsed text ideal for NLP tasks:
    - Passage-level segmentation (title, abstract, sections)
    - Sentence-level boundaries
    - Ready for named entity recognition, relation extraction
    
    Args:
        pmid: PubMed ID (for abstract in BioC)
        pmcid: PMC ID (for full-text in BioC)
        format: "xml" or "json"
    """
    from .tools.retrieval_tools import fetch_bioc_article as _fetch
    return await _fetch(pmid=pmid, pmcid=pmcid, format=format)


@mcp.tool()
async def batch_fetch_articles(
    pmids: List[str],
    include_metadata: bool = True,
    include_abstract: bool = True,
    batch_size: int = 100
) -> Dict[str, Any]:
    """
    Efficiently fetch multiple articles with rate limiting.
    
    Handles large batches by chunking requests and respecting
    NCBI rate limits. Returns both successful and failed retrievals.
    
    Args:
        pmids: List of PubMed IDs (up to 10,000)
        include_metadata: Include article metadata
        include_abstract: Include abstracts
        batch_size: IDs per API call (max 500)
    """
    from .tools.retrieval_tools import batch_fetch_articles as _fetch
    return await _fetch(
        pmids=pmids,
        include_metadata=include_metadata,
        include_abstract=include_abstract,
        batch_size=batch_size
    )


# =============================================================================
# Cross-Reference & Linking Tools (3)
# =============================================================================

@mcp.tool()
async def find_related_articles(
    pmid: str,
    relationship_type: str = "similar",
    max_results: int = 20
) -> Dict[str, Any]:
    """
    Find articles related to a source article.
    
    Discovers related literature through citation networks
    and computational similarity.
    
    Args:
        pmid: Source PubMed ID
        relationship_type:
            - "similar": Computationally similar articles
            - "cited_by": Articles that cite this one
            - "cites": Articles this one references
        max_results: Maximum related articles
    """
    from .tools.linking_tools import find_related_articles as _find
    return await _find(
        pmid=pmid,
        relationship_type=relationship_type,
        max_results=max_results
    )


@mcp.tool()
async def link_to_databases(
    pmid: str,
    target_databases: List[str]
) -> Dict[str, Any]:
    """
    Find records in other NCBI databases linked to an article.
    
    Maps from literature to biological knowledge bases.
    
    Args:
        pmid: Source PubMed ID
        target_databases: Databases to link to:
            - "gene": Associated genes
            - "protein": Related proteins
            - "structure": 3D molecular structures
            - "clinvar": Clinical variants
            - "snp": Genetic variants
            - "biosystems": Biological pathways
            - "pccompound": Chemical compounds
    """
    from .tools.linking_tools import link_to_databases as _link
    return await _link(pmid=pmid, target_databases=target_databases)


@mcp.tool()
async def find_citations_by_authors(
    author_name: str,
    date_range_start: Optional[str] = None,
    date_range_end: Optional[str] = None,
    max_results: int = 100
) -> Dict[str, Any]:
    """
    Find all publications by a specific author.
    
    Args:
        author_name: Author name ("LastName FirstInitial" format works best,
            e.g., "Smith J" or "Zhang Feng")
        date_range_start: Start year (YYYY)
        date_range_end: End year (YYYY)
        max_results: Maximum publications to return
    """
    from .tools.linking_tools import find_citations_by_authors as _find
    return await _find(
        author_name=author_name,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        max_results=max_results
    )


# =============================================================================
# ID Conversion Tools (2)
# =============================================================================

@mcp.tool()
async def convert_article_ids(
    ids: List[str],
    from_type: str = "auto",
    include_versions: bool = False
) -> Dict[str, Any]:
    """
    Convert article IDs between different formats.
    
    Supports batch conversion (up to 200 IDs) between:
    - PMID (PubMed ID): e.g., "37000000"
    - PMCID (PubMed Central ID): e.g., "PMC7611378"
    - DOI: e.g., "10.1093/nar/gks1195"
    - Manuscript ID: e.g., "NIHMS1677310"
    
    Args:
        ids: List of IDs to convert (max 200)
        from_type: "auto" (detect), "pmid", "pmcid", "doi", "mid"
        include_versions: Include version history
    """
    from .tools.id_conversion_tools import convert_article_ids as _convert
    return await _convert(
        ids=ids,
        from_type=from_type,
        include_versions=include_versions
    )


@mcp.tool()
async def resolve_article_identifier(
    identifier: str,
    auto_detect_type: bool = True
) -> Dict[str, Any]:
    """
    Resolve a single identifier to all available ID formats.
    
    Automatically detects the ID type and returns all available
    identifiers for the article.
    
    Args:
        identifier: Any article ID (PMID, PMCID, DOI, or MID)
        auto_detect_type: Auto-detect the ID type
        
    Example:
        Input: "10.1038/nature12373"
        Output: {pmid: "23903654", pmcid: "PMC3749474", doi: "10.1038/nature12373"}
    """
    from .tools.id_conversion_tools import resolve_article_identifier as _resolve
    return await _resolve(
        identifier=identifier,
        auto_detect_type=auto_detect_type
    )


# =============================================================================
# Advanced Operations Tools (2)
# =============================================================================

@mcp.tool()
async def build_search_pipeline(
    steps: List[Dict[str, Any]],
    output_step: Optional[int] = None
) -> Dict[str, Any]:
    """
    Build and execute a multi-step search pipeline.
    
    Uses Entrez History Server to chain operations efficiently.
    Ideal for complex queries like:
    "Find diabetes reviews, then limit to articles linked to HLA genes"
    
    Args:
        steps: List of pipeline steps, each with:
            - operation: "search", "link", or "combine"
            - database: Target database ("pubmed", "pmc", "gene", etc.)
            - parameters: Operation-specific params
              - search: {"query": "search terms"}
              - link: {"from_db": "pubmed", "link_name": "pubmed_gene"}
              - combine: {"combine_with": 1, "operator": "AND"}
        output_step: Step number to return results from
        
    Example:
        steps=[
            {"operation": "search", "database": "pubmed", 
             "parameters": {"query": "diabetes[mh] AND review[pt]"}},
            {"operation": "link", "database": "gene",
             "parameters": {"from_db": "pubmed"}}
        ]
    """
    from .tools.advanced_tools import build_search_pipeline as _build
    return await _build(steps=steps, output_step=output_step)


@mcp.tool()
async def batch_process_articles(
    input_source: Dict[str, Any],
    operation: str = "fetch_summaries",
    output_format: str = "json",
    batch_config: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Process large sets of articles with batch operations.
    
    Handles datasets of 10K+ articles efficiently with chunked
    processing and rate limiting.
    
    Args:
        input_source: Data source specification
            - {"from_search": {"query": "...", "database": "pubmed"}}
            - {"from_ids": ["pmid1", "pmid2", ...]}
            - {"from_pipeline": {"query_key": "1", "web_env": "..."}}
        operation:
            - "fetch_summaries": Get article metadata
            - "fetch_full": Get full records
            - "export_bioc": Export in BioC format
            - "text_statistics": Compute text statistics
        output_format: "json", "csv", or "ndjson"
        batch_config: {"batch_size": 100, "parallel_workers": 3}
    """
    from .tools.advanced_tools import batch_process_articles as _process
    return await _process(
        input_source=input_source,
        operation=operation,
        output_format=output_format,
        batch_config=batch_config
    )


# =============================================================================
# Resources
# =============================================================================

@mcp.resource("pubmed://status")
def get_server_status() -> str:
    """Get PubMed MCP Server status and configuration."""
    from .config import Config
    
    return f"""
PubMed Advanced MCP Server Status
=================================
Version: 1.0.0
API Key Configured: {'Yes' if Config.NCBI_API_KEY else 'No'}
Rate Limit: {Config.get_rate_limit()} requests/second

Available Tools (16):
- Search & Discovery: pubmed_search, pmc_search, mesh_term_search, advanced_search, global_search
- Retrieval: fetch_article_summary, fetch_full_article, fetch_bioc_article, batch_fetch_articles
- Linking: find_related_articles, link_to_databases, find_citations_by_authors
- ID Conversion: convert_article_ids, resolve_article_identifier
- Advanced: build_search_pipeline, batch_process_articles

Data Sources:
- PubMed: 34M+ abstracts
- PMC: 7M+ full-text articles (3.8M open access)
- 38+ NCBI databases for cross-linking
"""


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    import os
    
    # Get configuration from environment or defaults
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "8000"))
    
    logger.info(f"Starting PubMed Advanced MCP Server on {host}:{port} (Streamable HTTP transport)")
    
    # Run with Streamable HTTP transport only
    mcp.run(transport="streamable-http", host=host, port=port)
