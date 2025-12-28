"""
Advanced Operations Tools (2 tools)

Tools for complex multi-step queries and batch processing.
"""

from typing import Dict, Any, List, Optional
import asyncio
import logging

from ..clients.eutilities import EUtilitiesClient
from ..clients.session_manager import SessionManager
from ..config import Config

logger = logging.getLogger(__name__)


async def build_search_pipeline(
    steps: List[Dict[str, Any]],
    output_step: Optional[int] = None
) -> Dict[str, Any]:
    """
    Build and execute a multi-step search pipeline.
    
    Uses Entrez History Server to chain operations without
    re-downloading intermediate results. Ideal for complex queries like:
    "Find diabetes reviews, then limit to articles linked to HLA genes"
    
    Args:
        steps: List of pipeline steps, each with:
            - operation: "search", "link", or "combine"
            - database: Target database
            - parameters: Operation-specific params
                - For search: {query: str}
                - For link: {from_db: str, link_name: str}
                - For combine: {combine_with: int, operator: str}
        output_step: Which step's results to return (last if not specified)
        
    Returns:
        Dictionary with pipeline execution log and results
        
    Example:
        >>> result = await build_search_pipeline([
        ...     {"operation": "search", "database": "pubmed", 
        ...      "parameters": {"query": "diabetes review"}},
        ...     {"operation": "link", "database": "gene",
        ...      "parameters": {"from_db": "pubmed"}}
        ... ])
    """
    session = SessionManager()
    
    try:
        execution_log = []
        
        for i, step in enumerate(steps):
            operation = step.get("operation", "search")
            database = step.get("database", "pubmed")
            params = step.get("parameters", {})
            
            step_result = None
            
            if operation == "search":
                if i == 0:
                    # First step: start session
                    step_result = await session.start_session(
                        db=database,
                        query=params.get("query", "")
                    )
                else:
                    # Subsequent search: chain with history
                    step_result = await session.add_search_step(
                        db=database,
                        query=params.get("query", ""),
                        combine_with=params.get("combine_with"),
                        combine_operator=params.get("operator", "AND")
                    )
            
            elif operation == "link":
                step_result = await session.add_link_step(
                    from_db=params.get("from_db", "pubmed"),
                    to_db=database,
                    link_name=params.get("link_name"),
                    from_step=params.get("from_step")
                )
            
            elif operation == "combine":
                # Combine is a special search that references previous steps
                combine_with = params.get("combine_with")
                if combine_with:
                    step_result = await session.add_search_step(
                        db=database,
                        query=params.get("query", "*"),
                        combine_with=str(combine_with),
                        combine_operator=params.get("operator", "AND")
                    )
            
            if step_result:
                execution_log.append({
                    "step": i + 1,
                    "operation": operation,
                    "database": database,
                    "query_key": step_result.query_key,
                    "result_count": step_result.result_count
                })
        
        # Get summary
        summary = session.get_pipeline_summary()
        
        # Fetch final results if requested
        final_results = None
        target_step = output_step or len(steps)
        
        if summary.get("final_result_count", 0) > 0:
            try:
                raw_results = await session.fetch_results(
                    step=target_step,
                    retmax=100  # Limit for response size
                )
                final_results = {
                    "format": "xml",
                    "content_preview": raw_results[:5000]  # Preview
                }
            except Exception as e:
                logger.warning(f"Could not fetch final results: {e}")
        
        return {
            "pipeline_steps": len(steps),
            "execution_log": execution_log,
            "summary": summary,
            "final_results": final_results,
            "web_env": summary.get("web_env"),
            "final_count": summary.get("final_result_count", 0)
        }
        
    finally:
        await session.close()


async def batch_process_articles(
    input_source: Dict[str, Any],
    operation: str = "fetch_summaries",
    output_format: str = "json",
    batch_config: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """
    Process large sets of articles with map/reduce style operations.
    
    Handles datasets of 10K+ articles efficiently with:
    - Chunked processing respecting rate limits
    - Parallel workers for throughput
    - Progress tracking
    
    Args:
        input_source: Data source specification
            - {"from_search": {"query": str, "database": str}}
            - {"from_ids": [list of IDs]}
            - {"from_pipeline": {"query_key": str, "web_env": str}}
        operation: Processing operation
            - "fetch_summaries": Get article metadata
            - "fetch_full": Get full records
            - "export_bioc": Export in BioC format
            - "text_statistics": Compute text stats
        output_format: Output format (json, csv, ndjson)
        batch_config: {batch_size: int, parallel_workers: int}
        
    Returns:
        Dictionary with processed results and statistics
    """
    config = batch_config or {"batch_size": 100, "parallel_workers": 3}
    batch_size = min(config.get("batch_size", 100), Config.MAX_BATCH_SIZE)
    
    async with EUtilitiesClient() as client:
        # Resolve input source to list of IDs
        pmids = []
        source_info = {}
        
        if "from_ids" in input_source:
            pmids = input_source["from_ids"]
            source_info = {"type": "direct_ids", "count": len(pmids)}
            
        elif "from_search" in input_source:
            search_params = input_source["from_search"]
            result = await client.search(
                db=search_params.get("database", "pubmed"),
                query=search_params.get("query", ""),
                retmax=10000  # Max for batch processing
            )
            pmids = result.get("ids", [])
            source_info = {
                "type": "search",
                "query": search_params.get("query"),
                "total_available": result.get("count", 0)
            }
            
        elif "from_pipeline" in input_source:
            # Use History server to get IDs
            pipeline_params = input_source["from_pipeline"]
            raw = await client.fetch(
                db="pubmed",
                query_key=pipeline_params.get("query_key"),
                web_env=pipeline_params.get("web_env"),
                rettype="uilist",
                retmode="text",
                retmax=10000
            )
            pmids = [id.strip() for id in raw.strip().split("\n") if id.strip()]
            source_info = {"type": "pipeline", "count": len(pmids)}
        
        if not pmids:
            return {
                "error": "No articles found from input source",
                "source_info": source_info
            }
        
        # Process based on operation
        results = []
        errors = []
        processed = 0
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            
            try:
                if operation == "fetch_summaries":
                    summaries = await client.summary(db="pubmed", ids=batch)
                    results.extend(summaries.get("results", []))
                    
                elif operation == "fetch_full":
                    content = await client.fetch(
                        db="pubmed",
                        ids=batch,
                        rettype="abstract",
                        retmode="xml"
                    )
                    results.append({
                        "batch": i // batch_size + 1,
                        "ids": batch,
                        "content_length": len(content)
                    })
                    
                elif operation == "text_statistics":
                    summaries = await client.summary(db="pubmed", ids=batch)
                    for article in summaries.get("results", []):
                        title = article.get("title", "")
                        results.append({
                            "pmid": article.get("uid", ""),
                            "title_length": len(title),
                            "title_words": len(title.split()),
                            "author_count": len(article.get("authors", []))
                        })
                
                processed += len(batch)
                logger.info(f"Processed batch {i//batch_size + 1}: {processed}/{len(pmids)}")
                
            except Exception as e:
                logger.error(f"Batch processing error: {e}")
                errors.extend([{"id": id, "error": str(e)} for id in batch])
        
        # Format output
        output = {
            "operation": operation,
            "source_info": source_info,
            "total_input": len(pmids),
            "processed": processed,
            "error_count": len(errors),
            "batch_size": batch_size,
            "format": output_format
        }
        
        if output_format == "json":
            output["results"] = results
        elif output_format == "ndjson":
            # Newline-delimited JSON
            import json
            output["results_ndjson"] = "\n".join(json.dumps(r) for r in results)
        elif output_format == "csv":
            # Simple CSV for summaries
            if results and operation in ["fetch_summaries", "text_statistics"]:
                headers = list(results[0].keys()) if results else []
                rows = [",".join(str(r.get(h, "")) for h in headers) for r in results]
                output["csv_content"] = "\n".join([",".join(headers)] + rows)
        
        if errors:
            output["errors"] = errors[:100]  # Limit error list
        
        return output
