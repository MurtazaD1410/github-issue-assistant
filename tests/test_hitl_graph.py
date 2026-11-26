import asyncio
from unittest.mock import AsyncMock, MagicMock

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

import graph_builder


def _build_test_graph(monkeypatch, ai_responses):
    executed_writes = []

    @tool
    def get_issues(owner: str, repo: str) -> str:
        """Read-only tool."""
        return f"issues for {owner}/{repo}"

    @tool
    def create_issue(owner: str, repo: str, title: str) -> str:
        """Write tool."""
        executed_writes.append((owner, repo, title))
        return f"created issue: {title}"

    fake_client = MagicMock()
    fake_client.get_tools = AsyncMock(return_value=[get_issues, create_issue])
    monkeypatch.setattr(graph_builder, "MultiServerMCPClient", lambda *a, **kw: fake_client)

    responses = iter(ai_responses)
    fake_bound_llm = MagicMock()
    fake_bound_llm.ainvoke = AsyncMock(side_effect=lambda *a, **kw: next(responses))

    fake_llm = MagicMock()
    fake_llm.bind_tools = MagicMock(return_value=fake_bound_llm)
    monkeypatch.setattr(graph_builder, "ChatOllama", lambda *a, **kw: fake_llm)

    graph, _ = asyncio.run(graph_builder.build_graph(MemorySaver()))
    return graph, executed_writes


def test_read_tool_executes_without_interrupt(monkeypatch):
    graph, _ = _build_test_graph(
        monkeypatch,
        [
            AIMessage(
                content="",
                tool_calls=[{"id": "call_1", "name": "get_issues", "args": {"owner": "o", "repo": "r"}}],
            ),
            AIMessage(content="Here are the issues."),
        ],
    )
    config = {"configurable": {"thread_id": "read-test"}}
    result = asyncio.run(graph.ainvoke({"messages": [HumanMessage(content="list issues")]}, config=config))

    assert "__interrupt__" not in result
    assert result["messages"][-1].content == "Here are the issues."


def test_write_tool_interrupts_and_executes_when_approved(monkeypatch):
    graph, executed_writes = _build_test_graph(
        monkeypatch,
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_w1",
                        "name": "create_issue",
                        "args": {"owner": "o", "repo": "r", "title": "Bug"},
                    }
                ],
            ),
            AIMessage(content="Issue created."),
        ],
    )
    config = {"configurable": {"thread_id": "write-approve"}}
    first = asyncio.run(graph.ainvoke({"messages": [HumanMessage(content="create bug")]}, config=config))

    assert "__interrupt__" in first
    assert first["__interrupt__"][0].value["type"] == "tool_approval"
    assert executed_writes == []

    resumed = asyncio.run(graph.ainvoke(Command(resume=True), config=config))
    assert "__interrupt__" not in resumed
    assert executed_writes == [("o", "r", "Bug")]
    assert resumed["messages"][-1].content == "Issue created."


def test_write_tool_cancelled_when_rejected(monkeypatch):
    graph, executed_writes = _build_test_graph(
        monkeypatch,
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "id": "call_w2",
                        "name": "create_issue",
                        "args": {"owner": "o", "repo": "r", "title": "Bug"},
                    }
                ],
            ),
            AIMessage(content="Action cancelled as requested."),
        ],
    )
    config = {"configurable": {"thread_id": "write-reject"}}
    first = asyncio.run(graph.ainvoke({"messages": [HumanMessage(content="create bug")]}, config=config))
    assert "__interrupt__" in first

    resumed = asyncio.run(graph.ainvoke(Command(resume=False), config=config))
    assert executed_writes == []
    assert "cancelled" in resumed["messages"][-1].content.lower()
