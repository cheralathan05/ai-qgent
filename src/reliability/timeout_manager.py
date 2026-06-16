"""
Timeout Manager
Prevents workflows from hanging indefinitely
"""

import asyncio
import logging
from typing import Callable, Any, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class TimeoutConfig:
    """Configuration for timeout behavior"""
    default_timeout_seconds: int = 30
    intent_detection_timeout: int = 5
    planning_timeout: int = 10
    execution_timeout: int = 60
    verification_timeout: int = 15
    agent_call_timeout: int = 30
    adb_call_timeout: int = 20


class TimeoutManager:
    """Manages timeouts across the system"""
    
    def __init__(self, config: Optional[TimeoutConfig] = None):
        self.config = config or TimeoutConfig()
        self.active_timeouts: Dict[str, asyncio.Task] = {}
    
    async def execute_with_timeout(
        self,
        func: Callable,
        timeout_seconds: int,
        operation_id: Optional[str] = None,
        on_timeout: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with timeout
        
        Args:
            func: Async function to execute
            timeout_seconds: Timeout in seconds
            operation_id: Unique operation ID for tracking
            on_timeout: Callback when timeout occurs
            
        Returns:
            Result from function
            
        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        try:
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout_seconds
            )
            
            if operation_id and operation_id in self.active_timeouts:
                del self.active_timeouts[operation_id]
            
            return result
        
        except asyncio.TimeoutError:
            logger.error(
                f"Operation '{operation_id}' exceeded timeout of {timeout_seconds}s"
            )
            
            if on_timeout:
                try:
                    await on_timeout(operation_id)
                except Exception as e:
                    logger.error(f"Error in timeout callback: {e}")
            
            raise
    
    async def execute_intent_detection(self, func: Callable, *args, **kwargs) -> Any:
        """Execute intent detection with standard timeout"""
        return await self.execute_with_timeout(
            func,
            self.config.intent_detection_timeout,
            "intent_detection",
            *args,
            **kwargs
        )
    
    async def execute_planning(self, func: Callable, *args, **kwargs) -> Any:
        """Execute planning with standard timeout"""
        return await self.execute_with_timeout(
            func,
            self.config.planning_timeout,
            "planning",
            *args,
            **kwargs
        )
    
    async def execute_execution(self, func: Callable, *args, **kwargs) -> Any:
        """Execute execution with standard timeout"""
        return await self.execute_with_timeout(
            func,
            self.config.execution_timeout,
            "execution",
            *args,
            **kwargs
        )
    
    async def execute_verification(self, func: Callable, *args, **kwargs) -> Any:
        """Execute verification with standard timeout"""
        return await self.execute_with_timeout(
            func,
            self.config.verification_timeout,
            "verification",
            *args,
            **kwargs
        )
    
    async def execute_agent_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute agent call with standard timeout"""
        return await self.execute_with_timeout(
            func,
            self.config.agent_call_timeout,
            "agent_call",
            *args,
            **kwargs
        )
    
    async def execute_adb_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute ADB call with standard timeout"""
        return await self.execute_with_timeout(
            func,
            self.config.adb_call_timeout,
            "adb_call",
            *args,
            **kwargs
        )
    
    def get_config(self) -> Dict[str, int]:
        """Get current timeout configuration"""
        return {
            "default_timeout": self.config.default_timeout_seconds,
            "intent_detection": self.config.intent_detection_timeout,
            "planning": self.config.planning_timeout,
            "execution": self.config.execution_timeout,
            "verification": self.config.verification_timeout,
            "agent_call": self.config.agent_call_timeout,
            "adb_call": self.config.adb_call_timeout,
        }
    
    def update_timeout(self, timeout_type: str, seconds: int) -> None:
        """Update a specific timeout"""
        if hasattr(self.config, timeout_type):
            setattr(self.config, timeout_type, seconds)
            logger.info(f"Updated {timeout_type} timeout to {seconds}s")


# Global instance
timeout_manager = TimeoutManager()


def get_timeout_manager() -> TimeoutManager:
    """Get global timeout manager"""
    return timeout_manager
