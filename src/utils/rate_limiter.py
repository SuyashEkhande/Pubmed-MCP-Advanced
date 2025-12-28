"""
Token bucket rate limiter for NCBI API compliance.

NCBI enforces strict rate limits:
- 3 requests/second without API key
- 10 requests/second with API key
- Violation = IP block for 24+ hours
"""

import asyncio
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter for NCBI API calls.
    
    This implementation uses a token bucket algorithm that:
    - Refills tokens at a constant rate
    - Allows bursting up to max_requests tokens
    - Blocks when no tokens are available
    """
    
    def __init__(self, max_requests: int = 3, window: float = 1.0):
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum requests per window (3 without API key, 10 with key)
            window: Time window in seconds (default 1.0 = per second)
        """
        self.max_requests = max_requests
        self.window = window
        self.tokens = float(max_requests)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
        
        logger.info(f"RateLimiter initialized: {max_requests} requests per {window}s")
    
    async def acquire(self) -> None:
        """
        Wait until a token is available, then consume it.
        
        This method is async and will block if rate limit is reached.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            
            # Refill tokens based on elapsed time
            self.tokens = min(
                self.max_requests,
                self.tokens + elapsed * (self.max_requests / self.window)
            )
            self.last_update = now
            
            if self.tokens < 1:
                # Calculate wait time until one token is available
                wait_time = (1 - self.tokens) * (self.window / self.max_requests)
                logger.debug(f"Rate limit reached, waiting {wait_time:.3f}s")
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1
            
            logger.debug(f"Token acquired, {self.tokens:.2f} tokens remaining")
    
    def update_limit(self, new_limit: int) -> None:
        """
        Update the rate limit (e.g., when API key is added).
        
        Args:
            new_limit: New maximum requests per window
        """
        self.max_requests = new_limit
        logger.info(f"Rate limit updated to {new_limit} requests per {self.window}s")
    
    @property
    def available_tokens(self) -> float:
        """Get the current number of available tokens."""
        now = time.monotonic()
        elapsed = now - self.last_update
        return min(
            self.max_requests,
            self.tokens + elapsed * (self.max_requests / self.window)
        )


class RetryHandler:
    """
    Handles retry logic with exponential backoff for rate limit errors.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0
    ):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            backoff_factor: Multiplier for each retry
            max_delay: Maximum delay between retries
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given retry attempt.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds before next retry
        """
        delay = self.base_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)
    
    async def wait(self, attempt: int) -> None:
        """
        Wait before the next retry attempt.
        
        Args:
            attempt: Current attempt number (0-indexed)
        """
        delay = self.get_delay(attempt)
        logger.info(f"Retry attempt {attempt + 1}/{self.max_retries}, waiting {delay:.1f}s")
        await asyncio.sleep(delay)
