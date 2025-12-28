"""
BioC API client for text mining format retrieval.

Provides access to:
- PubMed abstracts in BioC format
- PMC Open Access full-text articles in BioC format
"""

import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import logging
import httpx

from ..config import Config
from ..utils.error_handler import ArticleNotFoundError, PubMedError

logger = logging.getLogger(__name__)


class BioCClient:
    """
    Client for NCBI BioC APIs.
    
    BioC provides pre-parsed text for NLP/text mining with:
    - Passage-level segmentation (title, abstract, intro, results, etc.)
    - Sentence-level boundaries
    - Token-level annotations
    """
    
    # BioC API endpoints
    PUBMED_BIOC_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pubmed.cgi/BioC_xml"
    PMC_BIOC_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml"
    
    def __init__(self, timeout: int = 60):
        """
        Initialize BioC client.
        
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
    
    async def fetch_pubmed_bioc(
        self,
        pmid: str,
        format: str = "xml"
    ) -> Dict[str, Any]:
        """
        Fetch PubMed abstract in BioC format.
        
        Args:
            pmid: PubMed ID
            format: Output format (xml or json)
            
        Returns:
            BioC document with passages and annotations
        """
        client = await self._get_client()
        
        # Build URL based on format
        if format.lower() == "json":
            url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pubmed.cgi/BioC_json/{pmid}/unicode"
        else:
            url = f"{self.PUBMED_BIOC_URL}/{pmid}/unicode"
        
        try:
            response = await client.get(url)
            
            if response.status_code == 404:
                raise ArticleNotFoundError(
                    message=f"Article not found: PMID {pmid}",
                    identifier=pmid,
                    id_type="pmid"
                )
            
            response.raise_for_status()
            
            if format.lower() == "json":
                return self._parse_bioc_json(response.text, pmid)
            else:
                return self._parse_bioc_xml(response.text, pmid)
                
        except httpx.HTTPError as e:
            logger.error(f"BioC fetch error for PMID {pmid}: {e}")
            raise PubMedError(
                message=f"Failed to fetch BioC for PMID {pmid}",
                details=str(e)
            )
    
    async def fetch_pmc_bioc(
        self,
        pmcid: str,
        format: str = "xml"
    ) -> Dict[str, Any]:
        """
        Fetch PMC Open Access full-text in BioC format.
        
        Args:
            pmcid: PMC ID (with or without 'PMC' prefix)
            format: Output format (xml or json)
            
        Returns:
            BioC document with full-text passages
        """
        # Normalize PMCID format
        if not pmcid.upper().startswith("PMC"):
            pmcid = f"PMC{pmcid}"
        
        client = await self._get_client()
        
        # Build URL based on format
        if format.lower() == "json":
            url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmcid}/unicode"
        else:
            url = f"{self.PMC_BIOC_URL}/{pmcid}/unicode"
        
        try:
            response = await client.get(url)
            
            if response.status_code == 404:
                raise ArticleNotFoundError(
                    message=f"Article not found in PMC Open Access: {pmcid}",
                    identifier=pmcid,
                    id_type="pmcid"
                )
            
            response.raise_for_status()
            
            if format.lower() == "json":
                return self._parse_bioc_json(response.text, pmcid)
            else:
                return self._parse_bioc_xml(response.text, pmcid)
                
        except httpx.HTTPError as e:
            logger.error(f"BioC fetch error for {pmcid}: {e}")
            raise PubMedError(
                message=f"Failed to fetch BioC for {pmcid}",
                details=str(e)
            )
    
    def _parse_bioc_xml(self, xml_text: str, identifier: str) -> Dict[str, Any]:
        """
        Parse BioC XML response.
        
        Args:
            xml_text: Raw XML response
            identifier: Article identifier for error messages
            
        Returns:
            Structured BioC document
        """
        try:
            root = ET.fromstring(xml_text)
            
            # Get collection info
            source = root.findtext("source", "")
            date = root.findtext("date", "")
            
            documents = []
            for doc in root.findall(".//document"):
                doc_id = doc.findtext("id", "")
                
                passages = []
                for passage in doc.findall(".//passage"):
                    passage_data = {
                        "offset": int(passage.findtext("offset", "0")),
                        "text": passage.findtext("text", ""),
                        "infons": {}
                    }
                    
                    # Parse infons (metadata)
                    for infon in passage.findall("infon"):
                        key = infon.get("key", "")
                        passage_data["infons"][key] = infon.text
                    
                    # Parse sentences if available
                    sentences = []
                    for sentence in passage.findall(".//sentence"):
                        sent_data = {
                            "offset": int(sentence.findtext("offset", "0")),
                            "text": sentence.findtext("text", "")
                        }
                        sentences.append(sent_data)
                    
                    if sentences:
                        passage_data["sentences"] = sentences
                    
                    passages.append(passage_data)
                
                documents.append({
                    "id": doc_id,
                    "passages": passages
                })
            
            return {
                "source": source,
                "date": date,
                "documents": documents,
                "format": "bioc_xml",
                "identifier": identifier
            }
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse BioC XML: {e}")
            raise PubMedError(
                message="Failed to parse BioC XML response",
                details=str(e)
            )
    
    def _parse_bioc_json(self, json_text: str, identifier: str) -> Dict[str, Any]:
        """
        Parse BioC JSON response.
        
        Args:
            json_text: Raw JSON response
            identifier: Article identifier for error messages
            
        Returns:
            Structured BioC document
        """
        try:
            data = json.loads(json_text)
            
            # BioC API can return either a list or dict format
            if isinstance(data, list):
                # List format: extract documents from list
                documents = []
                for item in data:
                    if isinstance(item, dict):
                        if "documents" in item:
                            documents.extend(item.get("documents", []))
                        else:
                            documents.append(item)
                return {
                    "source": "BioC API",
                    "date": "",
                    "documents": documents,
                    "format": "bioc_json",
                    "identifier": identifier
                }
            else:
                # Dict format: standard BioC structure
                return {
                    "source": data.get("source", "") if isinstance(data, dict) else "",
                    "date": data.get("date", "") if isinstance(data, dict) else "",
                    "documents": data.get("documents", []) if isinstance(data, dict) else [],
                    "format": "bioc_json",
                    "identifier": identifier
                }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse BioC JSON: {e}")
            raise PubMedError(
                message="Failed to parse BioC JSON response",
                details=str(e)
            )
    
    def extract_text_from_bioc(self, bioc_doc: Dict[str, Any]) -> str:
        """
        Extract plain text from BioC document.
        
        Args:
            bioc_doc: Parsed BioC document
            
        Returns:
            Concatenated text from all passages
        """
        texts = []
        
        documents = bioc_doc.get("documents", [])
        if not isinstance(documents, list):
            documents = [documents] if documents else []
        
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            passages = doc.get("passages", [])
            if not isinstance(passages, list):
                passages = [passages] if passages else []
            
            for passage in passages:
                if not isinstance(passage, dict):
                    continue
                text = passage.get("text", "")
                if text:
                    texts.append(text)
        
        return "\n\n".join(texts)
    
    def extract_sections_from_bioc(self, bioc_doc: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Extract named sections from BioC document.
        
        Args:
            bioc_doc: Parsed BioC document
            
        Returns:
            List of section dictionaries with type and text
        """
        sections = []
        
        documents = bioc_doc.get("documents", [])
        if not isinstance(documents, list):
            documents = [documents] if documents else []
        
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            passages = doc.get("passages", [])
            if not isinstance(passages, list):
                passages = [passages] if passages else []
            
            for passage in passages:
                if not isinstance(passage, dict):
                    continue
                infons = passage.get("infons", {})
                if not isinstance(infons, dict):
                    infons = {}
                section_type = infons.get("section_type", infons.get("type", "unknown"))
                text = passage.get("text", "")
                
                if text:
                    sections.append({
                        "section_type": section_type,
                        "text": text
                    })
        
        return sections
    
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
