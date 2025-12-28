"""
Search & Discovery Tools (5 tools)

Tools for finding articles in PubMed and PMC databases.
"""

from typing import Dict, Any, List, Optional
import logging

from ..clients.eutilities import EUtilitiesClient
from ..utils.query_builder import QueryBuilder
from ..schemas.tool_schemas import (
    SearchFilters,
    PubMedSearchInput,
    PMCSearchInput,
    MeSHSearchInput,
    AdvancedSearchInput,
    GlobalSearchInput,
    ArticleSummary,
    Author,
    MeSHTerm,
    Journal,
)

logger = logging.getLogger(__name__)


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
    
    This tool searches across 34M+ PubMed abstracts using natural language
    or structured E-query syntax. Returns publication metadata including
    titles, abstracts, authors, MeSH indexing, and DOI information.
    
    Args:
        query: Search query (natural language or E-utilities syntax)
        filters: Optional filters (publication_date_start/end, publication_types, language, free_full_text_only)
        sort_by: Sort order (relevance, pub_date, first_author)
        max_results: Maximum results to return (1-10000)
        include_abstract: Include abstracts in results
        use_history: Store results on Entrez History for pipeline chaining
        
    Returns:
        Dictionary with total_results, results list, query_translation
        
    Example:
        >>> result = await pubmed_search("CRISPR gene therapy", max_results=10)
        >>> print(f"Found {result['total_results']} articles")
    """
    async with EUtilitiesClient() as client:
        # Build the full query with filters
        if filters:
            full_query = QueryBuilder.build_advanced_query(
                base_query=query,
                date_start=filters.get("publication_date_start"),
                date_end=filters.get("publication_date_end"),
                publication_types=filters.get("publication_types"),
                language=filters.get("language"),
                free_full_text_only=filters.get("free_full_text_only", False),
                open_access_only=filters.get("open_access_only", False)
            )
        else:
            full_query = query
        
        # Execute search
        search_result = await client.search(
            db="pubmed",
            query=full_query,
            retmax=max_results,
            sort=sort_by,
            usehistory=use_history
        )
        
        articles = []
        
        # Fetch summaries for returned IDs
        if search_result["ids"] and include_abstract:
            summaries = await client.summary(
                db="pubmed",
                ids=search_result["ids"][:max_results]
            )
            
            for article_data in summaries.get("results", []):
                article = _parse_article_summary(article_data)
                articles.append(article)
        else:
            # Return minimal info without abstracts
            for pmid in search_result["ids"][:max_results]:
                articles.append({"pmid": pmid})
        
        return {
            "total_results": search_result["count"],
            "returned_count": len(articles),
            "results": articles,
            "query_translation": search_result.get("query_translation", full_query),
            "history_key": search_result.get("query_key"),
            "web_env": search_result.get("web_env")
        }


async def pmc_search(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    has_full_text: bool = True,
    max_results: int = 50,
    use_history: bool = False
) -> Dict[str, Any]:
    """
    Search PMC for full-text articles.
    
    PMC contains 7M+ full-text articles. Unlike PubMed (abstracts only),
    PMC search queries the complete article text.
    
    Args:
        query: Search query
        filters: Optional filters
        has_full_text: Limit to articles with full text
        max_results: Maximum results
        use_history: Store on History server
        
    Returns:
        Dictionary with PMCIDs and article metadata
    """
    async with EUtilitiesClient() as client:
        # Build query
        if filters:
            full_query = QueryBuilder.build_advanced_query(
                base_query=query,
                date_start=filters.get("publication_date_start"),
                date_end=filters.get("publication_date_end"),
                publication_types=filters.get("publication_types"),
                language=filters.get("language"),
                open_access_only=filters.get("open_access_only", False)
            )
        else:
            full_query = query
        
        if has_full_text:
            full_query = f"({full_query}) AND free fulltext[filter]"
        
        # Execute search
        search_result = await client.search(
            db="pmc",
            query=full_query,
            retmax=max_results,
            usehistory=use_history
        )
        
        articles = []
        
        # Fetch summaries
        if search_result["ids"]:
            summaries = await client.summary(
                db="pmc",
                ids=search_result["ids"][:max_results]
            )
            
            for article_data in summaries.get("results", []):
                article = _parse_pmc_summary(article_data)
                articles.append(article)
        
        return {
            "total_results": search_result["count"],
            "returned_count": len(articles),
            "results": articles,
            "query_translation": search_result.get("query_translation", full_query),
            "history_key": search_result.get("query_key"),
            "web_env": search_result.get("web_env")
        }


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
    Search using MeSH (Medical Subject Headings) controlled vocabulary.
    
    MeSH provides standardized, hierarchical indexing for biomedical concepts.
    Using MeSH terms ensures consistent retrieval across different terminologies.
    
    Args:
        mesh_term: MeSH descriptor (e.g., "Neoplasms", "Diabetes Mellitus")
        qualifiers: MeSH qualifiers (e.g., ["therapy", "prevention"])
        search_mode: "exact" for term only, "descendant" for hierarchy
        explode: Include all subtree terms
        date_range_start: Start date filter
        date_range_end: End date filter
        max_results: Maximum results
        
    Returns:
        Dictionary with MeSH descriptor info and matching articles
    """
    async with EUtilitiesClient() as client:
        # Build MeSH query
        mesh_query = QueryBuilder.build_mesh_query(
            mesh_term=mesh_term,
            qualifiers=qualifiers,
            explode=explode
        )
        
        # Add date range if specified
        if date_range_start or date_range_end:
            date_filter = QueryBuilder.build_date_range(
                start_date=date_range_start,
                end_date=date_range_end
            )
            if date_filter:
                mesh_query = f"({mesh_query}) AND {date_filter}"
        
        # Execute search
        search_result = await client.search(
            db="pubmed",
            query=mesh_query,
            retmax=max_results
        )
        
        articles = []
        
        # Fetch summaries
        if search_result["ids"]:
            summaries = await client.summary(
                db="pubmed",
                ids=search_result["ids"][:max_results]
            )
            
            for article_data in summaries.get("results", []):
                article = _parse_article_summary(article_data)
                articles.append(article)
        
        return {
            "mesh_descriptor": {
                "heading": mesh_term,
                "qualifiers": qualifiers,
                "exploded": explode
            },
            "total_results": search_result["count"],
            "returned_count": len(articles),
            "results": articles,
            "query_translation": search_result.get("query_translation", mesh_query)
        }


async def advanced_search(
    query_builder: List[Dict[str, str]],
    date_range_start: Optional[str] = None,
    date_range_end: Optional[str] = None,
    date_field: str = "publication_date",
    max_results: int = 50
) -> Dict[str, Any]:
    """
    Build complex Boolean queries with field-specific search.
    
    Allows precise control over search logic with multiple terms,
    fields, and Boolean operators.
    
    Args:
        query_builder: List of {field, term, operator} dicts
            - field: title, abstract, author, journal, all_fields, mesh
            - term: search term
            - operator: AND, OR, NOT
        date_range_start: Start date
        date_range_end: End date
        date_field: publication_date or entry_date
        max_results: Maximum results
        
    Returns:
        Dictionary with search results
        
    Example:
        >>> result = await advanced_search([
        ...     {"field": "title", "term": "CRISPR", "operator": "AND"},
        ...     {"field": "mesh", "term": "Gene Therapy", "operator": "AND"}
        ... ])
    """
    from ..utils.query_builder import QueryTerm
    
    async with EUtilitiesClient() as client:
        # Convert to QueryTerm objects
        terms = [
            QueryTerm(
                term=qt["term"],
                field=qt.get("field", "all_fields"),
                operator=qt.get("operator", "AND")
            )
            for qt in query_builder
        ]
        
        # Build Boolean query
        base_query = QueryBuilder.build_boolean_query(terms)
        
        # Add date range
        full_query = base_query
        if date_range_start or date_range_end:
            date_filter = QueryBuilder.build_date_range(
                start_date=date_range_start,
                end_date=date_range_end,
                field="dp" if date_field == "publication_date" else "edat"
            )
            if date_filter:
                full_query = f"({base_query}) AND {date_filter}"
        
        # Execute search
        search_result = await client.search(
            db="pubmed",
            query=full_query,
            retmax=max_results
        )
        
        articles = []
        
        if search_result["ids"]:
            summaries = await client.summary(
                db="pubmed",
                ids=search_result["ids"][:max_results]
            )
            
            for article_data in summaries.get("results", []):
                article = _parse_article_summary(article_data)
                articles.append(article)
        
        return {
            "total_results": search_result["count"],
            "returned_count": len(articles),
            "results": articles,
            "query_translation": search_result.get("query_translation", full_query),
            "constructed_query": full_query
        }


async def global_search(
    query: str,
    databases: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Search across all NCBI databases to discover data availability.
    
    Returns hit counts for each of 38+ NCBI databases, helping identify
    which databases have relevant data for a query.
    
    Args:
        query: Search query
        databases: Specific databases to filter (shows all if empty)
        
    Returns:
        Dictionary with database hit counts
    """
    async with EUtilitiesClient() as client:
        try:
            result = await client.gquery(query)
            db_results = result.get("databases", [])
        except Exception as e:
            logger.warning(f"EGQuery failed, using fallback: {e}")
            # Fallback: search key databases individually
            fallback_dbs = databases or ["pubmed", "pmc", "gene", "protein", "structure"]
            db_results = []
            for db_name in fallback_dbs[:10]:  # Limit to 10 databases
                try:
                    search = await client.search(db=db_name, query=query, retmax=0)
                    db_results.append({
                        "db_name": db_name,
                        "menu_name": db_name.title(),
                        "count": search.get("count", 0),
                        "status": "ok"
                    })
                except Exception:
                    db_results.append({
                        "db_name": db_name,
                        "menu_name": db_name.title(),
                        "count": 0,
                        "status": "error"
                    })
        
        # Filter if specific databases requested
        if databases:
            db_lower = [d.lower() for d in databases]
            db_results = [
                d for d in db_results 
                if d.get("db_name", "").lower() in db_lower
            ]
        
        # Calculate total
        total = sum(d.get("count", 0) for d in db_results)
        
        return {
            "query": query,
            "databases": [
                {
                    "name": d.get("db_name"),
                    "display_name": d.get("menu_name"),
                    "result_count": d.get("count", 0),
                    "status": d.get("status", "ok")
                }
                for d in db_results
                if d.get("count", 0) > 0 or d.get("status") != "ok"
            ],
            "total_across_databases": total
        }


# =============================================================================
# Helper Functions
# =============================================================================

def _parse_article_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse ESummary result into article dictionary."""
    # Handle both version 2.0 JSON and older formats
    authors = []
    author_list = data.get("authors") or data.get("AuthorList") or []
    for auth in author_list:
        if isinstance(auth, dict):
            authors.append({
                "name": auth.get("name", auth.get("Name", "")),
                "authtype": auth.get("authtype", "")
            })
        elif isinstance(auth, str):
            authors.append({"name": auth})
    
    return {
        "pmid": str(data.get("uid", data.get("Id", ""))),
        "title": data.get("title", data.get("Title", "")),
        "source": data.get("source", data.get("Source", "")),
        "pubdate": data.get("pubdate", data.get("PubDate", "")),
        "authors": authors,
        "volume": data.get("volume", ""),
        "issue": data.get("issue", ""),
        "pages": data.get("pages", ""),
        "doi": data.get("elocationid", ""),
        "pmcid": data.get("pmcid", ""),
        "pubtype": data.get("pubtype", []),
        "fulljournalname": data.get("fulljournalname", ""),
        "sortfirstauthor": data.get("sortfirstauthor", "")
    }


def _parse_pmc_summary(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse PMC ESummary result."""
    return {
        "pmcid": f"PMC{data.get('uid', data.get('Id', ''))}",
        "title": data.get("title", ""),
        "source": data.get("source", ""),
        "pubdate": data.get("pubdate", ""),
        "pmid": data.get("pmid", ""),
        "doi": data.get("doi", ""),
        "authors": data.get("authors", [])
    }
