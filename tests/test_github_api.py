from unittest.mock import MagicMock
import requests
import github_api


def _mock_response(status_code=200, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.headers = headers or {}
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


def test_get_open_issues_filters_prs(monkeypatch):
    monkeypatch.setattr(github_api, "get_token", lambda: None)
    payload = [
        {
            "number": 1,
            "title": "Real bug",
            "html_url": "https://example.com/1",
            "state": "open",
            "labels": [{"name": "bug"}],
        },
        {
            "number": 2,
            "title": "A PR",
            "html_url": "https://example.com/2",
            "state": "open",
            "labels": [],
            "pull_request": {},
        },
    ]
    monkeypatch.setattr(
        requests, "request", lambda *a, **kw: _mock_response(200, payload)
    )

    result = github_api.get_open_issues("octocat", "Hello-World")
    assert result["total_returned"] == 1
    assert result["issues"][0]["number"] == 1
    assert result["issues"][0]["labels"] == ["bug"]


def test_get_open_issues_empty(monkeypatch):
    monkeypatch.setattr(github_api, "get_token", lambda: None)
    monkeypatch.setattr(requests, "request", lambda *a, **kw: _mock_response(200, []))

    result = github_api.get_open_issues("octocat", "Hello-World")
    assert result["total_returned"] == 0
    assert "no open issues" in result["message"].lower()


def test_github_request_errors(monkeypatch):
    monkeypatch.setattr(github_api, "get_token", lambda: None)

    monkeypatch.setattr(requests, "request", lambda *a, **kw: _mock_response(404))
    assert "404" in github_api.get_repository("o", "r")["error"]

    monkeypatch.setattr(requests, "request", lambda *a, **kw: _mock_response(401))
    assert "/login" in github_api.get_repository("o", "r")["error"]

    monkeypatch.setattr(
        requests,
        "request",
        lambda *a, **kw: _mock_response(403, headers={"X-RateLimit-Remaining": "0"}),
    )
    assert "rate limit" in github_api.get_repository("o", "r")["error"].lower()

    def raise_timeout(*a, **kw):
        raise requests.Timeout()

    monkeypatch.setattr(requests, "request", raise_timeout)
    assert "timed out" in github_api.get_repository("o", "r")["error"].lower()


def test_write_tools_require_auth(monkeypatch):
    monkeypatch.setattr(github_api, "get_token", lambda: None)

    assert "Not authenticated" in github_api.get_user_repositories()["error"]
    assert "Not authenticated" in github_api.create_issue("o", "r", "Title")["error"]
    assert (
        "Not authenticated" in github_api.add_issue_comment("o", "r", 1, "Hi")["error"]
    )
    assert (
        "Not authenticated"
        in github_api.update_issue("o", "r", 1, state="closed")["error"]
    )


def test_search_issues_appends_is_issue(monkeypatch):
    monkeypatch.setattr(github_api, "get_token", lambda: None)
    monkeypatch.setattr(
        requests,
        "request",
        lambda *a, **kw: _mock_response(200, {"total_count": 0, "items": []}),
    )

    result = github_api.search_issues("repo:octocat/Hello-World bug")
    assert result["query"] == "repo:octocat/Hello-World bug is:issue"


def test_get_open_issues_paginates(monkeypatch):
    monkeypatch.setattr(github_api, "get_token", lambda: None)
    page1 = [
        {
            "number": i,
            "title": f"Issue {i}",
            "html_url": f"https://example.com/{i}",
            "state": "open",
            "labels": [],
        }
        for i in range(1, 101)
    ]
    page2 = [
        {
            "number": 101,
            "title": "Issue 101",
            "html_url": "https://example.com/101",
            "state": "open",
            "labels": [],
        }
    ]
    calls = []

    def fake_request(method, url, headers=None, params=None, json=None, timeout=None):
        calls.append(params["page"])
        return _mock_response(200, page1 if params["page"] == 1 else page2)

    monkeypatch.setattr(requests, "request", fake_request)
    result = github_api.get_open_issues("octocat", "Hello-World")
    assert calls == [1, 2]
    assert result["total_returned"] == 101


def test_auth_manager_env_fallback_on_non_macos(monkeypatch):
    import subprocess
    import auth_manager

    def raise_not_found(*a, **kw):
        raise FileNotFoundError("security not found")

    monkeypatch.setattr(subprocess, "run", raise_not_found)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_env_test_123")
    assert auth_manager.get_token() == "ghp_env_test_123"
    assert auth_manager.save_token("x") is False
    assert auth_manager.delete_token() is False
