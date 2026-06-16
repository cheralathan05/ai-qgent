"""
Circuit Breaker Pattern
Prevents cascading failures by stopping requests to failing services
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes before closing (from half-open)
    timeout_seconds: int = 60   # Time before trying to recover
    window_size: int = 10        # Failure count window


@dataclass
class CircuitMetrics:
    """Metrics for circuit breaker"""
    state: CircuitState = CircuitState.CLOSED
    failures: int = 0
    successes: int = 0
    total_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.utcnow)
    recovery_attempts: int = 0
    
    def reset(self) -> None:
        """Reset metrics"""
        self.failures = 0
        self.successes = 0
        self.total_calls = 0
        self.last_failure_time = None
        self.recovery_attempts = 0


class CircuitBreaker:
    """Circuit breaker for services"""
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.metrics = CircuitMetrics()
        self._lock = asyncio.Lock()
    
    async def call(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Async function to execute
            
        Returns:
            Result from function
            
        Raises:
            CircuitBreakerOpenException: If circuit is open
        """
        async with self._lock:
            # Check state and potentially transition
            self._check_state()
            
            if self.metrics.state == CircuitState.OPEN:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is OPEN"
                )
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        
        except Exception as e:
            self._record_failure()
            raise
    
    def _check_state(self) -> None:
        """Check and potentially transition circuit state"""
        
        if self.metrics.state == CircuitState.CLOSED:
            # Transition to open if threshold exceeded
            if self.metrics.failures >= self.config.failure_threshold:
                self._transition_to_open()
        
        elif self.metrics.state == CircuitState.OPEN:
            # Transition to half-open if timeout expired
            if self._timeout_exceeded():
                self._transition_to_half_open()
        
        elif self.metrics.state == CircuitState.HALF_OPEN:
            # Transition to closed or reopen
            if self.metrics.successes >= self.config.success_threshold:
                self._transition_to_closed()
            elif self.metrics.failures >= 1:
                self._transition_to_open()
    
    def _transition_to_open(self) -> None:
        """Transition to OPEN state"""
        self.metrics.state = CircuitState.OPEN
        self.metrics.last_state_change = datetime.utcnow()
        logger.warning(f"Circuit breaker '{self.name}' is now OPEN")
    
    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state"""
        self.metrics.state = CircuitState.HALF_OPEN
        self.metrics.last_state_change = datetime.utcnow()
        self.metrics.failures = 0
        self.metrics.successes = 0
        self.metrics.recovery_attempts += 1
        logger.warning(
            f"Circuit breaker '{self.name}' is now HALF_OPEN "
            f"(recovery attempt {self.metrics.recovery_attempts})"
        )
    
    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state"""
        self.metrics.state = CircuitState.CLOSED
        self.metrics.last_state_change = datetime.utcnow()
        self.metrics.reset()
        logger.info(f"Circuit breaker '{self.name}' is now CLOSED (recovered)")
    
    def _timeout_exceeded(self) -> bool:
        """Check if timeout exceeded"""
        if self.metrics.last_state_change is None:
            return False
        
        elapsed = datetime.utcnow() - self.metrics.last_state_change
        return elapsed >= timedelta(seconds=self.config.timeout_seconds)
    
    def _record_success(self) -> None:
        """Record successful call"""
        async def _async_record():
            async with self._lock:
                self.metrics.total_calls += 1
                if self.metrics.state == CircuitState.HALF_OPEN:
                    self.metrics.successes += 1
        
        try:
            asyncio.create_task(_async_record())
        except RuntimeError:
            # No running event loop
            pass
    
    def _record_failure(self) -> None:
        """Record failed call"""
        async def _async_record():
            async with self._lock:
                self.metrics.total_calls += 1
                self.metrics.failures += 1
                self.metrics.last_failure_time = datetime.utcnow()
        
        try:
            asyncio.create_task(_async_record())
        except RuntimeError:
            # No running event loop
            pass
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit status"""
        return {
            "name": self.name,
            "state": self.metrics.state.value,
            "failures": self.metrics.failures,
            "successes": self.metrics.successes,
            "total_calls": self.metrics.total_calls,
            "last_failure": self.metrics.last_failure_time,
            "last_state_change": self.metrics.last_state_change,
            "recovery_attempts": self.metrics.recovery_attempts,
        }
    
    def reset(self) -> None:
        """Manually reset circuit breaker"""
        self.metrics = CircuitMetrics()
        logger.info(f"Circuit breaker '{self.name}' manually reset")


class CircuitBreakerOpenException(Exception):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreakerRegistry:
    """Registry for all circuit breakers"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name, config)
        return self.breakers[name]
    
    def get_status_all(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {name: breaker.get_status() for name, breaker in self.breakers.items()}


# Global registry
circuit_breaker_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get or create circuit breaker"""
    return circuit_breaker_registry.get_or_create(name, config)
