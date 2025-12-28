"""
Base HTTP client for all NCBI API interactions.

Provides common functionality for request handling, logging, and error management.
"""

import httpx
from typing import Optional, Dict, Any
import logging
from urllib.parse import urlencode

from ..config import Config
from ..utils.rate_limiter import RateLimiter, RetryHandler
from ..utils.error_handler import (
    PubMedError,
    RateLimitError,
    ServiceUnavailableError,
    NetworkError,
    map_http_status_to_error,
)

logger = logging.getLogger(__name__)


class BaseClient:
    """
    Base HTTP client with rate limiting and retry logic.
    
    All API clients should inherit from this class.
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the base client.
        
        Args:
            base_url: Base URL for API requests
            api_key: Optional NCBI API key for higher rate limits
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or Config.NCBI_API_KEY
        self.timeout = timeout
        
        # Initialize rate limiter based on API key presence
        rate_limit = 10 if self.api_key else 3
        self.rate_limiter = RateLimiter(max_requests=rate_limit, window=1.0)
        
        # Initialize retry handler
        self.retry_handler = RetryHandler(
            max_retries=Config.MAX_RETRIES,
            base_delay=1.0,
            backoff_factor=Config.RETRY_BACKOFF_FACTOR
        )
        
        # HTTP client configuration
        self._client: Optional[httpx.AsyncClient] = None
        
        logger.info(f"BaseClient initialized for {base_url} (rate limit: {rate_limit}/sec)")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                headers=self._get_default_headers(),
                follow_redirects=True
            )
        return self._client
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for all requests."""
        return {
            "User-Agent": f"{Config.TOOL_NAME}/1.0 (mailto:{Config.TOOL_EMAIL})",
            "Accept": "application/xml, application/json, text/xml",
        }
    
    def _build_params(self, **kwargs) -> Dict[str, str]:
        """
        Build query parameters with common fields.
        
        Automatically adds tool, email, and api_key if available.
        """
        params = {
            "tool": Config.TOOL_NAME,
            "email": Config.TOOL_EMAIL,
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        # Add provided parameters, filtering out None values
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, bool):
                    params[key] = "y" if value else "n"
                elif isinstance(value, list):
                    params[key] = ",".join(str(v) for v in value)
                else:
                    params[key] = str(value)
        
        return params
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        retry_on_rate_limit: bool = True
    ) -> httpx.Response:
        """
        Make an HTTP request with rate limiting and retries.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (appended to base_url)
            params: Query parameters
            data: POST data
            retry_on_rate_limit: Whether to retry on 429 errors
            
        Returns:
            httpx.Response object
            
        Raises:
            PubMedError: For API errors
            NetworkError: For network issues
        """
        url = f"{self.base_url}/{endpoint}"
        client = await self._get_client()
        
        for attempt in range(self.retry_handler.max_retries + 1):
            try:
                # Apply rate limiting before request
                await self.rate_limiter.acquire()
                
                logger.debug(f"Request: {method} {url} (attempt {attempt + 1})")
                
                if method.upper() == "GET":
                    response = await client.get(url, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, params=params, data=data)
                else:
                    response = await client.request(method, url, params=params, data=data)
                
                # Check for rate limit response
                if response.status_code == 429:
                    if retry_on_rate_limit and attempt < self.retry_handler.max_retries:
                        await self.retry_handler.wait(attempt)
                        continue
                    raise RateLimitError(
                        message="Rate limit exceeded after retries",
                        retry_after=float(response.headers.get("Retry-After", 60))
                    )
                
                # Check for server errors that warrant retry
                if response.status_code >= 500:
                    if attempt < self.retry_handler.max_retries:
                        await self.retry_handler.wait(attempt)
                        continue
                    raise ServiceUnavailableError(
                        message=f"Server error: {response.status_code}",
                        retry_after=60.0
                    )
                
                # Check for client errors
                if response.status_code >= 400:
                    raise map_http_status_to_error(
                        response.status_code,
                        response.text[:500]  # Truncate long error messages
                    )
                
                logger.debug(f"Response: {response.status_code} ({len(response.text)} bytes)")
                return response
                
            except httpx.TimeoutException as e:
                if attempt < self.retry_handler.max_retries:
                    await self.retry_handler.wait(attempt)
                    continue
                raise NetworkError(
                    message="Request timed out",
                    original_error=str(e)
                )
            
            except httpx.RequestError as e:
                if attempt < self.retry_handler.max_retries:
                    await self.retry_handler.wait(attempt)
                    continue
                raise NetworkError(
                    message="Network request failed",
                    original_error=str(e)
                )
        
        # Should not reach here, but just in case
        raise PubMedError("Max retries exceeded")
    
    async def get(
        self,
        endpoint: str,
        **params
    ) -> httpx.Response:
        """Make a GET request."""
        full_params = self._build_params(**params)
        return await self._request("GET", endpoint, params=full_params)
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        **params
    ) -> httpx.Response:
        """Make a POST request."""
        full_params = self._build_params(**params)
        return await self._request("POST", endpoint, params=full_params, data=data)
    
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
