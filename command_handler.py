import asyncio
import uuid
import os

from prompt_toolkit import PromptSession

from session_manager import (
    create_session,
    update_title,
    get_sessions,
    delete_session,
    clear_title,
)
from session_ui import select_session
from ui import (
    print_system_message,
    print_error_message,
    print_session_list,
    print_tool_list,
    show_thinking,
)
from context_manager import compact_conversation
from auth_manager import verify_token, save_token, delete_token
from langchain_core.messages import AIMessage, HumanMessage


def start_new_session():
    new_thread_id = str(uuid.uuid4())
    new_config = {"configurable": {"thread_id": new_thread_id}}

    return new_thread_id, new_config


async def handle_command(user_input, graph, app_state):
    command = user_input.strip()
    command_lower = command.lower()

    # HELP
    if command_lower == "/help":
        print_system_message("""
Available commands:
/help     - Show available commands
/tools    - List available MCP tools
/login    - Authenticate with a GitHub token
/logout   - Remove stored GitHub credentials
/clear    - Clear conversation history
/compact  - Summarise older conversation history
/new      - Start a new conversation
/sessions - List saved conversations
/switch   - Switch conversations
/rename   - Rename the current conversation
/delete   - Delete a conversation
/exit     - Exit the assistant
        """)
        return True

    # CLEAR
    if command_lower == "/clear":
        await graph.checkpointer.adelete_thread(app_state["thread_id"])

        clear_title(app_state["thread_id"])
        app_state["is_new_conversation"] = True

        print_system_message("Conversation history cleared.")
        return True

    # RENAME
    parts = command.split(maxsplit=1)

    if parts[0].lower() == "/rename":
        if len(parts) < 2:
            print_error_message("Usage: /rename <new title>")
            return True

        new_title = parts[1].strip()

        create_session(app_state["thread_id"])
        update_title(app_state["thread_id"], new_title)

        print_system_message(f"Conversation renamed to: {new_title}")
        return True

    # SWITCH
    if command_lower == "/switch":
        sessions = get_sessions()

        selected_thread_id = await select_session(sessions, "Search conversation: ")

        if selected_thread_id is None:
            print_system_message("Switch cancelled.")
            return True

        app_state["thread_id"] = selected_thread_id
        app_state["config"] = {"configurable": {"thread_id": selected_thread_id}}

        graph_state = await graph.aget_state(config=app_state["config"])

        app_state["is_new_conversation"] = not graph_state.values.get("messages")

        selected_title = next(
            (s[1] for s in sessions if s[0] == selected_thread_id), "(No title yet)"
        )

        print_system_message(f"Switched to: {selected_title}")
        return True

    # NEW
    if command_lower == "/new":
        thread_id, config = start_new_session()

        app_state["thread_id"] = thread_id
        app_state["config"] = config
        app_state["is_new_conversation"] = True

        os.system("clear")

        print_system_message("Started a new conversation.")
        return True

    # COMPACT
    if command_lower == "/compact":
        thinking_task = asyncio.create_task(show_thinking())
        try:
            success, message = await compact_conversation(graph, app_state["config"])
        finally:
            thinking_task.cancel()
            try:
                await thinking_task
            except asyncio.CancelledError:
                pass
        if success:
            print_system_message(message)
        else:
            print_error_message(message)
        return True

    # DELETE
    if command_lower == "/delete":
        sessions = get_sessions()

        selected_thread_id = await select_session(
            sessions, "Search conversation to delete: "
        )

        if selected_thread_id is None:
            print_system_message("Deletion cancelled.")
            return True

        selected_title = next(
            (s[1] for s in sessions if s[0] == selected_thread_id), "(No title yet)"
        )

        confirm_prompt = PromptSession()
        try:
            confirmation = (
                (
                    await confirm_prompt.prompt_async(
                        f"Are you sure you want to delete '{selected_title}'? (y/n): "
                    )
                )
                .strip()
                .lower()
            )
        except (EOFError, KeyboardInterrupt):
            print_system_message("Deletion cancelled.")
            return True

        if confirmation not in ["yes", "y"]:
            print_system_message("Deletion cancelled.")
            return True

        await graph.checkpointer.adelete_thread(selected_thread_id)
        delete_session(selected_thread_id)

        print_system_message(f"Conversation '{selected_title}' deleted.")

        if selected_thread_id == app_state["thread_id"]:
            thread_id, config = start_new_session()

            app_state["thread_id"] = thread_id
            app_state["config"] = config
            app_state["is_new_conversation"] = True

        return True

    # LIST SESSIONS
    if command_lower == "/sessions":
        sessions = get_sessions()

        if not sessions:
            print_system_message("No saved conversations.")
            return True

        print_session_list(sessions)
        return True

    # TOOLS
    if command_lower == "/tools":
        tools = app_state.get("tools", [])

        if not tools:
            print_system_message("No MCP tools available.")
            return True

        print_tool_list(tools)
        return True

    # LOGIN
    if command_lower == "/login":
        token_prompt = PromptSession()
        try:
            token = (
                await token_prompt.prompt_async(
                    "Enter GitHub Personal Access Token: ",
                    is_password=True,
                )
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print_system_message("Login cancelled.")
            return True
        if not token:
            print_error_message("Login cancelled — no token entered.")
            return True
        username = verify_token(token)
        if not username:
            print_error_message("Invalid or expired GitHub token.")
            return True
        if save_token(token):
            print_system_message(f"Authenticated as @{username}.")
            if not app_state["is_new_conversation"]:
                await graph.aupdate_state(
                    app_state["config"],
                    {
                        "messages": [
                            HumanMessage(
                                content="I just ran /login and authenticated with GitHub."
                            ),
                            AIMessage(
                                content=f"Great, you are now authenticated as @{username}. I will use the GitHub tools for your account."
                            ),
                        ]
                    },
                )
        else:
            print_error_message("Failed to save token to macOS Keychain.")
        return True

    # LOGOUT
    if command_lower == "/logout":
        if delete_token():
            print_system_message(
                "Logged out. GitHub credentials removed from Keychain."
            )
            if not app_state["is_new_conversation"]:
                await graph.aupdate_state(
                    app_state["config"],
                    {
                        "messages": [
                            HumanMessage(
                                content="I just ran /logout and removed my GitHub credentials."
                            ),
                            AIMessage(
                                content="Understood. You are now logged out of GitHub."
                            ),
                        ]
                    },
                )
        else:
            print_system_message("No stored GitHub credentials found.")

    # Not a command handled here
    return False
