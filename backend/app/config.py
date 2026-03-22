"""
FinAgent Configuration Settings
Loads environment variables and provides typed configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    
    # Fi MCP Server
    fi_mcp_url: str = Field(
        default="http://localhost:8080/mcp/stream",
        description="Fi MCP server URL"
    )
    fi_mcp_phone_number: str = Field(
        default="2222222222",
        description="Default phone number for Fi MCP authentication"
    )
    
    # Firecrawl MCP (optional)
    firecrawl_mcp_url: Optional[str] = Field(
        default=None,
        description="Firecrawl MCP server URL"
    )
    firecrawl_api_key: Optional[str] = Field(
        default=None,
        description="Firecrawl API key"
    )
    
    
    # Tavily Search API (optional)
    tavily_api_key: Optional[str] = Field(
        default=None,
        description="Tavily API key for web search"
    )
    
    # Alpha Vantage Stock API (optional)
    alpha_vantage_api_key: Optional[str] = Field(
        default=None,
        description="Alpha Vantage API key for stock market data"
    )
    # Local LLM Configuration (MLX) / OpenRouter / DeepSeek
    llm_provider: str = Field(
        default="mlx",
        description="LLM provider: openrouter, deepseek, or mlx"
    )
    llm_model: str = Field(
        default="mlx-community/gemma-3-4b-it-4bit",
        description="Model name for the selected LLM provider"
    )
    llm_max_tokens: int = Field(
        default=2048,
        description="Maximum tokens for LLM generation"
    )
    llm_temperature: float = Field(
        default=0.7,
        description="LLM temperature for generation"
    )
    
    # OpenRouter API
    openrouter_api_key: Optional[str] = Field(
        default=None,
        description="OpenRouter API key for free LLM models"
    )
    
    # DeepSeek API
    deepseek_api_key: Optional[str] = Field(
        default=None,
        description="DeepSeek API key (fallback provider)"
    )
    
    # TradingAgents Integration
    trading_agents_llm_provider: str = Field(
        default="openrouter",
        description="LLM provider for TradingAgents pipeline"
    )
    trading_agents_deep_think_llm: str = Field(
        default="qwen/qwen3-next-80b-a3b-instruct:free",
        description="Deep thinking model for TradingAgents"
    )
    trading_agents_quick_think_llm: str = Field(
        default="qwen/qwen3-coder:free",
        description="Quick thinking model for TradingAgents"
    )
    
    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///./finagent.db",
        description="Database connection URL"
    )
    
    # Privacy Settings
    privacy_level: str = Field(
        default="HIGH",
        description="Privacy level (LOW, MEDIUM, HIGH)"
    )
    enable_audit_logging: bool = Field(
        default=True,
        description="Enable audit logging for all operations"
    )
    
    # Frontend
    frontend_url: str = Field(
        default="http://localhost:3000",
        description="Frontend URL for CORS"
    )
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated CORS allowed origins"
    )

    # Auth
    jwt_secret_key: str = Field(
        default="CHANGE_ME_IN_ENV",
        description="JWT signing secret"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    jwt_access_token_expire_minutes: int = Field(
        default=60 * 24,
        description="JWT access token expiry in minutes"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse configured comma-separated CORS origins."""
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return origins or [self.frontend_url]


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    import os
    try:
        # Check if .env file is accessible
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.isfile(env_path):
            return Settings()
    except PermissionError:
        pass
    # Fall back to environment variables only (skip .env file)
    return Settings(_env_file=None)
