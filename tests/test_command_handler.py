import asyncio
from unittest.mock import MagicMock

import command_handler


def test_empty_input_returns_false():
    graph = MagicMock()
    app_state = {"thread_id": "t1", "config": {}, "is_new_conversation": True, "tools": []}
    assert asyncio.run(command_handler.handle_command("", graph, app_state)) is False
    assert asyncio.run(command_handler.handle_command("   ", graph, app_state)) is False


def test_logout_returns_true(monkeypatch):
    monkeypatch.setattr(command_handler, "delete_token", lambda: False)
    monkeypatch.setattr(command_handler, "print_system_message", lambda *a, **kw: None)
    graph = MagicMock()
    app_state = {"thread_id": "t1", "config": {}, "is_new_conversation": True, "tools": []}
    assert asyncio.run(command_handler.handle_command("/logout", graph, app_state)) is True
