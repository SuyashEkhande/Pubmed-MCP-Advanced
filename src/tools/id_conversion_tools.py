"""
ID Conversion & Validation Tools (2 tools)

Tools for converting between article identifier formats.
"""

from typing import Dict, Any, List, Optional
import logging

from ..clients.id_converter import IDConverterClient

logger = logging.getLogger(__name__)


async def convert_article_ids(
    ids: List[str],
    from_type: str = "auto",
    include_versions: bool = False
) -> Dict[str, Any]:
    """
    Convert article IDs between different formats.
    
    Supports batch conversion (up to 200 IDs) between:
    - PMID (PubMed ID): e.g., 37000000
    - PMCID (PubMed Central ID): e.g., PMC7611378
    - DOI (Digital Object Identifier): e.g., 10.1093/nar/gks1195
    - Manuscript ID: e.g., NIHMS1677310
    
    Args:
        ids: List of IDs to convert (max 200)
        from_type: Source ID type (auto, pmid, pmcid, doi, mid)
        include_versions: Include version history
        
    Returns:
        Dictionary with conversion results
        
    Example:
        >>> result = await convert_article_ids(["37000000", "36000000"])
        >>> for conv in result["conversions"]:
        ...     print(f"PMID {conv['pmid']} -> DOI {conv['doi']}")
    """
    async with IDConverterClient() as client:
        # Auto-detect ID type if needed
        idtype = None if from_type == "auto" else from_type
        
        result = await client.convert_ids(
            ids=ids,
            idtype=idtype,
            versions=include_versions
        )
        
        return {
            "total_requested": result.get("total_requested", len(ids)),
            "successful": result.get("successful", 0),
            "failed_count": result.get("failed_count", 0),
            "conversions": result.get("conversions", []),
            "failed_ids": result.get("failed", [])
        }


async def resolve_article_identifier(
    identifier: str,
    auto_detect_type: bool = True
) -> Dict[str, Any]:
    """
    Resolve a single identifier to all available ID formats.
    
    Automatically detects the ID type and returns all available
    identifiers for the article.
    
    Args:
        identifier: Single ID to resolve
        auto_detect_type: Auto-detect the ID type
        
    Returns:
        Dictionary with all available identifiers
        
    Example:
        >>> result = await resolve_article_identifier("10.1093/nar/gks1195")
        >>> print(f"PMID: {result['pmid']}, PMCID: {result['pmcid']}")
    """
    async with IDConverterClient() as client:
        # Detect ID type
        detected_type = client.detect_id_type(identifier) if auto_detect_type else None
        
        try:
            result = await client.resolve_id(
                identifier=identifier,
                idtype=detected_type if detected_type != "unknown" else None
            )
            
            return {
                "input_identifier": identifier,
                "detected_type": detected_type,
                "pmid": result.get("pmid"),
                "pmcid": result.get("pmcid"),
                "doi": result.get("doi"),
                "manuscript_id": result.get("manuscript_id"),
                "is_live": result.get("live", True),
                "release_date": result.get("release_date"),
                "versions": result.get("versions", [])
            }
            
        except Exception as e:
            return {
                "input_identifier": identifier,
                "detected_type": detected_type,
                "error": str(e),
                "suggestion": _get_id_suggestion(identifier, detected_type)
            }


def _get_id_suggestion(identifier: str, detected_type: str) -> str:
    """Provide helpful suggestions for failed ID resolution."""
    suggestions = {
        "pmid": "Verify the PMID is correct. PMIDs are numeric (e.g., 37000000).",
        "pmcid": "Verify the PMCID is correct. Format: PMC followed by numbers (e.g., PMC7611378).",
        "doi": "Verify the DOI is correct. DOIs start with '10.' (e.g., 10.1093/nar/gks1195).",
        "mid": "Verify the Manuscript ID. Format: NIHMS followed by numbers.",
        "unknown": "Could not determine ID type. Try specifying the type explicitly."
    }
    return suggestions.get(detected_type, suggestions["unknown"])
