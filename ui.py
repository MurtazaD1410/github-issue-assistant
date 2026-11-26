import os
import sys
import tty
import termios
import select
import asyncio

from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown

console = Console()

STYLE = Style.from_dict(
    {
        "user-label": "bold fg:#60a5fa",
        "assistant-label": "bold fg:#4ade80",
        "system-label": "bold fg:#facc15",
        "error-label": "bold fg:#f87171",
        "tool-label": "fg:#9ca3af",
        "description": "fg:#9ca3af",
        "item-title": "bold fg:#ffffff",
        "meta-key": "fg:#93c5fd",
        "separator": "fg:#555555",
        "mascot": "fg:#4ade80",
        "mascot-eye": "bg:#4ade80 fg:#111827",
    }
)


def print_user_prompt():
    return FormattedText(
        [
            ("class:user-label", "You "),
            ("class:separator", "› "),
        ]
    )


def print_assistant_message(content: str):
    print()
    print_formatted_text(
        FormattedText(
            [
                ("class:assistant-label", "Assistant ›"),
            ]
        ),
        style=STYLE,
    )
    console.print(Markdown(content.strip()))
    print()


def print_system_message(content: str):
    print()
    print_formatted_text(
        FormattedText(
            [
                ("class:system-label", "System "),
                ("", content.strip()),
            ]
        ),
        style=STYLE,
    )
    print()


def print_error_message(content: str):
    print()
    print_formatted_text(
        FormattedText(
            [
                ("class:error-label", "Error "),
                ("", content.strip()),
            ]
        ),
        style=STYLE,
    )
    print()


def print_separator():
    print_formatted_text(
        FormattedText(
            [
                ("class:separator", "─" * 50),
            ]
        ),
        style=STYLE,
    )


def print_session_list(sessions):
    print()
    print_formatted_text(
        FormattedText(
            [
                ("class:system-label", "Saved conversations"),
            ]
        ),
        style=STYLE,
    )

    for index, saved_session in enumerate(sessions, start=1):
        thread_id, title, created_at, updated_at = saved_session
        display_title = title or "(No title yet)"

        print_formatted_text(
            FormattedText(
                [
                    ("class:item-title", f"  {index}. {display_title}\n"),
                    ("class:meta-key", "     ID: "),
                    ("class:description", f"{thread_id[:8]}\n"),
                    ("class:meta-key", "     Last updated: "),
                    ("class:description", f"{updated_at}"),
                ]
            ),
            style=STYLE,
        )

    print()


async def show_thinking():
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    phrases = [
        "Thinking",
        "Pondering",
        "Working through it",
        "Putting things together",
    ]

    index = 0

    try:
        while True:
            frame = frames[index % len(frames)]
            phrase = phrases[(index // len(frames)) % len(phrases)]

            line = f"{frame} {phrase}... (Esc to cancel)"

            sys.stdout.write(f"\r\033[2K\033[38;5;245m{line}\033[0m")
            sys.stdout.flush()

            await asyncio.sleep(0.12)
            index += 1

    finally:
        sys.stdout.write("\r\033[2K")
        sys.stdout.flush()


def print_goodbye():
    print()
    print_formatted_text(
        FormattedText(
            [
                ("class:assistant-label", "Goodbye "),
                ("class:separator", "› "),
                ("", "Thanks for using GitHub Issue Assistant!"),
            ]
        ),
        style=STYLE,
    )
    print()


def print_tool_usage(tool_name: str, args: dict | None = None):
    sys.stdout.write("\r\033[2K")
    sys.stdout.flush()

    args_str = ""
    if args:
        formatted = ", ".join(f"{k}={v!r}" for k, v in args.items())
        args_str = f"({formatted})"

    print_formatted_text(
        FormattedText(
            [
                ("class:separator", "  • "),
                ("class:tool-label", f"Using tool: {tool_name}{args_str}"),
            ]
        ),
        style=STYLE,
    )


def print_tool_list(tools):
    print()
    print_formatted_text(
        FormattedText(
            [
                ("class:system-label", "Available MCP tools"),
            ]
        ),
        style=STYLE,
    )

    for index, tool in enumerate(tools, start=1):
        description = (tool.description or "").strip().splitlines()[0]
        parts = [("class:item-title", f"  {index}. {tool.name}")]
        if description:
            parts.append(("class:description", f"\n     {description}"))

        print_formatted_text(FormattedText(parts), style=STYLE)

    print()


async def watch_for_escape(on_escape):
    """Listen for a standalone Esc key press and invoke on_escape."""
    if not sys.stdin.isatty():
        return

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setcbreak(fd)
        while True:
            ready, _, _ = select.select([fd], [], [], 0)
            if ready:
                ch = os.read(fd, 1)
                if ch == b"\x1b":
                    # Ignore multi-byte escape sequences (e.g. arrow keys)
                    more, _, _ = select.select([fd], [], [], 0.02)
                    if not more:
                        on_escape()
                        return
                    os.read(fd, 16)
            await asyncio.sleep(0.05)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


async def show_startup_animation(
    model_name: str,
    tool_count: int,
    username: str | None = None,
):
    steps = [
        "Initialising local memory",
        "Connecting to GitHub MCP server",
        f"Loaded {tool_count} MCP tools",
    ]
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    for step in steps:
        for i in range(6):
            frame = frames[i % len(frames)]
            sys.stdout.write(f"\r\033[2K\033[38;5;245m{frame} {step}...\033[0m")
            sys.stdout.flush()
            await asyncio.sleep(0.05)

    sys.stdout.write("\r\033[2K")
    sys.stdout.flush()

    auth_text = f"@{username}" if username else "Not logged in (/login)"

    # Each frame is (row1, blink, row3) — all exactly 9 chars wide
    dance_frames = [
        (" ▄█████▄ ", False, " ▀▘   ▝▀ "),
        ("▘▄█████▄ ", False, " ▝▀   ▀▘ "),
        (" ▀█████▀ ", True, "  ▀▘ ▝▀  "),
        (" ▄█████▄▝", False, " ▀▘   ▝▀ "),
        (" ▄█████▄ ", False, " ▀▘   ▝▀ "),
    ]

    print()
    sys.stdout.write("\033[?25l")  # hide cursor during dance
    sys.stdout.flush()

    try:
        for idx, (row1, blink, row3) in enumerate(dance_frames * 2):
            if idx > 0:
                sys.stdout.write("\033[3A\r")
                sys.stdout.flush()

            face = (
                [("class:mascot", "▐███████▌")]
                if blink
                else [
                    ("class:mascot", "▐█"),
                    ("class:mascot-eye", "▪"),
                    ("class:mascot", "███"),
                    ("class:mascot-eye", "▪"),
                    ("class:mascot", "█▌"),
                ]
            )

            print_formatted_text(
                FormattedText(
                    [
                        ("class:mascot", row1),
                        ("class:item-title", "   GitHub Issue Assistant\n"),
                        *face,
                        (
                            "class:description",
                            f"   {model_name} · {tool_count} MCP tools\n",
                        ),
                        ("class:mascot", row3),
                        ("class:description", f"   {auth_text} · /help for commands"),
                    ]
                ),
                style=STYLE,
            )
            await asyncio.sleep(0.14)
    finally:
        sys.stdout.write("\033[?25h\n")  # restore cursor
        sys.stdout.flush()


def print_approval_prompt(actions: list[dict]):
    print()
    print_formatted_text(
        FormattedText(
            [
                ("class:system-label", "Approval required for write action"),
            ]
        ),
        style=STYLE,
    )

    for action in actions:
        parts = [("class:item-title", f"  • {action['name']}\n")]
        for key, value in action.get("args", {}).items():
            parts.append(("class:meta-key", f"    {key}: "))
            parts.append(("class:description", f"{value}\n"))
        print_formatted_text(FormattedText(parts), style=STYLE)
