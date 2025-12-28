"""
Cross-Reference & Linking Tools (3 tools)

Tools for discovering related articles and cross-references.
"""

from typing import Dict, Any, List, Optional
import logging

from ..clients.eutilities import EUtilitiesClient
from ..utils.query_builder import QueryBuilder

logger = logging.getLogger(__name__)


async def find_related_articles(
    pmid: str,
    relationship_type: str = "similar",
    max_results: int = 20
) -> Dict[str, Any]:
    """
    Find articles related to a source article.
    
    Discovers related literature through:
    - Citation relationships (who cites this, what this cites)
    - Computational similarity (shared concepts, MeSH terms)
    
    Args:
        pmid: Source PubMed ID
        relationship_type: Type of relationship
            - "similar": Computationally similar articles
            - "cited_by": Articles citing this one
            - "cites": Articles this one cites
        max_results: Maximum related articles to return
        
    Returns:
        Dictionary with related articles
    """
    async with EUtilitiesClient() as client:
        # Map relationship type to ELink linkname
        linkname_map = {
            "similar": "pubmed_pubmed",  # Computationally similar
            "cited_by": "pubmed_pubmed_citedin",  # Cited by
            "cites": "pubmed_pubmed_refs"  # References
        }
        
        linkname = linkname_map.get(relationship_type, "pubmed_pubmed")
        
        result = await client.link(
            dbfrom="pubmed",
            db="pubmed",
            ids=[pmid],
            linkname=linkname,
            retmode="json"
        )
        
        # Extract linked IDs
        related_ids = []
        for linkset in result.get("linksets", []):
            related_ids.extend(linkset.get("ids", []))
        
        # Limit results
        related_ids = related_ids[:max_results]
        
        # Fetch summaries for related articles
        articles = []
        if related_ids:
            summaries = await client.summary(
                db="pubmed",
                ids=related_ids
            )
            
            for article in summaries.get("results", []):
                articles.append({
                    "pmid": str(article.get("uid", "")),
                    "title": article.get("title", ""),
                    "source": article.get("source", ""),
                    "pubdate": article.get("pubdate", ""),
                    "authors": article.get("authors", [])
                })
        
        return {
            "source_pmid": pmid,
            "relationship_type": relationship_type,
            "total_related": len(related_ids),
            "related_articles": articles
        }


async def link_to_databases(
    pmid: str,
    target_databases: List[str]
) -> Dict[str, Any]:
    """
    Find records in other NCBI databases linked to an article.
    
    Maps from literature to biological knowledge bases like:
    - Gene: Associated genes
    - Protein: Related proteins
    - Structure: 3D molecular structures
    - ClinVar: Clinical variants
    - SNP: Genetic variants
    - BioSystems: Biological pathways
    
    Args:
        pmid: Source PubMed ID
        target_databases: List of databases to link to
        
    Returns:
        Dictionary with linked records per database
    """
    async with EUtilitiesClient() as client:
        linked_records = {}
        
        for target_db in target_databases:
            try:
                result = await client.link(
                    dbfrom="pubmed",
                    db=target_db,
                    ids=[pmid],
                    retmode="json"
                )
                
                # Extract linked IDs
                linked_ids = []
                for linkset in result.get("linksets", []):
                    linked_ids.extend(linkset.get("ids", []))
                
                if linked_ids:
                    # Get summaries for linked records
                    try:
                        summaries = await client.summary(
                            db=target_db,
                            ids=linked_ids[:20]  # Limit to 20 per database
                        )
                        
                        records = []
                        for item in summaries.get("results", []):
                            records.append({
                                "uid": str(item.get("uid", "")),
                                "name": item.get("name", item.get("title", "")),
                                "description": item.get("description", "")[:200]
                            })
                        
                        linked_records[target_db] = {
                            "count": len(linked_ids),
                            "records": records
                        }
                    except Exception as e:
                        linked_records[target_db] = {
                            "count": len(linked_ids),
                            "ids": linked_ids[:20],
                            "note": "Could not fetch record details"
                        }
                else:
                    linked_records[target_db] = {
                        "count": 0,
                        "records": []
                    }
                    
            except Exception as e:
                logger.error(f"Error linking to {target_db}: {e}")
                linked_records[target_db] = {
                    "error": str(e)
                }
        
        return {
            "source_pmid": pmid,
            "linked_records": linked_records,
            "databases_queried": target_databases
        }


async def find_citations_by_authors(
    author_name: str,
    date_range_start: Optional[str] = None,
    date_range_end: Optional[str] = None,
    max_results: int = 100
) -> Dict[str, Any]:
    """
    Find all publications by a specific author.
    
    Searches for an author's publication history with optional
    date range filtering.
    
    Args:
        author_name: Author name (LastName FirstInitial format works best)
        date_range_start: Start year (YYYY)
        date_range_end: End year (YYYY)
        max_results: Maximum results
        
    Returns:
        Dictionary with author's publications
    """
    async with EUtilitiesClient() as client:
        # Build author query
        query = QueryBuilder.build_author_query(
            author_name=author_name,
            date_start=date_range_start,
            date_end=date_range_end
        )
        
        # Search
        search_result = await client.search(
            db="pubmed",
            query=query,
            retmax=max_results,
            sort="pub_date"  # Sort by date
        )
        
        articles = []
        
        if search_result["ids"]:
            summaries = await client.summary(
                db="pubmed",
                ids=search_result["ids"]
            )
            
            for article in summaries.get("results", []):
                articles.append({
                    "pmid": str(article.get("uid", "")),
                    "title": article.get("title", ""),
                    "source": article.get("source", ""),
                    "pubdate": article.get("pubdate", ""),
                    "authors": article.get("authors", []),
                    "doi": article.get("elocationid", "")
                })
        
        return {
            "author_query": author_name,
            "date_range": {
                "start": date_range_start,
                "end": date_range_end
            },
            "total_publications": search_result["count"],
            "returned_count": len(articles),
            "publications": articles
        }
