from mcp.server.fastmcp import FastMCP
import github_api
import logging

logging.basicConfig(level=logging.WARNING)

# Connect the MCP server
mcp = FastMCP("Github Issue Assistant")


@mcp.tool()
def get_issues(owner: str, repo: str) -> dict:
    """
    Retrieve all open issues from a GitHub repository.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
    """
    return github_api.get_open_issues(owner, repo)


@mcp.tool()
def list_repos(limit: int = 30) -> dict:
    """
    List repositories accessible to the authenticated GitHub user
    (including private repositories if authorised).

    Args:
        limit: Maximum number of repositories to return (1-100).
    """
    return github_api.get_user_repositories(limit=limit)


@mcp.tool()
def get_issue_details(owner: str, repo: str, issue_number: int) -> dict:
    """
    Retrieve full details for a single GitHub issue.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        issue_number: Issue number.
    """
    return github_api.get_issue_details(owner, repo, issue_number)


@mcp.tool()
def get_issue_comments(
    owner: str, repo: str, issue_number: int, limit: int = 30
) -> dict:
    """
    Retrieve comments for a GitHub issue.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        issue_number: Issue number.
        limit: Maximum number of comments to return (1-100).
    """
    return github_api.get_issue_comments(owner, repo, issue_number, limit)


@mcp.tool()
def get_repository(owner: str, repo: str) -> dict:
    """
    Get metadata for a GitHub repository (stars, language, default branch, open issues).

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
    """
    return github_api.get_repository(owner, repo)


@mcp.tool()
def search_issues(query: str, limit: int = 20) -> dict:
    """
    Search GitHub issues using GitHub search syntax (e.g., 'repo:owner/name bug is:open').

    Args:
        query: GitHub issue search query.
        limit: Maximum number of results to return (1-100). Default is 20.
    """
    return github_api.search_issues(query, limit=limit)


@mcp.tool()
def list_pull_requests(
    owner: str, repo: str, state: str = "open", limit: int = 30
) -> dict:
    """
    List pull requests for a GitHub repository.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        state: Filter by PR state: 'open', 'closed', or 'all'. Default is 'open'.
        limit: Maximum number of pull requests to return (1-100). Default is 30.
    """
    return github_api.list_pull_requests(owner, repo, state=state, limit=limit)


@mcp.tool()
def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """
    Create a new issue in a GitHub repository.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        title: Issue title.
        body: Optional issue description.
        labels: Optional list of label names.
        assignees: Optional list of GitHub usernames to assign.
    """
    return github_api.create_issue(
        owner, repo, title, body=body, labels=labels, assignees=assignees
    )


@mcp.tool()
def add_issue_comment(owner: str, repo: str, issue_number: int, body: str) -> dict:
    """
    Add a comment to a GitHub issue.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        issue_number: Issue number.
        body: Comment text.
    """
    return github_api.add_issue_comment(owner, repo, issue_number, body)


@mcp.tool()
def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    state: str | None = None,
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> dict:
    """
    Update a GitHub issue's state ('open' or 'closed'), labels, or assignees.

    Args:
        owner: GitHub repository owner.
        repo: GitHub repository name.
        issue_number: Issue number.
        state: Optional new state ('open' or 'closed').
        labels: Optional replacement list of label names.
        assignees: Optional replacement list of assignee usernames.
    """
    return github_api.update_issue(
        owner, repo, issue_number, state=state, labels=labels, assignees=assignees
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
