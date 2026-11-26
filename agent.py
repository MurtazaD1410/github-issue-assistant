import asyncio
from pathlib import Path
from config import CHECKPOINTS_DB_PATH, OLLAMA_MODEL, BASE_DIR

from ui import (
    print_assistant_message,
    show_startup_animation,
    print_approval_prompt,
    print_system_message,
    print_user_prompt,
    print_tool_usage,
    watch_for_escape,
    print_separator,
    show_thinking,
    print_goodbye,
    STYLE,
)

from auth_manager import get_token, verify_token

from prompt_toolkit import PromptSession
from prompt_toolkit.application import get_app
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph.message import RemoveMessage
from langgraph.types import Command
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from graph_builder import build_graph
from title_generator import generate_title
from command_handler import handle_command, start_new_session
from session_manager import (
    initialize_database,
    update_title,
    touch_session,
    get_session,
    create_session,
)

commands = [
    "/help",
    "/login",
    "/logout",
    "/tools",
    "/clear",
    "/compact",
    "/new",
    "/sessions",
    "/switch",
    "/rename",
    "/delete",
    "/exit",
]

command_completer = WordCompleter(commands, ignore_case=True, sentence=True)


class CommandAutoSuggest(AutoSuggest):

    def get_suggestion(self, buffer, document):
        text = document.text_before_cursor

        if not text.startswith("/") or " " in text:
            return None

        for command in commands:
            if command.startswith(text) and command != text:
                return Suggestion(command[len(text) :])

        return None


async def main():

    initialize_database()

    async with AsyncSqliteSaver.from_conn_string(
        str(CHECKPOINTS_DB_PATH)
    ) as checkpointer:
        graph, tools = await build_graph(checkpointer)

        thread_id, config = start_new_session()

        app_state = {
            "thread_id": thread_id,
            "config": config,
            "is_new_conversation": True,
            "tools": tools,
        }

        # 6. System prompt
        system_message = SystemMessage(
            content=(
                "You are a GitHub issue assistant. "
                "Always base your answers on the actual results "
                "returned by GitHub tools. "
                "Never invent issue numbers, titles, or usernames. "
                "If the tool returns an empty list, explicitly say "
                "that the repository has no open issues. "
                "Never use placeholder examples as real data. "
                "Authentication state can change between turns when the user "
                "runs /login or /logout, so always call the appropriate GitHub "
                "tool rather than assuming authentication status from earlier turns."
                "Never estimate counts or use '...' to abbreviate lists; "
                "report the exact counts and items returned by the tool."
                "If a tool returns an 'error' field, report that exact error "
                "clearly to the user and do not guess or fabricate data."
            )
        )

        token = get_token()
        username = verify_token(token) if token else None
        await show_startup_animation(OLLAMA_MODEL, len(tools), username)

        kb = KeyBindings()

        @kb.add(
            "enter",
            filter=Condition(lambda: not get_app().current_buffer.text.strip()),
        )
        def _(event):
            # Ignore Enter on empty input so it doesn't print another prompt line
            pass

        session = PromptSession(
            completer=command_completer,
            auto_suggest=CommandAutoSuggest(),
            complete_while_typing=True,
            key_bindings=kb,
            style=STYLE,
        )

        # 8. looping for chat like feel
        while True:
            user_input = (await session.prompt_async(print_user_prompt())).strip()

            if not user_input:
                continue

            if user_input.lower() == "/exit":
                print_goodbye()
                break

            handled = await handle_command(user_input, graph, app_state)

            if handled:
                continue

            input_messages = [{"role": "user", "content": user_input}]

            if app_state["is_new_conversation"]:
                input_messages.insert(0, system_message)

            graph_input = {"messages": input_messages}
            cancelled = False
            final_content = ""
            title = None

            while True:

                async def run_agent_turn(current_input):
                    content = ""
                    interrupt_data = None
                    async for chunk in graph.astream(
                        current_input,
                        config=app_state["config"],
                        stream_mode="updates",
                    ):
                        if "__interrupt__" in chunk:
                            interrupt_data = chunk["__interrupt__"][0].value
                            break
                        if "call_model" in chunk:
                            msg = chunk["call_model"]["messages"][-1]
                            tool_calls = getattr(msg, "tool_calls", None)
                            if tool_calls:
                                for tc in tool_calls:
                                    print_tool_usage(tc["name"], tc.get("args"))
                            else:
                                content = msg.content
                    return content, interrupt_data

                agent_task = asyncio.create_task(run_agent_turn(graph_input))
                thinking_task = asyncio.create_task(show_thinking())
                escape_task = asyncio.create_task(watch_for_escape(agent_task.cancel))
                interrupt_payload = None

                try:
                    final_content, interrupt_payload = await agent_task
                except asyncio.CancelledError:
                    cancelled = True
                    state = await graph.aget_state(app_state["config"])
                    messages = state.values.get("messages", [])
                    if messages:
                        last_msg = messages[-1]
                        if isinstance(last_msg, AIMessage) and getattr(
                            last_msg, "tool_calls", None
                        ):
                            await graph.aupdate_state(
                                app_state["config"],
                                {"messages": [RemoveMessage(id=last_msg.id)]},
                            )
                finally:
                    escape_task.cancel()
                    thinking_task.cancel()
                    for task in (escape_task, thinking_task):
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

                if cancelled:
                    break

                if interrupt_payload is not None:
                    print_approval_prompt(interrupt_payload.get("actions", []))
                    approval_prompt = PromptSession()
                    try:
                        answer = (
                            (
                                await approval_prompt.prompt_async(
                                    "Approve this action? (y/n): "
                                )
                            )
                            .strip()
                            .lower()
                        )
                        approved = answer in ("y", "yes")
                    except (EOFError, KeyboardInterrupt):
                        approved = False

                    graph_input = Command(resume=approved)
                    continue

                create_session(app_state["thread_id"])
                touch_session(app_state["thread_id"])

                if app_state["is_new_conversation"]:
                    session_record = get_session(app_state["thread_id"])
                    has_title = session_record and session_record[1]
                    if not has_title:
                        title = await generate_title(user_input)
                break

            if cancelled:
                print_system_message("Request cancelled.")
                print_separator()
                continue

            if app_state["is_new_conversation"]:
                if title:
                    update_title(app_state["thread_id"], title)
                app_state["is_new_conversation"] = False

            print_assistant_message(final_content)
            print_separator()


if __name__ == "__main__":
    asyncio.run(main())
