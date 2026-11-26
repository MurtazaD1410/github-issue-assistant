# GitHub Issue Assistant — Project Handover

## 1. What is this project?

I'm building a **GitHub Issue Assistant** as a practical AI engineering portfolio project.

The goal is to build a conversational AI agent that can interact with GitHub repositories and issues through the Model Context Protocol (MCP).

The project has two independently usable components:

1. **GitHub MCP Server** — exposes GitHub functionality as reusable MCP tools. Other compatible AI clients should be able to connect to it.
2. **GitHub Issue Assistant** — a terminal-based conversational agent using Ollama, LangGraph, and the GitHub MCP server.

The project is intended to demonstrate practical knowledge of:

- Model Context Protocol (MCP)
- Tool-calling agents
- LangGraph and agent orchestration
- Conversational state and persistent memory
- Context management and summarisation
- External API integration
- Authentication and secure credential management
- Human-in-the-loop approvals
- Production-quality Python engineering

This is deliberately not another RAG project. I already have a separate RAG engineering project, so this one should focus on agents, MCP, and tool integration.

## 2. Development environment

- OS: macOS
- Hardware: Apple M3 Pro, 18 GB RAM
- Python: 3.14.6
- Local LLM runtime: Ollama
- Model: `qwen3:8b`
- Git branch: `main`
- Project directory:

`/Users/murtazadhariwala/Desktop/Development/ai/github-issue-assistant`

### Main dependencies

- `mcp`
- `langchain-mcp-adapters`
- `langgraph`
- `langchain-ollama`
- `langgraph-checkpoint-sqlite`
- `prompt-toolkit`
- `requests`

## 3. Current architecture

The project has been separated into modules:

| File | Responsibility |
|---|---|
| `agent.py` | Application entry point and interactive chat loop |
| `graph_builder.py` | Creates the LangGraph graph, configures Ollama and connects MCP tools |
| `server.py` | GitHub MCP server using FastMCP |
| `github_api.py` | GitHub REST API integration |
| `command_handler.py` | Handles terminal commands |
| `session_manager.py` | SQLite session metadata and CRUD operations |
| `session_ui.py` | Interactive session selection |
| `title_generator.py` | Generates conversation titles using Ollama |
| `ui.py` | Terminal formatting, messages, spinner and presentation |
| `checkpoints.sqlite` | LangGraph conversation checkpoints |
| `sessions.sqlite` | Conversation metadata |

The SQLite databases have separate responsibilities:

- `checkpoints.sqlite` stores actual conversation state, including messages and tool interactions.
- `sessions.sqlite` stores thread IDs, titles, creation dates and last-updated dates.

Do not merge these responsibilities unnecessarily.

## 4. Completed milestones

### Milestone 1 — GitHub API integration

Implemented `github_api.py`.

- Retrieve open GitHub issues using the GitHub REST API.
- Extract issue number, title, URL, state and labels.
- Exclude pull requests.
- Handle HTTP errors using `raise_for_status()`.

Tested against public repositories.

### Milestone 2 — GitHub MCP server

Implemented `server.py` using FastMCP.

- Created the `get_issues` MCP tool.
- Uses stdio transport.
- Tested using MCP Inspector.
- Created a standalone MCP client to connect, list and call tools.

### Milestone 3 — LangGraph and Ollama integration

- Connected Ollama using `ChatOllama`.
- Used `qwen3:8b`.
- Retrieved MCP tools through `MultiServerMCPClient`.
- Bound tools to the LLM.
- Created a LangGraph workflow using `StateGraph`, `MessagesState`, `ToolNode` and `tools_condition`.
- Added a system prompt to reduce hallucinations and ensure responses rely on actual tool results.

### Milestone 4 — Interactive terminal chat

- Implemented a continuous conversation loop.
- Added `/exit`, `/help` and `/clear`.
- Fixed command handling and message history issues.

### Milestone 5 — Persistent conversation history

- Installed `langgraph-checkpoint-sqlite`.
- Integrated `AsyncSqliteSaver`.
- Conversations persist across application restarts.
- Added unique thread IDs.
- Implemented conversation clearing through LangGraph's checkpointer.

### Milestone 6 — Terminal autocomplete

- Installed `prompt-toolkit`.
- Added command autocomplete.
- Added a custom `AutoSuggest` implementation for inline ghost-text suggestions.
- Added command dropdown completion.

### Milestone 7 — Session management

Created `session_manager.py` and `session_ui.py`.

Implemented:

- `/new` — start a new conversation.
- `/sessions` — list saved conversations.
- `/switch` — switch between conversations.
- `/rename` — rename a conversation.
- `/delete` — delete a conversation.
- `/clear` — clear the current conversation without deleting its session.

Session deletion removes both the LangGraph checkpoint and the session metadata.

Conversation titles are generated using Ollama from the first user message. Manually renamed titles are preserved unless explicitly cleared.

### Milestone 8 — Refactoring and terminal UI

Separated the application into dedicated modules.

Implemented terminal presentation helpers:

- Styled user, assistant, system and error messages.
- Consistent message spacing.
- Separator lines.
- A formatted goodbye message.
- Animated thinking indicator with changing phrases such as:
  - Thinking
  - Pondering
  - Working through it
  - Putting things together
- Muted grey spinner styling.
- Fixed leftover terminal characters when longer phrases are replaced by shorter ones.

MCP INFO logs were also identified as a UI issue, with logging-level suppression proposed. Verify that this is working in the current code.

## 5. Immediate next task — Milestone 8.5: `/compact`

This is the next feature to implement. It has not yet been implemented.

The goal is to provide context compaction similar to Claude Code.

Expected behaviour:

1. Read the current conversation history from the LangGraph checkpoint.
2. Identify older messages that can be summarised.
3. Use Qwen3 to generate a concise summary of important context.
4. Preserve important facts, decisions, user preferences, outstanding tasks and relevant technical details.
5. Preserve the most recent messages.
6. Replace the older history with the summary.
7. Keep the same thread ID, session title and conversation.

Implementation considerations:

- Create a separate `context_manager.py`.
- Investigate LangGraph's `RemoveMessage` and `REMOVE_ALL_MESSAGES` mechanisms.
- Use `graph.aget_state()` to retrieve the existing conversation state.
- Use `graph.aupdate_state()` to update the checkpoint.
- Preserve the original system instructions.
- Do not leave orphaned tool calls or tool results.
- Keep recent conversational turns intact.
- Avoid duplicate system messages.
- Handle empty conversations and failed summarisation.
- Do not overwrite the existing checkpoint until a valid summary has been generated.

Add `/compact` to the command autocomplete list and `/help`.

Test that the assistant remembers earlier context after compaction and can continue the conversation naturally.

## 6. Upcoming major milestones

### Milestone 9 — GitHub authentication

Implement GitHub authentication.

Expected functionality:

- `/login` to authenticate.
- Secure token storage.
- Authenticated GitHub API requests.
- Higher API rate limits.
- Access to private repositories when authorised.
- `/logout` to remove the stored credentials.
- Ability to list the authenticated user's repositories.

Security requirements:

- Never print tokens in terminal output.
- Never store plaintext credentials in Git.
- Use an appropriate secure credential-storage mechanism on macOS.
- Keep public unauthenticated requests working.

Investigate the appropriate GitHub authentication flow before implementing it.

### Milestone 10 — Expand the GitHub MCP server

Add useful reusable MCP tools.

Potential tools:

- `list_repositories`
- `get_repository`
- `get_issues`
- `get_issue_details`
- `search_issues`
- `get_issue_comments`
- `list_pull_requests`

The MCP server must remain independent of LangGraph and Ollama.

### Milestone 11 — Improve agent reliability

Improve the assistant's decision-making and tool usage.

Focus on:

- Better tool selection.
- Correct interpretation of tool results.
- Structured tool outputs.
- Handling empty results.
- API errors and rate limits.
- Avoiding hallucinated issue numbers and repository information.
- Better system instructions.
- Clear separation between tool execution and final responses.

Do not assume that a system prompt alone guarantees reliability.

### Milestone 12 — GitHub write operations and human approval

Allow the assistant to perform actions, not just retrieve information.

Potential functionality:

- Create GitHub issues.
- Add comments.
- Update issue labels.
- Change issue state.
- Assign issues.

Important requirement:

**Destructive or externally visible actions must require explicit user approval before execution.**

Implement this using LangGraph human-in-the-loop mechanisms, such as interrupts and resume.

Demonstrate the difference between read-only tools and write tools.

### Milestone 13 — Production readiness

Improve the project for real-world usage.

Potential work:

- Configuration management.
- Environment variables.
- Logging.
- Error handling.
- Unit and integration tests.
- API validation.
- Secure credential management.
- Better project documentation.
- Architecture diagrams.
- Installation instructions.
- Docker support if useful.

### Milestone 14 — MCP interoperability

Make the GitHub MCP server usable by other compatible clients.

Investigate and test integrations with:

- Claude Desktop.
- VS Code and compatible MCP clients.
- Other MCP-compatible applications.

Keep the MCP server independent from the terminal assistant.

Understand the distinction between local stdio connections and remotely accessible MCP servers. Do not assume every client supports the same transport or authentication setup.

## 7. Development rules

Please follow these rules throughout development:

1. Work incrementally, one small step at a time.
2. Explain what each change does and why it is necessary.
3. Do not dump an entire implementation at once.
4. Prefer simple solutions over unnecessary abstraction.
5. Inspect the existing code before suggesting modifications.
6. Do not rewrite working modules without a clear reason.
7. Do not introduce unnecessary dependencies.
8. Avoid blanket `Any` types and poorly structured code.
9. Test each meaningful change before moving to the next step.
10. Explain errors and help debug them rather than immediately replacing the implementation.
11. Preserve the existing architecture unless a change is justified.
12. Never automatically commit, push, reset, rebase, or rewrite Git history.
13. Ask before making destructive changes.
14. Do not expose credentials or tokens in logs.

## 8. How to continue

First, inspect the existing repository and understand its current implementation.

Do not immediately modify files.

Start by checking:

- Current project structure.
- `agent.py`.
- `graph_builder.py`.
- `command_handler.py`.
- `session_manager.py`.
- `ui.py`.
- `title_generator.py`.

Then report:

1. What is already implemented.
2. Whether the implementation matches this handover.
3. Any differences or potential bugs.
4. The smallest next step for implementing `/compact`.

We will finish `/compact`, test it, and then proceed to Milestone 9: GitHub authentication.

The objective is to understand and build a genuinely useful AI engineering project, not merely generate code that appears impressive.
