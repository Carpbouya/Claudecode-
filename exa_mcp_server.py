#!/usr/bin/env python3
"""Exa MCP server — exposes Exa search capabilities to Claude Code."""

import os
import sys
import json
import asyncio
from typing import Any

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp import types
except ImportError:
    print("mcp package not found. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    from exa_py import Exa
except ImportError:
    print("exa-py not found. Run: pip install exa-py", file=sys.stderr)
    sys.exit(1)


def get_client() -> Exa:
    api_key = os.environ.get("EXA_API_KEY")
    if not api_key:
        raise RuntimeError("EXA_API_KEY environment variable is not set")
    return Exa(api_key=api_key)


server = Server("exa-search")


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="exa_search",
            description=(
                "Search the web with Exa's AI-powered search engine. "
                "Returns titles, URLs, and optional snippets/full text."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default 5, max 10)",
                        "default": 5,
                    },
                    "include_text": {
                        "type": "boolean",
                        "description": "Include full page text in results",
                        "default": False,
                    },
                    "use_autoprompt": {
                        "type": "boolean",
                        "description": "Let Exa optimise the query automatically",
                        "default": True,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="exa_find_similar",
            description=(
                "Find pages similar to a given URL using Exa."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to find similar pages for",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default 5)",
                        "default": 5,
                    },
                    "include_text": {
                        "type": "boolean",
                        "description": "Include full page text in results",
                        "default": False,
                    },
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="exa_get_contents",
            description="Retrieve the full text contents of one or more URLs via Exa.",
            inputSchema={
                "type": "object",
                "properties": {
                    "urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of URLs to fetch content for",
                    },
                },
                "required": ["urls"],
            },
        ),
    ]


def _format_results(results: Any, include_text: bool) -> str:
    output = []
    for i, r in enumerate(results.results, 1):
        parts = [f"{i}. {r.title}", f"   URL: {r.url}"]
        if hasattr(r, "score") and r.score is not None:
            parts.append(f"   Score: {r.score:.4f}")
        if include_text and hasattr(r, "text") and r.text:
            snippet = r.text[:800].replace("\n", " ")
            parts.append(f"   Text: {snippet}…")
        output.append("\n".join(parts))
    return "\n\n".join(output) if output else "No results found."


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    exa = get_client()

    if name == "exa_search":
        query = arguments["query"]
        num_results = min(int(arguments.get("num_results", 5)), 10)
        include_text = bool(arguments.get("include_text", False))
        use_autoprompt = bool(arguments.get("use_autoprompt", True))

        kwargs: dict[str, Any] = {
            "num_results": num_results,
            "use_autoprompt": use_autoprompt,
        }
        if include_text:
            kwargs["text"] = True

        results = exa.search(query, **kwargs)
        return [types.TextContent(type="text", text=_format_results(results, include_text))]

    elif name == "exa_find_similar":
        url = arguments["url"]
        num_results = min(int(arguments.get("num_results", 5)), 10)
        include_text = bool(arguments.get("include_text", False))

        kwargs = {"num_results": num_results}
        if include_text:
            kwargs["text"] = True

        results = exa.find_similar(url, **kwargs)
        return [types.TextContent(type="text", text=_format_results(results, include_text))]

    elif name == "exa_get_contents":
        urls = arguments["urls"]
        results = exa.get_contents(urls)
        output = []
        for r in results.results:
            text = (r.text or "").strip()[:2000]
            output.append(f"URL: {r.url}\n\n{text}")
        text = "\n\n---\n\n".join(output) if output else "No content retrieved."
        return [types.TextContent(type="text", text=text)]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
