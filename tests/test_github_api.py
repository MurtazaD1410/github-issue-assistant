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
