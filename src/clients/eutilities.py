"""
NCBI E-Utilities client for PubMed MCP Server.

Provides methods for all E-utilities endpoints:
- ESearch: Text-based database search
- ESummary: Document metadata retrieval
- EFetch: Full record download
- EPost: Batch UID upload
- ELink: Cross-database linking
- EGQuery: Global multi-database search
- ESpell: Query spelling correction
"""

import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import logging
import json

from .base import BaseClient
from ..config import Config
from ..utils.error_handler import InvalidQueryError, ArticleNotFoundError

logger = logging.getLogger(__name__)


class EUtilitiesClient(BaseClient):
    """
    Client for NCBI E-Utilities API.
    
    Base URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize E-Utilities client."""
        super().__init__(
            base_url=Config.EUTILITIES_BASE_URL,
            api_key=api_key,
            timeout=Config.REQUEST_TIMEOUT
        )
    
    async def search(
        self,
        db: str,
        query: str,
        retmax: int = 50,
        retstart: int = 0,
        sort: str = "relevance",
        usehistory: bool = False,
        rettype: str = "json",
        datetype: Optional[str] = None,
        mindate: Optional[str] = None,
        maxdate: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search a database using ESearch.
        
        Args:
            db: Database to search (pubmed, pmc, etc.)
            query: Search query in E-utilities syntax
            retmax: Maximum number of IDs to return (max 10000)
            retstart: Starting index for pagination
            sort: Sort order (relevance, pub_date, etc.)
            usehistory: Store results on History server
            rettype: Return type (json or xml)
            datetype: Date type for filtering (pdat, edat)
            mindate: Minimum date (YYYY/MM/DD or YYYY)
            maxdate: Maximum date (YYYY/MM/DD or YYYY)
            
        Returns:
            Dictionary with search results including:
            - count: Total results
            - ids: List of IDs
            - query_key: History key (if usehistory)
            - web_env: History WebEnv (if usehistory)
            - query_translation: How NCBI interpreted the query
        """
        params = {
            "db": db,
            "term": query,
            "retmax": min(retmax, Config.MAX_SEARCH_RESULTS),
            "retstart": retstart,
            "sort": sort,
            "usehistory": usehistory,
            "retmode": rettype,
        }
        
        if datetype:
            params["datetype"] = datetype
        if mindate:
            params["mindate"] = mindate
        if maxdate:
            params["maxdate"] = maxdate
        
        response = await self.get("esearch.fcgi", **params)
        
        if rettype == "json":
            return self._parse_esearch_json(response.text)
        else:
            return self._parse_esearch_xml(response.text)
    
    def _parse_esearch_json(self, response_text: str) -> Dict[str, Any]:
        """Parse ESearch JSON response."""
        try:
            data = json.loads(response_text)
            result = data.get("esearchresult", {})
            
            return {
                "count": int(result.get("count", 0)),
                "ids": result.get("idlist", []),
                "query_key": result.get("querykey"),
                "web_env": result.get("webenv"),
                "query_translation": result.get("querytranslation", ""),
                "ret_max": int(result.get("retmax", 0)),
                "ret_start": int(result.get("retstart", 0)),
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ESearch JSON: {e}")
            raise InvalidQueryError(
                message="Failed to parse search results",
                details=str(e)
            )
    
    def _parse_esearch_xml(self, response_text: str) -> Dict[str, Any]:
        """Parse ESearch XML response."""
        try:
            root = ET.fromstring(response_text)
            
            # Check for errors
            error = root.find(".//ERROR")
            if error is not None:
                raise InvalidQueryError(
                    message="Search error",
                    details=error.text
                )
            
            return {
                "count": int(root.findtext("Count", "0")),
                "ids": [id_elem.text for id_elem in root.findall(".//IdList/Id")],
                "query_key": root.findtext("QueryKey"),
                "web_env": root.findtext("WebEnv"),
                "query_translation": root.findtext("QueryTranslation", ""),
                "ret_max": int(root.findtext("RetMax", "0")),
                "ret_start": int(root.findtext("RetStart", "0")),
            }
        except ET.ParseError as e:
            logger.error(f"Failed to parse ESearch XML: {e}")
            raise InvalidQueryError(
                message="Failed to parse search results",
                details=str(e)
            )
    
    async def summary(
        self,
        db: str,
        ids: List[str],
        version: str = "2.0",
        retmode: str = "json"
    ) -> Dict[str, Any]:
        """
        Get document summaries using ESummary.
        
        Args:
            db: Database (pubmed, pmc, etc.)
            ids: List of IDs to retrieve summaries for
            version: ESummary version (1.0 or 2.0)
            retmode: Return mode (json or xml)
            
        Returns:
            Dictionary mapping IDs to summary objects
        """
        if not ids:
            return {"results": []}
        
        ids_str = ",".join(str(id) for id in ids)
        
        response = await self.get(
            "esummary.fcgi",
            db=db,
            id=ids_str,
            version=version,
            retmode=retmode
        )
        
        if retmode == "json":
            return self._parse_esummary_json(response.text)
        else:
            return self._parse_esummary_xml(response.text, db)
    
    def _parse_esummary_json(self, response_text: str) -> Dict[str, Any]:
        """Parse ESummary JSON response."""
        try:
            data = json.loads(response_text)
            result = data.get("result", {})
            
            # Remove the "uids" key and return article data
            uids = result.pop("uids", [])
            
            articles = []
            for uid in uids:
                if uid in result:
                    article = result[uid]
                    article["uid"] = uid
                    articles.append(article)
            
            return {"results": articles, "uids": uids}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ESummary JSON: {e}")
            return {"results": [], "error": str(e)}
    
    def _parse_esummary_xml(self, response_text: str, db: str) -> Dict[str, Any]:
        """Parse ESummary XML response."""
        try:
            root = ET.fromstring(response_text)
            articles = []
            
            for doc_sum in root.findall(".//DocumentSummary") or root.findall(".//DocSum"):
                article = {}
                
                # Get UID
                uid = doc_sum.get("uid") or doc_sum.findtext("Id")
                article["uid"] = uid
                
                # Parse items
                for item in doc_sum.findall("Item"):
                    name = item.get("Name")
                    item_type = item.get("Type", "String")
                    
                    if item_type == "List":
                        article[name] = [
                            sub.text for sub in item.findall("Item") if sub.text
                        ]
                    else:
                        article[name] = item.text
                
                articles.append(article)
            
            return {"results": articles}
        except ET.ParseError as e:
            logger.error(f"Failed to parse ESummary XML: {e}")
            return {"results": [], "error": str(e)}
    
    async def fetch(
        self,
        db: str,
        ids: Optional[List[str]] = None,
        rettype: str = "abstract",
        retmode: str = "xml",
        query_key: Optional[str] = None,
        web_env: Optional[str] = None,
        retmax: int = 500,
        retstart: int = 0
    ) -> str:
        """
        Fetch full records using EFetch.
        
        Args:
            db: Database (pubmed, pmc, etc.)
            ids: List of IDs to fetch (or use query_key/web_env)
            rettype: Return type (abstract, full, medline, etc.)
            retmode: Return mode (xml, text)
            query_key: History query key
            web_env: History WebEnv
            retmax: Maximum records to return
            retstart: Starting index
            
        Returns:
            Raw response text (XML or text format)
        """
        params = {
            "db": db,
            "rettype": rettype,
            "retmode": retmode,
            "retmax": retmax,
            "retstart": retstart,
        }
        
        if ids:
            params["id"] = ",".join(str(id) for id in ids)
        elif query_key and web_env:
            params["query_key"] = query_key
            params["WebEnv"] = web_env
        else:
            raise ValueError("Either ids or query_key/web_env must be provided")
        
        response = await self.get("efetch.fcgi", **params)
        return response.text
    
    async def post(
        self,
        db: str,
        ids: List[str],
        web_env: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload IDs to History server using EPost.
        
        Args:
            db: Database (pubmed, pmc, etc.)
            ids: List of IDs to upload
            web_env: Existing WebEnv to add to (for chaining)
            
        Returns:
            Dictionary with query_key and web_env
        """
        data = {
            "db": db,
            "id": ",".join(str(id) for id in ids),
        }
        
        if web_env:
            data["WebEnv"] = web_env
        
        response = await super().post("epost.fcgi", data=data)
        
        # Parse XML response
        root = ET.fromstring(response.text)
        
        return {
            "query_key": root.findtext("QueryKey"),
            "web_env": root.findtext("WebEnv"),
        }
    
    async def link(
        self,
        dbfrom: str,
        db: str,
        ids: Optional[List[str]] = None,
        cmd: str = "neighbor",
        linkname: Optional[str] = None,
        query_key: Optional[str] = None,
        web_env: Optional[str] = None,
        retmode: str = "json"
    ) -> Dict[str, Any]:
        """
        Find related records using ELink.
        
        Args:
            dbfrom: Source database
            db: Target database
            ids: Source IDs
            cmd: Link command (neighbor, neighbor_history, prlinks, etc.)
            linkname: Specific link name
            query_key: History query key
            web_env: History WebEnv
            retmode: Return mode (json or xml)
            
        Returns:
            Dictionary with linked IDs
        """
        params = {
            "dbfrom": dbfrom,
            "db": db,
            "cmd": cmd,
            "retmode": retmode,
        }
        
        if ids:
            params["id"] = ",".join(str(id) for id in ids)
        elif query_key and web_env:
            params["query_key"] = query_key
            params["WebEnv"] = web_env
        
        if linkname:
            params["linkname"] = linkname
        
        response = await self.get("elink.fcgi", **params)
        
        if retmode == "json":
            return self._parse_elink_json(response.text)
        else:
            return self._parse_elink_xml(response.text)
    
    def _parse_elink_json(self, response_text: str) -> Dict[str, Any]:
        """Parse ELink JSON response."""
        try:
            data = json.loads(response_text)
            linksets = data.get("linksets", [])
            
            results = []
            for linkset in linksets:
                for link_db in linkset.get("linksetdbs", []):
                    results.append({
                        "db_to": link_db.get("dbto"),
                        "link_name": link_db.get("linkname"),
                        "ids": link_db.get("links", [])
                    })
            
            return {"linksets": results}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse ELink JSON: {e}")
            return {"linksets": [], "error": str(e)}
    
    def _parse_elink_xml(self, response_text: str) -> Dict[str, Any]:
        """Parse ELink XML response."""
        try:
            root = ET.fromstring(response_text)
            results = []
            
            for linkset_db in root.findall(".//LinkSetDb"):
                db_to = linkset_db.findtext("DbTo")
                link_name = linkset_db.findtext("LinkName")
                ids = [
                    link.findtext("Id") for link in linkset_db.findall(".//Link")
                ]
                
                results.append({
                    "db_to": db_to,
                    "link_name": link_name,
                    "ids": ids
                })
            
            return {"linksets": results}
        except ET.ParseError as e:
            logger.error(f"Failed to parse ELink XML: {e}")
            return {"linksets": [], "error": str(e)}
    
    async def gquery(self, term: str) -> Dict[str, Any]:
        """
        Search all databases using EGQuery.
        
        Args:
            term: Search query
            
        Returns:
            Dictionary with hit counts per database
        """
        response = await self.get("egquery.fcgi", term=term, retmode="xml")
        
        return self._parse_egquery_xml(response.text)
    
    def _parse_egquery_xml(self, response_text: str) -> Dict[str, Any]:
        """Parse EGQuery XML response."""
        try:
            root = ET.fromstring(response_text)
            databases = []
            
            for result in root.findall(".//ResultItem"):
                db_name = result.findtext("DbName")
                menu_name = result.findtext("MenuName")
                count = result.findtext("Count", "0")
                status = result.findtext("Status", "Ok")
                
                databases.append({
                    "db_name": db_name,
                    "menu_name": menu_name,
                    "count": int(count) if count else 0,
                    "status": status
                })
            
            return {"databases": databases}
        except ET.ParseError as e:
            logger.error(f"Failed to parse EGQuery XML: {e}")
            return {"databases": [], "error": str(e)}
    
    async def spell(self, db: str, term: str) -> Dict[str, Any]:
        """
        Get spelling suggestions using ESpell.
        
        Args:
            db: Database
            term: Query to check
            
        Returns:
            Dictionary with corrected query and suggestions
        """
        response = await self.get("espell.fcgi", db=db, term=term)
        
        return self._parse_espell_xml(response.text)
    
    def _parse_espell_xml(self, response_text: str) -> Dict[str, Any]:
        """Parse ESpell XML response."""
        try:
            root = ET.fromstring(response_text)
            
            return {
                "original_query": root.findtext(".//Query", ""),
                "corrected_query": root.findtext(".//CorrectedQuery", ""),
                "replaced_terms": [
                    term.text for term in root.findall(".//ReplacedQuery")
                ]
            }
        except ET.ParseError as e:
            logger.error(f"Failed to parse ESpell XML: {e}")
            return {"error": str(e)}
    
    async def citmatch(
        self,
        db: str,
        bdata: str,
        retmode: str = "xml"
    ) -> Dict[str, Any]:
        """
        Match citation strings using ECitMatch.
        
        Args:
            db: Database (usually pubmed)
            bdata: Citation data in pipe-delimited format
            retmode: Return mode
            
        Returns:
            Dictionary with matched PMIDs
        """
        response = await super().post(
            "ecitmatch.cgi",
            data={"db": db, "bdata": bdata, "retmode": retmode}
        )
        
        # ECitMatch returns a simple text format
        matches = []
        for line in response.text.strip().split("\n"):
            parts = line.split("|")
            if len(parts) >= 6:
                matches.append({
                    "journal": parts[0],
                    "year": parts[1],
                    "volume": parts[2],
                    "first_page": parts[3],
                    "author": parts[4],
                    "pmid": parts[5] if parts[5] != "NOT_FOUND" else None
                })
        
        return {"matches": matches}
