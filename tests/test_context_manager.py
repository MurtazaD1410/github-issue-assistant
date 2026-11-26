from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES, RemoveMessage

import context_manager


def _make_graph(messages):
    graph = MagicMock()
    graph.aget_state = AsyncMock(return_value=SimpleNamespace(values={"messages": messages}))
    graph.aupdate_state = AsyncMock()
    return graph


def test_compact_empty_conversation():
    import asyncio

    graph = _make_graph([])
    ok, msg = asyncio.run(context_manager.compact_conversation(graph, {"configurable": {"thread_id": "t1"}}))
    assert not ok
    assert "empty" in msg.lower()
    graph.aupdate_state.assert_not_awaited()


def test_compact_too_short():
    import asyncio

    messages = [
        SystemMessage(content="sys"),
        HumanMessage(content="hi"),
        AIMessage(content="hello"),
    ]
    graph = _make_graph(messages)
    ok, msg = asyncio.run(
        context_manager.compact_conversation(graph, {"configurable": {"thread_id": "t1"}}, keep_recent_turns=2)
    )
    assert not ok
    assert "too short" in msg.lower()
    graph.aupdate_state.assert_not_awaited()


def test_compact_preserves_system_and_recent_turns(monkeypatch):
    import asyncio

    sys_msg = SystemMessage(content="You are a GitHub assistant.")
    messages = [
        sys_msg,
        HumanMessage(content="List issues in octocat/Hello-World"),
        AIMessage(content="", tool_calls=[{"id": "c1", "name": "get_issues", "args": {"owner": "octocat", "repo": "Hello-World"}}]),
        ToolMessage(content='{"issues": [{"number": 1}]}', tool_call_id="c1", name="get_issues"),
        AIMessage(content="Found issue #1."),
        HumanMessage(content="Tell me more about #1"),
        AIMessage(content="Issue #1 is a test issue."),
        HumanMessage(content="Thanks!"),
        AIMessage(content="You're welcome!"),
    ]
    graph = _make_graph(messages)

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(return_value=SimpleNamespace(content="Discussed octocat/Hello-World issue #1."))
    monkeypatch.setattr(context_manager, "llm", fake_llm)

    ok, msg = asyncio.run(
        context_manager.compact_conversation(graph, {"configurable": {"thread_id": "t1"}}, keep_recent_turns=2)
    )
    assert ok
    assert "Compacted 4 older messages" in msg
    graph.aupdate_state.assert_awaited_once()

    updated = graph.aupdate_state.call_args[0][1]["messages"]
    assert isinstance(updated[0], RemoveMessage)
    assert updated[0].id == REMOVE_ALL_MESSAGES
    assert updated[1] == sys_msg
    assert isinstance(updated[2], HumanMessage)
    assert "[Summary of earlier conversation]" in updated[2].content
    assert "octocat/Hello-World issue #1" in updated[2].content
    # Recent 2 turns (4 messages: Human, AI, Human, AI) preserved intact
    assert [m.content for m in updated[3:]] == [
        "Tell me more about #1",
        "Issue #1 is a test issue.",
        "Thanks!",
        "You're welcome!",
    ]


def test_compact_llm_failure_leaves_state_unchanged(monkeypatch):
    import asyncio

    messages = [
        SystemMessage(content="sys"),
        HumanMessage(content="turn 1"),
        AIMessage(content="reply 1"),
        HumanMessage(content="turn 2"),
        AIMessage(content="reply 2"),
    ]
    graph = _make_graph(messages)

    fake_llm = MagicMock()
    fake_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Ollama down"))
    monkeypatch.setattr(context_manager, "llm", fake_llm)

    ok, msg = asyncio.run(
        context_manager.compact_conversation(graph, {"configurable": {"thread_id": "t1"}}, keep_recent_turns=1)
    )
    assert not ok
    assert "Ollama down" in msg
    graph.aupdate_state.assert_not_awaited()
