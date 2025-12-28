"""
Pydantic schemas for all MCP tools.

Defines input/output models for all 16 tools.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import date


# =============================================================================
# Common Models
# =============================================================================

class SearchFilters(BaseModel):
    """Common search filters."""
    publication_date_start: Optional[str] = Field(
        None,
        description="Start date for publication filter (YYYY or YYYY-MM-DD)"
    )
    publication_date_end: Optional[str] = Field(
        None,
        description="End date for publication filter (YYYY or YYYY-MM-DD)"
    )
    publication_types: Optional[List[str]] = Field(
        None,
        description="Filter by publication types (e.g., Review, Clinical Trial)"
    )
    language: Optional[str] = Field(
        None,
        description="Filter by language (e.g., eng, spa, fre)"
    )
    free_full_text_only: bool = Field(
        False,
        description="Limit to articles with free full text"
    )
    open_access_only: bool = Field(
        False,
        description="Limit to open access articles"
    )


class Author(BaseModel):
    """Author information."""
    lastname: Optional[str] = None
    forename: Optional[str] = None
    initials: Optional[str] = None
    affiliation: Optional[str] = None
    
    @property
    def full_name(self) -> str:
        parts = []
        if self.forename:
            parts.append(self.forename)
        if self.lastname:
            parts.append(self.lastname)
        return " ".join(parts) or "Unknown"


class MeSHTerm(BaseModel):
    """MeSH term with qualifier."""
    heading: str
    qualifiers: Optional[List[str]] = None
    is_major_topic: bool = False


class Journal(BaseModel):
    """Journal information."""
    title: str
    iso_abbr: Optional[str] = None
    nlm_id: Optional[str] = None
    issn: Optional[str] = None


class ArticleSummary(BaseModel):
    """Complete article summary."""
    pmid: str
    pmcid: Optional[str] = None
    doi: Optional[str] = None
    title: str
    abstract: Optional[str] = None
    authors: List[Author] = Field(default_factory=list)
    journal: Optional[Journal] = None
    publication_date: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    mesh_terms: List[MeSHTerm] = Field(default_factory=list)
    publication_types: List[str] = Field(default_factory=list)
    language: Optional[str] = None


# =============================================================================
# Search Tool Schemas
# =============================================================================

class PubMedSearchInput(BaseModel):
    """Input for pubmed_search tool."""
    query: str = Field(
        ...,
        description="Search query in natural language or E-utilities syntax"
    )
    filters: Optional[SearchFilters] = Field(
        None,
        description="Optional search filters"
    )
    sort_by: Literal["relevance", "pub_date", "first_author"] = Field(
        "relevance",
        description="Sort order for results"
    )
    max_results: int = Field(
        50,
        ge=1,
        le=10000,
        description="Maximum number of results to return"
    )
    include_abstract: bool = Field(
        True,
        description="Include abstracts in results"
    )
    use_history: bool = Field(
        False,
        description="Store results on Entrez History server for pipeline chaining"
    )


class PubMedSearchOutput(BaseModel):
    """Output for pubmed_search tool."""
    total_results: int
    results: List[ArticleSummary]
    query_translation: Optional[str] = None
    history_key: Optional[str] = None
    web_env: Optional[str] = None


class PMCSearchInput(BaseModel):
    """Input for pmc_search tool."""
    query: str = Field(
        ...,
        description="Search query for PMC full-text search"
    )
    filters: Optional[SearchFilters] = Field(
        None,
        description="Optional search filters"
    )
    has_full_text: bool = Field(
        True,
        description="Limit to articles with full text available"
    )
    max_results: int = Field(
        50,
        ge=1,
        le=10000,
        description="Maximum number of results"
    )
    use_history: bool = Field(
        False,
        description="Store results on Entrez History server"
    )


class MeSHSearchInput(BaseModel):
    """Input for mesh_term_search tool."""
    mesh_term: str = Field(
        ...,
        description="MeSH descriptor term (e.g., Neoplasms)"
    )
    qualifiers: Optional[List[str]] = Field(
        None,
        description="MeSH qualifiers (e.g., therapy, prevention)"
    )
    search_mode: Literal["exact", "descendant"] = Field(
        "descendant",
        description="Search exact term or include hierarchy descendants"
    )
    explode: bool = Field(
        True,
        description="Include all subtree terms in MeSH hierarchy"
    )
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    max_results: int = Field(
        50,
        ge=1,
        le=10000
    )


class QueryTerm(BaseModel):
    """A single term in an advanced query."""
    field: Literal[
        "title", "abstract", "author", "journal", "all_fields", "mesh"
    ] = Field(
        "all_fields",
        description="Field to search"
    )
    term: str = Field(
        ...,
        description="Search term"
    )
    operator: Literal["AND", "OR", "NOT"] = Field(
        "AND",
        description="Boolean operator"
    )


class AdvancedSearchInput(BaseModel):
    """Input for advanced_search tool."""
    query_builder: List[QueryTerm] = Field(
        ...,
        description="List of search terms with fields and operators"
    )
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    date_field: Literal["publication_date", "entry_date"] = "publication_date"
    max_results: int = Field(50, ge=1, le=10000)


class GlobalSearchInput(BaseModel):
    """Input for global_search tool."""
    query: str = Field(
        ...,
        description="Search query to check across all NCBI databases"
    )
    databases: Optional[List[str]] = Field(
        None,
        description="Specific databases to include (searches all if empty)"
    )


class DatabaseHitCount(BaseModel):
    """Hit count for a single database."""
    db_name: str
    display_name: str
    result_count: int
    status: str


class GlobalSearchOutput(BaseModel):
    """Output for global_search tool."""
    databases: List[DatabaseHitCount]
    total_across_databases: int


# =============================================================================
# Retrieval Tool Schemas
# =============================================================================

class FetchSummaryInput(BaseModel):
    """Input for fetch_article_summary tool."""
    pmid: str = Field(
        ...,
        description="PubMed ID to fetch"
    )
    database: Literal["pubmed", "pmc"] = Field(
        "pubmed",
        description="Database to fetch from"
    )
    include_full_metadata: bool = Field(
        True,
        description="Include all available metadata"
    )


class FetchFullArticleInput(BaseModel):
    """Input for fetch_full_article tool."""
    pmid: Optional[str] = Field(
        None,
        description="PubMed ID (for abstracts)"
    )
    pmcid: Optional[str] = Field(
        None,
        description="PMC ID (for full-text)"
    )
    format: Literal["abstract", "medline", "xml"] = Field(
        "xml",
        description="Output format"
    )


class FetchBioCInput(BaseModel):
    """Input for fetch_bioc_article tool."""
    pmid: Optional[str] = Field(
        None,
        description="PubMed ID (for abstracts in BioC format)"
    )
    pmcid: Optional[str] = Field(
        None,
        description="PMC ID (for full-text in BioC format)"
    )
    format: Literal["xml", "json"] = Field(
        "json",
        description="BioC output format"
    )


class BatchFetchInput(BaseModel):
    """Input for batch_fetch_articles tool."""
    pmids: List[str] = Field(
        ...,
        description="List of PubMed IDs to fetch"
    )
    include_metadata: bool = Field(
        True,
        description="Include article metadata"
    )
    include_abstract: bool = Field(
        True,
        description="Include abstracts"
    )
    batch_size: int = Field(
        100,
        ge=1,
        le=500,
        description="IDs per batch (for rate limiting)"
    )


# =============================================================================
# Linking Tool Schemas
# =============================================================================

class RelatedArticlesInput(BaseModel):
    """Input for find_related_articles tool."""
    pmid: str = Field(
        ...,
        description="Source PubMed ID"
    )
    relationship_type: Literal["cited_by", "cites", "similar"] = Field(
        "similar",
        description="Type of relationship to find"
    )
    max_results: int = Field(
        20,
        ge=1,
        le=500,
        description="Maximum related articles to return"
    )


class LinkToDatabasesInput(BaseModel):
    """Input for link_to_databases tool."""
    pmid: str = Field(
        ...,
        description="Source PubMed ID"
    )
    target_databases: List[Literal[
        "gene", "protein", "structure", "clinvar", "snp", "biosystems", "pccompound"
    ]] = Field(
        ...,
        description="Target databases to link to"
    )


class AuthorCitationsInput(BaseModel):
    """Input for find_citations_by_authors tool."""
    author_name: str = Field(
        ...,
        description="Author name (LastName FirstInitial format preferred)"
    )
    date_range_start: Optional[str] = Field(
        None,
        description="Start year (YYYY)"
    )
    date_range_end: Optional[str] = Field(
        None,
        description="End year (YYYY)"
    )
    max_results: int = Field(
        100,
        ge=1,
        le=1000
    )


# =============================================================================
# ID Conversion Tool Schemas
# =============================================================================

class ConvertIDsInput(BaseModel):
    """Input for convert_article_ids tool."""
    ids: List[str] = Field(
        ...,
        description="IDs to convert (max 200)"
    )
    from_type: Literal["auto", "pmid", "pmcid", "doi", "mid"] = Field(
        "auto",
        description="Source ID type (auto-detect if not specified)"
    )
    include_versions: bool = Field(
        False,
        description="Include version history"
    )


class IDConversion(BaseModel):
    """Single ID conversion result."""
    requested_id: str
    pmid: Optional[str] = None
    pmcid: Optional[str] = None
    doi: Optional[str] = None
    manuscript_id: Optional[str] = None
    is_live: bool = True
    release_date: Optional[str] = None
    versions: Optional[List[Dict[str, Any]]] = None


class ConvertIDsOutput(BaseModel):
    """Output for convert_article_ids tool."""
    conversions: List[IDConversion]
    failed_ids: List[Dict[str, str]] = Field(default_factory=list)
    total_requested: int
    successful: int


class ResolveIDInput(BaseModel):
    """Input for resolve_article_identifier tool."""
    identifier: str = Field(
        ...,
        description="Single identifier to resolve"
    )
    auto_detect_type: bool = Field(
        True,
        description="Auto-detect ID type"
    )


# =============================================================================
# Advanced Tool Schemas
# =============================================================================

class PipelineStepInput(BaseModel):
    """A single step in a search pipeline."""
    operation: Literal["search", "link", "combine"] = Field(
        ...,
        description="Operation type"
    )
    database: str = Field(
        ...,
        description="Target database"
    )
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific parameters (query, link_name, etc.)"
    )


class BuildPipelineInput(BaseModel):
    """Input for build_search_pipeline tool."""
    steps: List[PipelineStepInput] = Field(
        ...,
        description="Pipeline steps to execute"
    )
    output_step: Optional[int] = Field(
        None,
        description="Which step's results to return (last step if not specified)"
    )


class BatchProcessInput(BaseModel):
    """Input for batch_process_articles tool."""
    input_source: Dict[str, Any] = Field(
        ...,
        description="Source: {from_search: {query, database}}, {from_ids: [ids]}, or {from_pipeline: {query_key, web_env}}"
    )
    operation: Literal[
        "fetch_summaries", "fetch_full", "export_bioc", "text_statistics"
    ] = Field(
        "fetch_summaries",
        description="Processing operation"
    )
    output_format: Literal["json", "csv", "ndjson"] = Field(
        "json",
        description="Output format"
    )
    batch_config: Dict[str, int] = Field(
        default_factory=lambda: {"batch_size": 100, "parallel_workers": 3}
    )
