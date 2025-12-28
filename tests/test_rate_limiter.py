"""
Tests for rate limiter and utilities.
"""

import pytest
import asyncio
from src.utils.rate_limiter import RateLimiter, RetryHandler


class TestRateLimiter:
    """Tests for token bucket rate limiter."""
    
    @pytest.mark.asyncio
    async def test_initial_tokens(self):
        """Test rate limiter starts with full tokens."""
        limiter = RateLimiter(max_requests=10, window=1.0)
        assert limiter.available_tokens >= 9.9  # Allow small timing variance
    
    @pytest.mark.asyncio
    async def test_acquire_decrements_tokens(self):
        """Test acquiring a token decrements the count."""
        limiter = RateLimiter(max_requests=10, window=1.0)
        
        await limiter.acquire()
        tokens_after = limiter.available_tokens
        
        # Should have less tokens after acquire
        assert tokens_after < 10
    
    @pytest.mark.asyncio
    async def test_burst_within_limit(self):
        """Test burst requests within rate limit work."""
        limiter = RateLimiter(max_requests=5, window=1.0)
        
        # Should be able to make 5 quick requests
        for _ in range(5):
            await limiter.acquire()
    
    def test_update_limit(self):
        """Test updating rate limit."""
        limiter = RateLimiter(max_requests=3, window=1.0)
        assert limiter.max_requests == 3
        
        limiter.update_limit(10)
        assert limiter.max_requests == 10


class TestRetryHandler:
    """Tests for exponential backoff retry handler."""
    
    def test_exponential_backoff(self):
        """Test delay increases exponentially."""
        handler = RetryHandler(
            max_retries=5,
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=60.0
        )
        
        assert handler.get_delay(0) == 1.0  # 1 * 2^0
        assert handler.get_delay(1) == 2.0  # 1 * 2^1
        assert handler.get_delay(2) == 4.0  # 1 * 2^2
        assert handler.get_delay(3) == 8.0  # 1 * 2^3
    
    def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        handler = RetryHandler(
            max_retries=10,
            base_delay=1.0,
            backoff_factor=2.0,
            max_delay=30.0
        )
        
        # 2^10 = 1024, but should be capped at 30
        assert handler.get_delay(10) == 30.0
