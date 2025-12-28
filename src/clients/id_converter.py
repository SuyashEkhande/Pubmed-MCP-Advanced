"""
PMC ID Converter API client.

Converts between:
- PMID (PubMed ID)
- PMCID (PubMed Central ID)
- DOI (Digital Object Identifier)
- Manuscript ID (MID)
"""

import json
from typing import Dict, Any, List, Optional
import logging
import httpx

from ..config import Config
from ..utils.error_handler import InvalidIDError, PubMedError

logger = logging.getLogger(__name__)


class IDConverterClient:
    """
    Client for PMC ID Converter API.
    
    Endpoint: https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/
    
    Supports:
    - Batch conversion (up to 200 IDs)
    - Auto-detect ID type
    - Version history retrieval
    """
    
    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    
    def __init__(self, timeout: int = 60):
        """
        Initialize ID Converter client.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True
            )
        return self._client
    
    async def convert_ids(
        self,
        ids: List[str],
        idtype: Optional[str] = None,
        format: str = "json",
        versions: bool = False,
        showaiid: bool = False
    ) -> Dict[str, Any]:
        """
        Convert article IDs between formats.
        
        Args:
            ids: List of IDs to convert (max 200)
            idtype: ID type hint (pmid, pmcid, mid, doi, or auto-detect)
            format: Output format (json, xml, csv)
            versions: Include version history
            showaiid: Include article instance IDs
            
        Returns:
            Dictionary with conversion results
        """
        if len(ids) > Config.MAX_IDS_PER_ID_CONVERTER_REQUEST:
            raise InvalidIDError(
                message=f"Too many IDs: {len(ids)}. Maximum is {Config.MAX_IDS_PER_ID_CONVERTER_REQUEST}",
                identifier=str(len(ids)),
                expected_format=f"Maximum {Config.MAX_IDS_PER_ID_CONVERTER_REQUEST} IDs per request"
            )
        
        client = await self._get_client()
        
        # Build request parameters
        params = {
            "ids": ",".join(ids),
            "format": format,
            "tool": Config.TOOL_NAME,
            "email": Config.TOOL_EMAIL
        }
        
        if idtype:
            params["idtype"] = idtype
        
        if versions:
            params["versions"] = "yes"
        
        if showaiid:
            params["showaiid"] = "yes"
        
        try:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            if format == "json":
                return self._parse_json_response(response.text)
            else:
                return {"raw": response.text, "format": format}
                
        except httpx.TimeoutException as e:
            logger.error(f"ID conversion timeout: {e}")
            raise PubMedError(
                message="ID conversion request timed out",
                details=str(e)
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"ID conversion HTTP error: {e}")
            raise PubMedError(
                message=f"ID conversion failed with status {e.response.status_code}",
                details=str(e)
            )
        except httpx.RequestError as e:
            logger.error(f"ID conversion network error: {e}")
            raise PubMedError(
                message="ID conversion network error",
                details=str(e)
            )
        except Exception as e:
            logger.error(f"ID conversion error: {e}")
            raise PubMedError(
                message="ID conversion failed",
                details=str(e)
            )
    
    def _parse_json_response(self, json_text: str) -> Dict[str, Any]:
        """
        Parse ID Converter JSON response.
        
        Args:
            json_text: Raw JSON response
            
        Returns:
            Structured conversion results
        """
        try:
            data = json.loads(json_text)
            
            records = data.get("records", [])
            conversions = []
            failed = []
            
            for record in records:
                # Check for errors
                if "errmsg" in record:
                    failed.append({
                        "id": record.get("requested-id", ""),
                        "error": record.get("errmsg", "Unknown error")
                    })
                    continue
                
                conversion = {
                    "requested_id": record.get("requested-id", ""),
                    "pmid": record.get("pmid"),
                    "pmcid": record.get("pmcid"),
                    "doi": record.get("doi"),
                    "live": record.get("live", "true") == "true",
                    "release_date": record.get("release-date"),
                }
                
                # Include versions if present
                if "versions" in record:
                    conversion["versions"] = record["versions"]
                
                conversions.append(conversion)
            
            return {
                "status": data.get("status", "ok"),
                "conversions": conversions,
                "failed": failed,
                "total_requested": len(records),
                "successful": len(conversions),
                "failed_count": len(failed)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ID converter JSON: {e}")
            raise PubMedError(
                message="Failed to parse ID conversion response",
                details=str(e)
            )
    
    async def resolve_id(
        self,
        identifier: str,
        idtype: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve a single identifier to all available ID formats.
        
        Args:
            identifier: Single ID to resolve
            idtype: ID type hint (or auto-detect)
            
        Returns:
            Dictionary with all available ID formats
        """
        result = await self.convert_ids([identifier], idtype=idtype)
        
        if result["conversions"]:
            return result["conversions"][0]
        elif result["failed"]:
            error = result["failed"][0]
            raise InvalidIDError(
                message=f"Cannot resolve ID: {error.get('error', 'Unknown error')}",
                identifier=identifier
            )
        else:
            raise InvalidIDError(
                message="ID not found",
                identifier=identifier
            )
    
    @staticmethod
    def detect_id_type(identifier: str) -> str:
        """
        Detect the type of an identifier.
        
        Args:
            identifier: ID string to analyze
            
        Returns:
            Detected ID type (pmid, pmcid, doi, mid, or unknown)
        """
        identifier = identifier.strip()
        
        # PMCID: starts with "PMC" followed by digits
        if identifier.upper().startswith("PMC") and identifier[3:].isdigit():
            return "pmcid"
        
        # DOI: starts with "10." and contains "/"
        if identifier.startswith("10.") and "/" in identifier:
            return "doi"
        
        # Manuscript ID: starts with "NIHMS" or "MID"
        if identifier.upper().startswith("NIHMS") or identifier.upper().startswith("MID"):
            return "mid"
        
        # PMID: all digits
        if identifier.isdigit():
            return "pmid"
        
        return "unknown"
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
