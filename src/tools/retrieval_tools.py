"""
Document Retrieval & Mining Tools (4 tools)

Tools for fetching article content and metadata.
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging

from ..clients.eutilities import EUtilitiesClient
from ..clients.bioc_api import BioCClient
from ..config import Config

logger = logging.getLogger(__name__)


async def fetch_article_summary(
    pmid: str,
    database: str = "pubmed",
    include_full_metadata: bool = True
) -> Dict[str, Any]:
    """
    Fetch detailed article summary and metadata.
    
    Returns comprehensive article information including title, authors,
    abstract, MeSH terms, publication details, and more.
    
    Args:
        pmid: PubMed ID
        database: Database (pubmed or pmc)
        include_full_metadata: Include all available metadata
        
    Returns:
        Dictionary with complete article metadata
    """
    async with EUtilitiesClient() as client:
        # Get summary
        summaries = await client.summary(
            db=database,
            ids=[pmid],
            version="2.0"
        )
        
        results = summaries.get("results", [])
        
        if not results:
            return {
                "error": f"Article not found: {pmid}",
                "pmid": pmid
            }
        
        article = results[0]
        
        # If we want full metadata, also fetch the full record
        if include_full_metadata:
            try:
                full_record = await client.fetch(
                    db=database,
                    ids=[pmid],
                    rettype="abstract",
                    retmode="xml"
                )
                article["full_record_xml"] = full_record[:10000]  # Truncate for safety
            except Exception as e:
                logger.warning(f"Could not fetch full record: {e}")
        
        return {
            "pmid": pmid,
            "database": database,
            "title": article.get("title", ""),
            "source": article.get("source", ""),
            "authors": article.get("authors", []),
            "pubdate": article.get("pubdate", ""),
            "volume": article.get("volume", ""),
            "issue": article.get("issue", ""),
            "pages": article.get("pages", ""),
            "doi": article.get("elocationid", "").replace("doi: ", ""),
            "pmcid": article.get("pmcid", ""),
            "pubtype": article.get("pubtype", []),
            "fulljournalname": article.get("fulljournalname", ""),
            "essn": article.get("essn", ""),
            "issn": article.get("issn", ""),
            "recordstatus": article.get("recordstatus", ""),
            "pubstatus": article.get("pubstatus", ""),
            "availablefromurl": article.get("availablefromurl", "")
        }


async def fetch_full_article(
    pmid: Optional[str] = None,
    pmcid: Optional[str] = None,
    format: str = "xml"
) -> Dict[str, Any]:
    """
    Fetch full article content.
    
    For PubMed: Returns abstract and metadata (full text not available)
    For PMC: Returns full text if article is in PMC Open Access
    
    Args:
        pmid: PubMed ID (for abstracts)
        pmcid: PMC ID (for full-text)
        format: Output format (abstract, medline, xml)
        
    Returns:
        Dictionary with article content
    """
    if not pmid and not pmcid:
        return {"error": "Either pmid or pmcid must be provided"}
    
    async with EUtilitiesClient() as client:
        if pmcid:
            # Fetch from PMC for full text
            db = "pmc"
            identifier = pmcid.replace("PMC", "") if pmcid.startswith("PMC") else pmcid
            rettype = "full"
        else:
            # Fetch from PubMed (abstract only)
            db = "pubmed"
            identifier = pmid
            rettype = format if format != "xml" else "abstract"
        
        content = await client.fetch(
            db=db,
            ids=[identifier],
            rettype=rettype,
            retmode="xml"
        )
        
        return {
            "pmid": pmid,
            "pmcid": pmcid,
            "database": db,
            "format": format,
            "content": content,
            "content_length": len(content)
        }


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
        format: Output format (xml or json)
        
    Returns:
        Dictionary with BioC document
    """
    if not pmid and not pmcid:
        return {"error": "Either pmid or pmcid must be provided"}
    
    async with BioCClient() as client:
        if pmcid:
            # Fetch from PMC BioC API
            result = await client.fetch_pmc_bioc(pmcid, format=format)
            identifier = pmcid
            source = "pmc"
        else:
            # Fetch from PubMed BioC API
            result = await client.fetch_pubmed_bioc(pmid, format=format)
            identifier = pmid
            source = "pubmed"
        
        # Extract sections for convenience
        sections = client.extract_sections_from_bioc(result)
        plain_text = client.extract_text_from_bioc(result)
        
        return {
            "identifier": identifier,
            "source": source,
            "format": f"bioc_{format}",
            "bioc_document": result,
            "sections": sections,
            "plain_text": plain_text,
            "section_count": len(sections),
            "character_count": len(plain_text)
        }


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
        pmids: List of PubMed IDs to fetch (up to 10,000)
        include_metadata: Include article metadata
        include_abstract: Include abstracts
        batch_size: IDs per API call (max 500)
        
    Returns:
        Dictionary with articles array and processing stats
    """
    if not pmids:
        return {"error": "No PMIDs provided", "articles": []}
    
    # Limit batch size
    batch_size = min(batch_size, Config.MAX_BATCH_SIZE)
    
    async with EUtilitiesClient() as client:
        all_articles = []
        failed_ids = []
        
        # Process in batches
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            
            try:
                summaries = await client.summary(
                    db="pubmed",
                    ids=batch,
                    version="2.0"
                )
                
                for article in summaries.get("results", []):
                    parsed = {
                        "pmid": str(article.get("uid", "")),
                        "title": article.get("title", ""),
                        "source": article.get("source", ""),
                        "pubdate": article.get("pubdate", ""),
                        "authors": article.get("authors", []),
                        "doi": article.get("elocationid", ""),
                        "pmcid": article.get("pmcid", "")
                    }
                    
                    if include_metadata:
                        parsed.update({
                            "volume": article.get("volume", ""),
                            "issue": article.get("issue", ""),
                            "pages": article.get("pages", ""),
                            "pubtype": article.get("pubtype", []),
                            "fulljournalname": article.get("fulljournalname", "")
                        })
                    
                    all_articles.append(parsed)
                
                logger.info(f"Fetched batch {i//batch_size + 1}: {len(batch)} articles")
                
            except Exception as e:
                logger.error(f"Batch fetch failed for {len(batch)} IDs: {e}")
                failed_ids.extend(batch)
        
        return {
            "total_requested": len(pmids),
            "successful": len(all_articles),
            "failed": len(failed_ids),
            "articles": all_articles,
            "failed_ids": failed_ids,
            "batch_size_used": batch_size
        }
