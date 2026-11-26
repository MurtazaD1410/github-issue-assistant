from prompt_toolkit import PromptSession
from prompt_toolkit.completion import FuzzyWordCompleter


async def select_session(sessions, prompt_text):
    if not sessions:
        return None

    session_options = {
        f"{title or '(No title yet)'} [{thread_id[:8]}]": thread_id
        for thread_id, title, created_at, updated_at in sessions
    }

    prompt = PromptSession(completer=FuzzyWordCompleter(list(session_options.keys())))

    selected_option = (
        await prompt.prompt_async(prompt_text, complete_while_typing=True)
    ).strip()

    return session_options.get(selected_option)
