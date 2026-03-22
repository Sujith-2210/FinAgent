"""
MCP Client Wrapper
Provides connection management and tool invocation for MCP servers.

Updated for proper fi-mcp-dev integration with session management.
"""

from mcp.client.streamable_http import streamablehttp_client
from mcp.client.session import ClientSession
from typing import Optional, Dict, Any, List
import asyncio
import uuid
import json
from loguru import logger

from app.config import get_settings


class MCPClient:
    """
    MCP Client for connecting to MCP servers.
    
    Handles session management, authentication, and tool invocation.
    """
    
    def __init__(self, server_url: str, session_id: Optional[str] = None):
        self.server_url = server_url
        # Session ID must be prefixed with "mcp-session-" per fi-mcp-dev requirement
        self.session_id = session_id or f"mcp-session-{uuid.uuid4()}"
        self._connected = False
        self._authenticated = False
        self._phone_number: Optional[str] = None
    
    async def call_tool_with_connection(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Call a tool with a fresh connection.
        
        fi-mcp-dev expects a new connection per tool call since sessions
        are managed via the Mcp-Session-Id header.
        """
        try:
            logger.info(f"Calling MCP tool: {tool_name}")
            
            async with streamablehttp_client(
                self.server_url,
                headers={"Mcp-Session-Id": self.session_id}
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    # Call the tool
                    result = await session.call_tool(tool_name, arguments or {})
                    
                    # Parse the result
                    if hasattr(result, 'content') and result.content:
                        content = result.content[0]
                        if hasattr(content, 'text'):
                            try:
                                return json.loads(content.text)
                            except json.JSONDecodeError:
                                return {"raw_text": content.text}
                    
                    return {"result": str(result)}
                    
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            # Check if it's an auth error
            if "login_url" in str(e).lower() or "authentication" in str(e).lower():
                return {"requires_auth": True, "error": str(e)}
            raise
    
    async def list_tools_with_connection(self) -> List[Dict[str, Any]]:
        """List available tools with a fresh connection."""
        try:
            async with streamablehttp_client(
                self.server_url,
                headers={"Mcp-Session-Id": self.session_id}
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    return [{"name": t.name, "description": t.description} for t in tools.tools]
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []
    
    @property
    def is_connected(self) -> bool:
        return self._connected


class MCPClientManager:
    """
    Manages MCP client connections for the application.
    
    Provides a singleton-like access to MCP clients for different servers.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._fi_client: Optional[MCPClient] = None
        self._firecrawl_client: Optional[MCPClient] = None
        self._session_data: Dict[str, Dict[str, Any]] = {}
    
    def get_fi_client(self, phone_number: Optional[str] = None, session_id: Optional[str] = None) -> MCPClient:
        """Get or create Fi MCP client."""
        # Create a new client with the session ID
        if session_id:
            client = MCPClient(self.settings.fi_mcp_url, session_id)
        elif self._fi_client is None:
            self._fi_client = MCPClient(self.settings.fi_mcp_url)
            client = self._fi_client
        else:
            client = self._fi_client
        
        if phone_number:
            client._phone_number = phone_number
        
        return client
    
    def get_firecrawl_client(self) -> Optional[MCPClient]:
        """Get or create Firecrawl MCP client (if configured)."""
        if not self.settings.firecrawl_mcp_url:
            logger.warning("Firecrawl MCP URL not configured")
            return None
        
        if self._firecrawl_client is None:
            self._firecrawl_client = MCPClient(self.settings.firecrawl_mcp_url)
        return self._firecrawl_client
    
    def store_session_data(self, session_id: str, data: Dict[str, Any]):
        """Store session-specific data."""
        self._session_data[session_id] = data
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session-specific data."""
        return self._session_data.get(session_id)
    
    async def close(self):
        """Close all MCP connections."""
        logger.info("Closing MCP connections...")
        # Cleanup logic here
