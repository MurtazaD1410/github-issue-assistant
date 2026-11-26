import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import command_handler


def _make_graph(messages=None):
    graph = MagicMock()
    graph.checkpointer = MagicMock()
    graph.checkpointer.adelete_thread = AsyncMock()
    graph.aget_state = AsyncMock(
        return_value=SimpleNamespace(values={"messages": messages or []})
    )
    return graph


def test_empty_input_returns_false():
    graph = _make_graph()
    app_state = {"thread_id": "t1", "config": {}, "is_new_conversation": True, "tools": []}
    assert asyncio.run(command_handler.handle_command("", graph, app_state)) is False
    assert asyncio.run(command_handler.handle_command("   ", graph, app_state)) is False


def test_logout_returns_true(monkeypatch):
    monkeypatch.setattr(command_handler, "delete_token", lambda: False)
    monkeypatch.setattr(command_handler, "print_system_message", lambda *a, **kw: None)
    graph = _make_graph()
    app_state = {"thread_id": "t1", "config": {}, "is_new_conversation": True, "tools": []}
    assert asyncio.run(command_handler.handle_command("/logout", graph, app_state)) is True


def test_clear_deletes_thread_and_clears_title(monkeypatch):
    cleared = []
    monkeypatch.setattr(command_handler, "clear_title", lambda tid: cleared.append(tid))
    monkeypatch.setattr(command_handler, "print_system_message", lambda *a, **kw: None)

    graph = _make_graph()
    app_state = {"thread_id": "t1", "config": {}, "is_new_conversation": False, "tools": []}

    assert asyncio.run(command_handler.handle_command("/clear", graph, app_state)) is True
    graph.checkpointer.adelete_thread.assert_awaited_once_with("t1")
    assert cleared == ["t1"]
    assert app_state["is_new_conversation"] is True


def test_rename_updates_title_or_reports_usage(monkeypatch):
    renamed = []
    errors = []
    monkeypatch.setattr(command_handler, "create_session", lambda tid: None)
    monkeypatch.setattr(command_handler, "update_title", lambda tid, title: renamed.append((tid, title)))
    monkeypatch.setattr(command_handler, "print_system_message", lambda *a, **kw: None)
    monkeypatch.setattr(command_handler, "print_error_message", lambda msg: errors.append(msg))

    graph = _make_graph()
    app_state = {"thread_id": "t1", "config": {}, "is_new_conversation": True, "tools": []}

    assert asyncio.run(command_handler.handle_command("/rename", graph, app_state)) is True
    assert errors and "Usage" in errors[0]

    assert asyncio.run(command_handler.handle_command("/rename Bug Triage", graph, app_state)) is True
    assert renamed == [("t1", "Bug Triage")]


def test_switch_updates_app_state_and_handles_cancel(monkeypatch):
    monkeypatch.setattr(
        command_handler,
        "get_sessions",
        lambda: [("t2", "Second Chat", "2026-01-01", "2026-01-02")],
    )
    monkeypatch.setattr(command_handler, "print_system_message", lambda *a, **kw: None)

    graph = _make_graph(messages=["existing message"])
    app_state = {"thread_id": "t1", "config": {"configurable": {"thread_id": "t1"}}, "is_new_conversation": True, "tools": []}

    # Cancel
    monkeypatch.setattr(command_handler, "select_session", AsyncMock(return_value=None))
    assert asyncio.run(command_handler.handle_command("/switch", graph, app_state)) is True
    assert app_state["thread_id"] == "t1"

    # Switch to t2
    monkeypatch.setattr(command_handler, "select_session", AsyncMock(return_value="t2"))
    assert asyncio.run(command_handler.handle_command("/switch", graph, app_state)) is True
    assert app_state["thread_id"] == "t2"
    assert app_state["config"] == {"configurable": {"thread_id": "t2"}}
    assert app_state["is_new_conversation"] is False


def test_delete_confirmed_and_cancelled(monkeypatch):
    deleted_sessions = []
    monkeypatch.setattr(
        command_handler,
        "get_sessions",
        lambda: [("t1", "Current Chat", "2026-01-01", "2026-01-02")],
    )
    monkeypatch.setattr(command_handler, "select_session", AsyncMock(return_value="t1"))
    monkeypatch.setattr(command_handler, "delete_session", lambda tid: deleted_sessions.append(tid))
    monkeypatch.setattr(command_handler, "print_system_message", lambda *a, **kw: None)

    graph = _make_graph()
    app_state = {"thread_id": "t1", "config": {"configurable": {"thread_id": "t1"}}, "is_new_conversation": False, "tools": []}

    # Cancelled confirmation
    fake_prompt_no = MagicMock()
    fake_prompt_no.prompt_async = AsyncMock(return_value="n")
    monkeypatch.setattr(command_handler, "PromptSession", lambda: fake_prompt_no)
    assert asyncio.run(command_handler.handle_command("/delete", graph, app_state)) is True
    assert deleted_sessions == []
    graph.checkpointer.adelete_thread.assert_not_awaited()

    # Confirmed deletion of active thread resets app_state to a new thread
    fake_prompt_yes = MagicMock()
    fake_prompt_yes.prompt_async = AsyncMock(return_value="y")
    monkeypatch.setattr(command_handler, "PromptSession", lambda: fake_prompt_yes)
    assert asyncio.run(command_handler.handle_command("/delete", graph, app_state)) is True
    graph.checkpointer.adelete_thread.assert_awaited_once_with("t1")
    assert deleted_sessions == ["t1"]
    assert app_state["thread_id"] != "t1"
    assert app_state["is_new_conversation"] is True
