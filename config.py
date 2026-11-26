import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# LLM settings
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0"))

# Storage paths
CHECKPOINTS_DB_PATH = Path(
    os.getenv("CHECKPOINTS_DB_PATH", str(BASE_DIR / "checkpoints.sqlite"))
)
SESSIONS_DB_PATH = Path(
    os.getenv("SESSIONS_DB_PATH", str(BASE_DIR / "sessions.sqlite"))
)

# MCP server
MCP_SERVER_PATH = BASE_DIR / "server.py"

# Context compaction
KEEP_RECENT_TURNS = int(os.getenv("KEEP_RECENT_TURNS", "2"))

# GitHub API
GITHUB_API_TIMEOUT = int(os.getenv("GITHUB_API_TIMEOUT", "15"))
