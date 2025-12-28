"""
Configuration management for PubMed MCP Server.

Handles environment variables, API endpoints, and rate limiting settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Central configuration for PubMed MCP Server."""
    
    # NCBI API Key (optional but recommended for 10 req/sec vs 3 req/sec)
    NCBI_API_KEY: Optional[str] = os.getenv("NCBI_API_KEY")
    
    # Tool identification (required by NCBI)
    TOOL_NAME: str = os.getenv("TOOL_NAME", "pubmed-mcp-server")
    TOOL_EMAIL: str = os.getenv("TOOL_EMAIL", "pubmed-mcp@example.com")
    
    # Rate limiting
    MAX_REQUESTS_PER_SEC_WITH_KEY: int = 10
    MAX_REQUESTS_PER_SEC_WITHOUT_KEY: int = 3
    
    @classmethod
    def get_rate_limit(cls) -> int:
        """Get the appropriate rate limit based on API key presence."""
        return cls.MAX_REQUESTS_PER_SEC_WITH_KEY if cls.NCBI_API_KEY else cls.MAX_REQUESTS_PER_SEC_WITHOUT_KEY
    
    # API Base URLs
    EUTILITIES_BASE_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    BIOC_PUBMED_BASE_URL: str = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"
    BIOC_PMC_BASE_URL: str = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"
    ID_CONVERTER_BASE_URL: str = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"
    
    # Request settings
    REQUEST_TIMEOUT: int = 60  # seconds
    MAX_RETRIES: int = 3
    RETRY_BACKOFF_FACTOR: float = 1.5
    
    # Batch processing settings
    DEFAULT_BATCH_SIZE: int = 100
    MAX_BATCH_SIZE: int = 500  # NCBI limits
    MAX_IDS_PER_ID_CONVERTER_REQUEST: int = 200
    
    # Default search settings
    DEFAULT_MAX_RESULTS: int = 50
    MAX_SEARCH_RESULTS: int = 10000


# Export config instance
config = Config()
