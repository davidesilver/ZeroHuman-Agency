"""MCP Client to connect to remote Model Context Protocol servers like Context7."""

from __future__ import annotations

import httpx
import logging
from typing import Dict, Any, Optional

from ..config import settings

logger = logging.getLogger(__name__)

async def fetch_context7_docs(query: str, limit: int = 3) -> str:
    """
    Fetch up-to-date framework documentation using the Context 7 MCP Server.
    
    This function simulates an MCP request or direct REST call to Context 7 to
    retrieve documentation snippets to augment the LLM's context window.
    """
    if not settings.context7_mcp_url:
        return ""
        
    logger.info(f"Fetching Context 7 docs for query: {query}")
    
    # Normally we would use an MCP SDK like mcp-client for Python,
    # but Context7 also exposes REST endpoints or we can simulate the fetch here
    # Since Context 7 requires API keys for extended usage, we pass it if we have it
    
    headers = {"Content-Type": "application/json"}
    # In a real environment, you'd integrate the mcp SDK:
    # mcp = ClientSession(StdioServerParameters(command="npx", args=["-y", "@upstash/context7"]))
    
    # As a fallback representation of the Context7 call
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                settings.context7_mcp_url + "/query",
                json={"query": query, "limit": limit},
                headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                docs = data.get("documents", [])
                
                context_str = "\n\n--- CONTEXT 7 DOCUMENTATION ---\n"
                for doc in docs:
                    context_str += f"\nSnippet from {doc.get('title', 'Doc')}:\n{doc.get('content', '')}\n"
                
                return context_str
            else:
                logger.warning(f"Context 7 returned status {resp.status_code}")
                return ""
    except Exception as e:
        logger.error(f"Failed to fetch from Context 7: {e}")
        return ""

async def augment_prompt_with_mcp(base_prompt: str, queries: list[str]) -> str:
    """
    Given a base prompt, fetching context from MCP tools and appending it.
    """
    additional_context = ""
    for query in queries:
        docs = await fetch_context7_docs(query)
        if docs:
            additional_context += docs
            
    if additional_context:
        return base_prompt + "\n\nUse the following up-to-date documentation to inform your answer:\n" + additional_context
        
    return base_prompt
