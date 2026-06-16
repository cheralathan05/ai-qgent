"""
Application Configuration
Environment-based configuration for all components
"""

import os
from typing import Optional
from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse, unquote

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    user: str
    password: str
    database: str
    pool_size: int = 10
    
    @property
    def connection_string(self) -> str:
        return (
            f"postgresql://{quote_plus(self.user)}:{quote_plus(self.password)}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    @classmethod
    def from_uri(cls, uri: str):
        parsed = urlparse(uri)
        if parsed.scheme not in ("postgresql", "postgres"):
            raise ValueError(f"Unsupported database URI scheme: {parsed.scheme}")

        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=unquote(parsed.username or ""),
            password=unquote(parsed.password or ""),
            database=(parsed.path or "").lstrip("/"),
        )


@dataclass
class ADBConfig:
    """Android Debug Bridge configuration"""
    adb_path: str
    default_timeout: int = 30


@dataclass
class OllamaConfig:
    """Ollama LLM configuration"""
    host: str
    port: int
    model: str = "llama2"
    timeout: int = 60
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


@dataclass
class SecurityConfig:
    """Security configuration"""
    encryption_key_path: str
    vault_service: str  # aws_secrets, vault, 1password
    vault_endpoint: str


@dataclass
class TimeoutConfig:
    """Timeout configuration"""
    intent_detection: int = 5
    planning: int = 10
    execution: int = 60
    verification: int = 15
    agent_call: int = 30
    adb_call: int = 20


class Config:
    """Main configuration"""
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_USER = os.getenv("DB_USER", "apa_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "changeme")
    DB_NAME = os.getenv("DB_NAME", "apa_os")

    if DATABASE_URL:
        try:
            database_config = DatabaseConfig.from_uri(DATABASE_URL)
        except ValueError:
            database_config = DatabaseConfig(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
            )
    else:
        database_config = DatabaseConfig(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
    
    # ADB
    ADB_PATH = os.getenv("ADB_PATH", "adb")
    adb_config = ADBConfig(adb_path=ADB_PATH)
    
    # Ollama
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost")
    OLLAMA_PORT = int(os.getenv("OLLAMA_PORT", "11434"))
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    ollama_config = OllamaConfig(
        host=OLLAMA_HOST,
        port=OLLAMA_PORT,
        model=OLLAMA_MODEL,
    )

    # Security
    ENCRYPTION_KEY_PATH = os.getenv("ENCRYPTION_KEY_PATH", "")
    VAULT_SERVICE = os.getenv("VAULT_SERVICE", "aws_secrets")
    VAULT_ENDPOINT = os.getenv("VAULT_ENDPOINT", "")
    security_config = SecurityConfig(
        encryption_key_path=ENCRYPTION_KEY_PATH,
        vault_service=VAULT_SERVICE,
        vault_endpoint=VAULT_ENDPOINT,
    )
    
    # Timeouts
    INTENT_TIMEOUT = int(os.getenv("INTENT_TIMEOUT", "5"))
    PLANNING_TIMEOUT = int(os.getenv("PLANNING_TIMEOUT", "10"))
    EXECUTION_TIMEOUT = int(os.getenv("EXECUTION_TIMEOUT", "60"))
    timeout_config = TimeoutConfig(
        intent_detection=INTENT_TIMEOUT,
        planning=PLANNING_TIMEOUT,
        execution=EXECUTION_TIMEOUT,
    )
    
    # API
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_WORKERS = int(os.getenv("API_WORKERS", "4"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "apa_os.log")
    
    # Environment
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = ENVIRONMENT == "development"
    
    @classmethod
    def get_database_config(cls) -> DatabaseConfig:
        """Get database configuration"""
        return cls.database_config
    
    @classmethod
    def get_adb_config(cls) -> ADBConfig:
        """Get ADB configuration"""
        return cls.adb_config
    
    @classmethod
    def get_ollama_config(cls) -> OllamaConfig:
        """Get Ollama configuration"""
        return cls.ollama_config

    @classmethod
    def get_redis_url(cls) -> str:
        """Get Redis URL"""
        return cls.REDIS_URL
    
    @classmethod
    def get_security_config(cls) -> SecurityConfig:
        """Get security configuration"""
        return cls.security_config
    
    @classmethod
    def get_timeout_config(cls) -> TimeoutConfig:
        """Get timeout configuration"""
        return cls.timeout_config


def get_config() -> Config:
    """Get application configuration"""
    return Config()
