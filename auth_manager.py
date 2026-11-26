import shlex
import subprocess
import requests

SERVICE_NAME = "github-issue-assistant"
ACCOUNT_NAME = "github_token"
SECURITY_BIN = "/usr/bin/security"


def save_token(token: str) -> bool:
    """Store the GitHub token securely in macOS Keychain"""
    command = (
        f"add-generic-password -U -a {shlex.quote(ACCOUNT_NAME)} "
        f"-s {shlex.quote(SERVICE_NAME)} -w {shlex.quote(token)}\n"
    )

    result = subprocess.run(
        [SECURITY_BIN, "-i"], input=command, text=True, capture_output=True
    )

    return result.returncode == 0


def get_token() -> str | None:
    """Retrieve the GitHub token from macOS Keychain, or None if not set."""
    result = subprocess.run(
        [
            SECURITY_BIN,
            "find-generic-password",
            "-a",
            ACCOUNT_NAME,
            "-s",
            SERVICE_NAME,
            "-w",
        ],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        return None

    token = result.stdout.strip()
    return token if token else None


def delete_token() -> bool:
    """Delete the GitHub token from macOS Keychain"""

    result = subprocess.run(
        [
            SECURITY_BIN,
            "delete-generic-password",
            "-a",
            ACCOUNT_NAME,
            "-s",
            SERVICE_NAME,
        ],
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def verify_token(token: str) -> str | None:
    """Validate a GitHub toekn and return the authenticated username, or None."""
    try:
        response = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )

        if response.status_code == 200:
            return response.json().get("login")
        else:
            return None
    except requests.RequestException:
        return None
