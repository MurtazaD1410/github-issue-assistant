import requests
from auth_manager import get_token


def _get_header() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
    }
    token = get_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_request(
    method: str, url: str, params: dict | None = None, json_body: dict | None = None
) -> tuple[dict | list | None, str | None]:
    """Perform a GitHub GET request and return (data, error_message)."""

    try:
        response = requests.request(
            method,
            url,
            headers=_get_header(),
            params=params,
            json=json_body,
            timeout=15,
        )

    except requests.Timeout:
        return (
            None,
            "GitHub API request timed out. Please try again.",
        )
    except requests.RequestException as e:
        return None, f"Network error contacting GitHub: {e}"

    if response.status_code == 401:
        return (
            None,
            "GitHub authentication failed or token expired. Ask the user to run /login.",
        )

    if response.status_code in (403, 429):
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining == "0":
            hint = (
                " Ask the user to run /login for a higher rate limit."
                if not get_token()
                else ""
            )
            return None, f"GitHub API rate limit exceeded.{hint}"
        return (
            None,
            "Access forbidden (403). You may not have permission for this resource.",
        )

    if response.status_code == 404:
        return None, "Repository, issue, or resource not found (404)."

    if not response.ok:
        return None, f"GitHub API error ({response.status_code})."

    return response.json(), None


def _github_get(
    url: str, params: dict | None = None
) -> tuple[dict | list | None, str | None]:
    return _github_request("GET", url, params=params)


def get_open_issues(owner: str, repo: str) -> list[dict]:
    """Fetch open issues from a GitHub repository."""

    url = f"https://api.github.com/repos/{owner}/{repo}/issues"

    params = {
        "state": "open",
        "per_page": 100,
    }

    issues, error = _github_get(url, params=params)

    if error:
        return {"error": error}

    # GitHub's issues endpoint also returns pull requests.
    # We only want actual issues.
    formatted = [
        {
            "number": issue["number"],
            "title": issue["title"],
            "url": issue["html_url"],
            "state": issue["state"],
            "labels": [label["name"] for label in issue["labels"]],
        }
        for issue in issues
        if "pull_request" not in issue
    ]

    result = {
        "repository": f"{owner}/{repo}",
        "total_returned": len(formatted),
        "issues": formatted,
    }

    if not formatted:
        result["message"] = "This repository has no open issues."

    return result


def get_user_repositories(limit: int = 30) -> dict:
    """Fetch repositories for the authenticated Github user."""

    if not get_token():
        return {"error": "Not authenticated. Ask the user to run /login first."}

    url = f"https://api.github.com/user/repos"
    params = {
        "sort": "updated",
        "per_page": min(max(limit, 1), 100),
        "affiliation": "owner,collaborator,organization_member",
    }

    repos, error = _github_get(url, params=params)
    if error:
        return {"error": error}
    formatted = [
        {
            "full_name": repo["full_name"],
            "private": repo["private"],
            "open_issues_count": repo["open_issues_count"],
            "url": repo["html_url"],
        }
        for repo in repos
    ]

    public_count = sum(1 for r in formatted if not r["private"])
    private_count = sum(1 for r in formatted if r["private"])

    return {
        "total_returned": len(formatted),
        "public_count": public_count,
        "private_count": private_count,
        "repositories": formatted,
    }


def get_issue_details(owner: str, repo: str, issue_number: int) -> dict:
    """Fetch full details for a single GitHub issue."""

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"

    issue, error = _github_get(url)
    if error:
        return {"error": error}

    return {
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],
        "url": issue["html_url"],
        "author": issue["user"]["login"] if issue.get("user") else None,
        "assignees": [a["login"] for a in issue.get("assignees", [])],
        "labels": [label["name"] for label in issue.get("labels", [])],
        "comments_count": issue.get("comments", 0),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "body": issue.get("body") or "",
    }


def get_issue_comments(
    owner: str, repo: str, issue_number: int, limit: int = 30
) -> dict:
    """Fetch comments for a GitHub issue."""

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    params = {"per_page": min(max(limit, 1), 100)}

    comments, error = _github_get(url, params=params)
    if error:
        return {"error": error}

    formatted = [
        {
            "id": c["id"],
            "author": c["user"]["login"] if c.get("user") else None,
            "created_at": c.get("created_at"),
            "body": c.get("body") or "",
        }
        for c in comments
    ]

    result = {
        "issue_number": issue_number,
        "total_returned": len(formatted),
        "comments": formatted,
    }

    if not formatted:
        result["message"] = f"Issue #{issue_number} has no comments."

    return result


def get_repository(owner: str, repo: str) -> dict:
    """Fetch metadata for a single GitHub repository."""

    url = f"https://api.github.com/repos/{owner}/{repo}"

    data, error = _github_get(url)
    if error:
        return {"error": error}

    return {
        "full_name": data["full_name"],
        "private": data["private"],
        "description": data.get("description") or "",
        "url": data["html_url"],
        "default_branch": data.get("default_branch"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues_count": data.get("open_issues_count", 0),
        "updated_at": data.get("updated_at"),
    }


def search_issues(query: str, limit: int = 20) -> dict:
    """Search GitHub issues using GitHub search syntax."""

    effective_query = query.strip()
    if (
        "is:issue" not in effective_query.lower()
        and "is:pr" not in effective_query.lower()
    ):
        effective_query = f"{effective_query} is:issue"

    url = "https://api.github.com/search/issues"
    params = {
        "q": effective_query,
        "per_page": min(max(limit, 1), 100),
    }

    response = requests.get(url, headers=_get_header(), params=params, timeout=15)
    response.raise_for_status()

    data, error = _github_get(url, params=params)
    if error:
        return {"error": error}

    items = data.get("items", [])
    formatted = [
        {
            "number": item["number"],
            "title": item["title"],
            "state": item["state"],
            "url": item["html_url"],
            "labels": [label["name"] for label in item.get("labels", [])],
        }
        for item in items
    ]

    result = {
        "query": effective_query,
        "total_count": data.get("total_count", len(formatted)),
        "total_returned": len(formatted),
        "issues": formatted,
    }

    if not formatted:
        result["message"] = "No matching issues found."

    return result


def list_pull_requests(
    owner: str, repo: str, state: str = "open", limit: int = 30
) -> dict:
    """List pull requests for a GitHub repository."""

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    params = {
        "state": state,
        "per_page": min(max(limit, 1), 100),
    }

    prs, error = _github_get(url, params=params)
    if error:
        return {"error": error}

    formatted = [
        {
            "number": pr["number"],
            "title": pr["title"],
            "state": pr["state"],
            "author": pr["user"]["login"] if pr.get("user") else None,
            "draft": pr.get("draft", False),
            "url": pr["html_url"],
            "created_at": pr.get("created_at"),
        }
        for pr in prs
    ]

    result = {
        "state": state,
        "total_returned": len(formatted),
        "pull_requests": formatted,
    }

    if not formatted:
        result["message"] = f"No {state} pull requests found."

    return result


def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """Create a new GitHub issue."""
    if not get_token():
        return {"error": "Not authenticated. Ask the user to run /login first."}

    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    payload: dict = {"title": title, "body": body}
    if labels:
        payload["labels"] = labels
    if assignees:
        payload["assignees"] = assignees

    issue, error = _github_request("POST", url, json_body=payload)
    if error:
        return {"error": error}

    return {
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],
        "url": issue["html_url"],
    }


def add_issue_comment(owner: str, repo: str, issue_number: int, body: str) -> dict:
    """Add a comment to an existing GitHub issue."""
    if not get_token():
        return {"error": "Not authenticated. Ask the user to run /login first."}

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    comment, error = _github_request("POST", url, json_body={"body": body})
    if error:
        return {"error": error}

    return {
        "id": comment["id"],
        "issue_number": issue_number,
        "url": comment["html_url"],
    }


def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    state: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """Update an issue's state ('open'/'closed'), labels, or assignees."""
    if not get_token():
        return {"error": "Not authenticated. Ask the user to run /login first."}

    payload: dict = {}
    if state is not None:
        payload["state"] = state
    if labels is not None:
        payload["labels"] = labels
    if assignees is not None:
        payload["assignees"] = assignees

    if not payload:
        return {"error": "No fields provided to update."}

    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    issue, error = _github_request("PATCH", url, json_body=payload)
    if error:
        return {"error": error}

    return {
        "number": issue["number"],
        "title": issue["title"],
        "state": issue["state"],
        "labels": [label["name"] for label in issue.get("labels", [])],
        "assignees": [a["login"] for a in issue.get("assignees", [])],
        "url": issue["html_url"],
    }
