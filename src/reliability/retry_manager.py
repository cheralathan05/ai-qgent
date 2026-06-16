"""
Retry Manager with Exponential Backoff
Handles intelligent retries with configurable strategies
"""

import asyncio
import logging
import time
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import random

from reliability.failure_classifier import FailureClassifier, FailureType

logger = logging.getLogger(__name__)


class BackoffStrategy(str, Enum):
    """Backoff strategies for retries"""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    RANDOM = "random"


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_retries: int = 3
    initial_delay_ms: int = 100
    max_delay_ms: int = 30000
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: bool = True
    retry_on_transient_only: bool = True


class RetryManager:
    """Manages retries with exponential backoff"""
    
    # Default configurations for different scenarios
    CONFIGS = {
        "network": RetryConfig(max_retries=5, initial_delay_ms=100, max_delay_ms=10000),
        "device": RetryConfig(max_retries=4, initial_delay_ms=500, max_delay_ms=15000),
        "adb": RetryConfig(max_retries=3, initial_delay_ms=200, max_delay_ms=5000),
        "timeout": RetryConfig(max_retries=2, initial_delay_ms=1000, max_delay_ms=20000),
        "ollama": RetryConfig(max_retries=5, initial_delay_ms=2000, max_delay_ms=30000),
    }
    
    def __init__(self):
        self.attempt_count: Dict[str, int] = {}
        self.last_error: Dict[str, Exception] = {}
    
    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        config: Optional[RetryConfig] = None,
        operation_id: Optional[str] = None,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Async function to execute
            config: Retry configuration (defaults to exponential backoff)
            operation_id: Unique operation identifier for tracking
            on_retry: Callback when retry happens
            
        Returns:
            Result from function execution
            
        Raises:
            Exception: If all retries exhausted
        """
        config = config or RetryConfig()
        attempt = 0
        
        while attempt <= config.max_retries:
            try:
                logger.debug(f"Executing (attempt {attempt + 1}/{config.max_retries + 1})")
                result = await func(*args, **kwargs)
                
                # Reset on success
                if operation_id:
                    self.attempt_count[operation_id] = 0
                
                return result
            
            except Exception as e:
                attempt += 1
                
                # Classify failure
                failure_info = FailureClassifier.classify(e)
                
                # Don't retry permanent failures
                if not failure_info.is_recoverable and config.retry_on_transient_only:
                    logger.error(f"Permanent failure, not retrying: {failure_info.message}")
                    raise
                
                # No more retries
                if attempt > config.max_retries:
                    logger.error(f"Max retries exhausted ({config.max_retries})")
                    raise
                
                # Calculate backoff delay
                delay_ms = self._calculate_backoff(
                    attempt - 1,
                    config.initial_delay_ms,
                    config.max_delay_ms,
                    config.backoff_strategy,
                    config.jitter
                )
                
                logger.warning(
                    f"Retry {attempt}/{config.max_retries} after {delay_ms}ms - "
                    f"Failure: {failure_info.failure_type.value}"
                )
                
                # Call retry callback
                if on_retry:
                    on_retry(attempt, e)
                
                # Wait before retry
                await asyncio.sleep(delay_ms / 1000.0)
    
    @staticmethod
    def _calculate_backoff(
        attempt: int,
        initial_ms: int,
        max_ms: int,
        strategy: BackoffStrategy,
        jitter: bool = True
    ) -> int:
        """Calculate backoff delay based on strategy"""
        
        if strategy == BackoffStrategy.LINEAR:
            delay = initial_ms * (attempt + 1)
        
        elif strategy == BackoffStrategy.EXPONENTIAL:
            delay = initial_ms * (2 ** attempt)
        
        elif strategy == BackoffStrategy.FIBONACCI:
            fib = RetryManager._fibonacci(attempt + 1)
            delay = initial_ms * fib
        
        elif strategy == BackoffStrategy.RANDOM:
            delay = random.randint(initial_ms, max_ms)
        
        else:
            delay = initial_ms
        
        # Add jitter (randomize by ±10%)
        if jitter and strategy != BackoffStrategy.RANDOM:
            jitter_amount = delay * 0.1
            delay = int(delay + random.uniform(-jitter_amount, jitter_amount))
        
        # Cap at maximum
        delay = min(delay, max_ms)
        
        return delay
    
    @staticmethod
    def _fibonacci(n: int) -> int:
        """Get nth Fibonacci number"""
        if n <= 1:
            return 1
        a, b = 1, 1
        for _ in range(n - 1):
            a, b = b, a + b
        return a
    
    @staticmethod
    def get_config_for_failure(failure_type: FailureType) -> RetryConfig:
        """Get recommended retry config for failure type"""
        config_map = {
            FailureType.NETWORK_FAILURE: RetryManager.CONFIGS["network"],
            FailureType.DEVICE_DISCONNECTED: RetryManager.CONFIGS["device"],
            FailureType.ADB_FAILURE: RetryManager.CONFIGS["adb"],
            FailureType.WORKFLOW_TIMEOUT: RetryManager.CONFIGS["timeout"],
            FailureType.OLLAMA_UNAVAILABLE: RetryManager.CONFIGS["ollama"],
        }
        return config_map.get(failure_type, RetryConfig())


# Sync wrapper for non-async contexts
class SyncRetryManager:
    """Synchronous version of retry manager"""
    
    def __init__(self):
        self.async_manager = RetryManager()
    
    def execute_with_retry(
        self,
        func: Callable,
        *args,
        config: Optional[RetryConfig] = None,
        operation_id: Optional[str] = None,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        **kwargs
    ) -> Any:
        """Synchronous retry execution"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.async_manager.execute_with_retry(
                func, *args,
                config=config,
                operation_id=operation_id,
                on_retry=on_retry,
                **kwargs
            )
        )


# Global instances
retry_manager = RetryManager()
sync_retry_manager = SyncRetryManager()


def get_retry_manager() -> RetryManager:
    """Get global retry manager"""
    return retry_manager
