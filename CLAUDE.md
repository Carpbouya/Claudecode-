# Exa Integration for Claude Code

This project adds [Exa](https://exa.ai) web-search capabilities to Claude Code via an MCP server.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Exa API key

```bash
export EXA_API_KEY="your_api_key_here"
```

Get a key at https://dashboard.exa.ai

### 3. Start Claude Code in this directory

The `.claude/settings.json` file automatically registers `exa_mcp_server.py` as an MCP server.

## Available tools

| Tool | Description |
|------|-------------|
| `exa_search` | AI-powered web search |
| `exa_find_similar` | Find pages similar to a URL |
| `exa_get_contents` | Retrieve full text from URLs |

## Usage examples

Once Claude Code is running, you can ask:

- "Search for the latest news about AI agents"
- "Find pages similar to https://example.com"
- "Get the full contents of https://example.com/article"
