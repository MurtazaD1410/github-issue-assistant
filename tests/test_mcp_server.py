import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import github_api
import server

EXPECTED_TOOLS = {
    "get_issues",
    "list_repos",
    "get_issue_details",
    "get_issue_comments",
    "get_repository",
    "search_issues",
    "list_pull_requests",
    "create_issue",
    "add_issue_comment",
    "update_issue",
}


def test_mcp_stdio_registers_all_10_tools():
    server_path = str(Path(__file__).resolve().parent.parent / "server.py")

    async def list_via_stdio():
        params = StdioServerParameters(command=sys.executable, args=[server_path])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return {t.name: t for t in result.tools}

    tools = asyncio.run(list_via_stdio())
    assert set(tools.keys()) == EXPECTED_TOOLS
    for name, tool in tools.items():
        assert tool.description, f"Missing description on MCP tool {name}"


def test_all_10_mcp_tool_wrappers_delegate_to_github_api(monkeypatch):
    monkeypatch.setattr(github_api, "get_open_issues", lambda o, r: {"tool": "get_issues", "o": o, "r": r})
    monkeypatch.setattr(github_api, "get_user_repositories", lambda limit=30: {"tool": "list_repos", "limit": limit})
    monkeypatch.setattr(github_api, "get_issue_details", lambda o, r, n: {"tool": "get_issue_details", "n": n})
    monkeypatch.setattr(github_api, "get_issue_comments", lambda o, r, n, limit=30: {"tool": "get_issue_comments", "n": n, "limit": limit})
    monkeypatch.setattr(github_api, "get_repository", lambda o, r: {"tool": "get_repository", "o": o, "r": r})
    monkeypatch.setattr(github_api, "search_issues", lambda q, limit=20: {"tool": "search_issues", "q": q, "limit": limit})
    monkeypatch.setattr(github_api, "list_pull_requests", lambda o, r, state="open", limit=30: {"tool": "list_pull_requests", "state": state})
    monkeypatch.setattr(github_api, "create_issue", lambda o, r, t, body="", labels=None, assignees=None: {"tool": "create_issue", "t": t})
    monkeypatch.setattr(github_api, "add_issue_comment", lambda o, r, n, b: {"tool": "add_issue_comment", "n": n, "b": b})
    monkeypatch.setattr(github_api, "update_issue", lambda o, r, n, state=None, labels=None, assignees=None: {"tool": "update_issue", "state": state})

    assert server.get_issues("o", "r")["tool"] == "get_issues"
    assert server.list_repos(limit=5) == {"tool": "list_repos", "limit": 5}
    assert server.get_issue_details("o", "r", 3)["n"] == 3
    assert server.get_issue_comments("o", "r", 3, limit=10)["limit"] == 10
    assert server.get_repository("o", "r")["tool"] == "get_repository"
    assert server.search_issues("bug", limit=5)["q"] == "bug"
    assert server.list_pull_requests("o", "r", state="closed")["state"] == "closed"
    assert server.create_issue("o", "r", "Title")["t"] == "Title"
    assert server.add_issue_comment("o", "r", 3, "Hi")["b"] == "Hi"
    assert server.update_issue("o", "r", 3, state="closed")["state"] == "closed"
