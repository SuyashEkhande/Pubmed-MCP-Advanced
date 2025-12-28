"""
Custom exception hierarchy for PubMed MCP Server.

Provides user-friendly error messages and HTTP status code mapping.
"""

from typing import Optional


class PubMedError(Exception):
    """Base exception for all PubMed MCP Server errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)
    
    def to_dict(self) -> dict:
        """Convert error to dictionary for MCP response."""
        result = {"error": self.__class__.__name__, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


class RateLimitError(PubMedError):
    """
    Rate limit exceeded - NCBI returned 429.
    
    Indicates the client should retry with exponential backoff.
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None
    ):
        super().__init__(message)
        self.retry_after = retry_after
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.retry_after:
            result["retry_after_seconds"] = self.retry_after
        return result


class InvalidQueryError(PubMedError):
    """
    Query syntax error - malformed E-utilities query.
    
    Provides suggestions for correcting the query.
    """
    
    def __init__(
        self,
        message: str = "Invalid query syntax",
        query: Optional[str] = None,
        suggestion: Optional[str] = None
    ):
        super().__init__(message)
        self.query = query
        self.suggestion = suggestion
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.query:
            result["query"] = self.query
        if self.suggestion:
            result["suggestion"] = self.suggestion
        return result


class ArticleNotFoundError(PubMedError):
    """
    Article not found - PMID/PMCID doesn't exist.
    """
    
    def __init__(
        self,
        message: str = "Article not found",
        identifier: Optional[str] = None,
        id_type: Optional[str] = None
    ):
        super().__init__(message)
        self.identifier = identifier
        self.id_type = id_type
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.identifier:
            result["identifier"] = self.identifier
        if self.id_type:
            result["id_type"] = self.id_type
        return result


class ServiceUnavailableError(PubMedError):
    """
    NCBI service unavailable - temporary outage.
    
    Client should retry after the suggested delay.
    """
    
    def __init__(
        self,
        message: str = "NCBI service temporarily unavailable",
        retry_after: Optional[float] = 60.0
    ):
        super().__init__(message)
        self.retry_after = retry_after
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.retry_after:
            result["retry_after_seconds"] = self.retry_after
        return result


class InvalidIDError(PubMedError):
    """
    Invalid identifier format.
    
    The provided ID doesn't match expected format for PMID/PMCID/DOI/MID.
    """
    
    def __init__(
        self,
        message: str = "Invalid identifier format",
        identifier: Optional[str] = None,
        expected_format: Optional[str] = None
    ):
        super().__init__(message)
        self.identifier = identifier
        self.expected_format = expected_format
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.identifier:
            result["identifier"] = self.identifier
        if self.expected_format:
            result["expected_format"] = self.expected_format
        return result


class BatchSizeError(PubMedError):
    """
    Batch size exceeded maximum allowed.
    """
    
    def __init__(
        self,
        message: str = "Batch size too large",
        requested_size: Optional[int] = None,
        max_size: Optional[int] = None
    ):
        super().__init__(message)
        self.requested_size = requested_size
        self.max_size = max_size
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.requested_size:
            result["requested_size"] = self.requested_size
        if self.max_size:
            result["max_size"] = self.max_size
        return result


class NetworkError(PubMedError):
    """
    Network connectivity error.
    """
    
    def __init__(
        self,
        message: str = "Network error occurred",
        original_error: Optional[str] = None
    ):
        super().__init__(message)
        self.original_error = original_error
    
    def to_dict(self) -> dict:
        result = super().to_dict()
        if self.original_error:
            result["original_error"] = self.original_error
        return result


def map_http_status_to_error(
    status_code: int,
    response_text: Optional[str] = None
) -> PubMedError:
    """
    Map HTTP status codes to appropriate PubMedError subclasses.
    
    Args:
        status_code: HTTP status code
        response_text: Optional response body for additional context
        
    Returns:
        Appropriate PubMedError subclass instance
    """
    error_mapping = {
        400: InvalidQueryError(
            message="Bad request - check query syntax",
            details=response_text
        ),
        401: PubMedError(
            message="Authentication error - check API key",
            details=response_text
        ),
        404: ArticleNotFoundError(
            message="Resource not found",
            details=response_text
        ),
        429: RateLimitError(
            message="Rate limit exceeded - retry with backoff",
            retry_after=60.0
        ),
        500: ServiceUnavailableError(
            message="NCBI internal server error",
            retry_after=60.0
        ),
        502: ServiceUnavailableError(
            message="NCBI gateway error",
            retry_after=30.0
        ),
        503: ServiceUnavailableError(
            message="NCBI service temporarily unavailable",
            retry_after=60.0
        ),
        504: ServiceUnavailableError(
            message="NCBI gateway timeout",
            retry_after=30.0
        ),
    }
    
    return error_mapping.get(
        status_code,
        PubMedError(
            message=f"HTTP error {status_code}",
            details=response_text
        )
    )
