import session_manager


def test_session_crud(tmp_path, monkeypatch):
    monkeypatch.setattr(session_manager, "DB_PATH", tmp_path / "sessions.sqlite")
    session_manager.initialize_database()

    # Create is idempotent
    session_manager.create_session("thread-1")
    session_manager.create_session("thread-1")

    row = session_manager.get_session("thread-1")
    assert row is not None
    assert row[0] == "thread-1"
    assert row[1] is None

    # Update and clear title
    session_manager.update_title("thread-1", "Bug Triage")
    assert session_manager.get_session("thread-1")[1] == "Bug Triage"

    session_manager.clear_title("thread-1")
    assert session_manager.get_session("thread-1")[1] is None

    # List and delete
    assert len(session_manager.get_sessions()) == 1
    assert session_manager.delete_session("thread-1") is True
    assert session_manager.delete_session("thread-1") is False
    assert session_manager.get_sessions() == []
