from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_ollama import ChatOllama
from langgraph.graph.message import REMOVE_ALL_MESSAGES, RemoveMessage
from config import KEEP_RECENT_TURNS, OLLAMA_MODEL, OLLAMA_TEMPERATURE

llm = ChatOllama(model=OLLAMA_MODEL, temperature=OLLAMA_TEMPERATURE)


def _format_messages_for_summary(messages: list[BaseMessage]) -> str:
    lines: list[str] = []

    for msg in messages:
        if isinstance(msg, HumanMessage):
            lines.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            if msg.content:
                lines.append(f"Assistant: {msg.content}")
            elif msg.tool_calls:
                tool_names = ", ".join(tc["name"] for tc in msg.tool_calls)
                lines.append(f"Assistant called tools: {tool_names}")
        elif isinstance(msg, ToolMessage):
            content = str(msg.content)
            if len(content) > 500:
                content = content[:500] + "... [truncated]"
            lines.append(f"Tool ({msg.name}): {content}")
    return "\n".join(lines)


async def compact_conversation(
    graph, config: dict, keep_recent_turns: int = KEEP_RECENT_TURNS
) -> tuple[bool, str]:
    state = await graph.aget_state(config)
    messages: list[BaseMessage] = state.values.get("messages", [])

    if not messages:
        return False, "Nothing to compact - the conversation is empty."

    system_message = next((m for m in messages if isinstance(m, SystemMessage)), None)

    conversation_messages = [m for m in messages if not isinstance(m, SystemMessage)]

    human_indices = [
        i for i, m in enumerate(conversation_messages) if isinstance(m, HumanMessage)
    ]

    if len(human_indices) <= keep_recent_turns:
        return False, "Conversation is too short to compact."

    split_index = human_indices[-keep_recent_turns]
    older_messages = conversation_messages[:split_index]
    recent_messages = conversation_messages[split_index:]

    if not older_messages:
        return False, "Conversation is too short to compact."

    transcript = _format_messages_for_summary(older_messages)

    prompt = f"""Summarise the following conversation history concisely so an AI assistant can continue the conversation seamlessly.
Preserve:
- Key facts, repository names, and issue numbers discussed
- User preferences and decisions made
- Outstanding tasks or open questions
- Relevant technical details from tool results
Rules:
- Be concise and factual.
- Do not invent any details not present in the transcript.
- Return only the summary.
Conversation transcript:
{transcript}"""

    try:
        response = await llm.ainvoke(prompt)
        summary = str(response.content).strip()
    except Exception as e:
        return False, f"Summarisation failed: {e}"

    if not summary:
        return False, "Summarisation returned an empty summary; history unchanged."

    new_messages: list[BaseMessage] = []
    if system_message is not None:
        new_messages.append(system_message)

    new_messages.append(
        HumanMessage(content=f"[Summary of earlier conversation]\n{summary}")
    )

    new_messages.extend(recent_messages)

    await graph.aupdate_state(
        config,
        {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *new_messages]},
    )

    return (
        True,
        f"Compacted {len(older_messages)} older messages into a summary "
        f"(kept {len(recent_messages)} recent messages).",
    )
