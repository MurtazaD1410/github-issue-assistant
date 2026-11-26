import sys
from pathlib import Path
from typing import Literal

from config import MCP_SERVER_PATH, OLLAMA_MODEL, OLLAMA_TEMPERATURE

from langchain_core.messages import ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.types import Command, interrupt

BASE_DIR = Path(__file__).resolve().parent

WRITE_TOOLS = {"create_issue", "add_issue_comment", "update_issue"}


async def build_graph(checkpointer):
    # 1. Connect to the GitHub MCP server
    client = MultiServerMCPClient(
        {
            "github": {
                "command": sys.executable,
                "args": [str(MCP_SERVER_PATH)],
                "transport": "stdio",
            }
        }
    )

    # 2. Retrieve available MCP tools
    tools = await client.get_tools()

    # 3. Initialize Ollama and bind the tools
    llm = ChatOllama(model=OLLAMA_MODEL, temperature=OLLAMA_TEMPERATURE)

    model = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}

    # 4. Define the model node
    async def call_model(state: MessagesState):
        response = await model.ainvoke(state["messages"])
        return {"messages": [response]}

    def route_after_model(
        state: MessagesState,
    ) -> Literal["human_approval", "__end__"]:
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "human_approval"
        return END

    async def human_approval(
        state: MessagesState,
    ) -> Command[Literal["tools", "call_model"]]:
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", [])
        write_calls = [tc for tc in tool_calls if tc["name"] in WRITE_TOOLS]

        if not write_calls:
            return Command(goto="tools")

        approved = interrupt(
            {
                "type": "tool_approval",
                "actions": [
                    {"name": tc["name"], "args": tc["args"]} for tc in write_calls
                ],
            }
        )

        if approved:
            return Command(goto="tools")

        result_messages = []
        for tc in tool_calls:
            if tc["name"] in WRITE_TOOLS:
                result_messages.append(
                    ToolMessage(
                        tool_call_id=tc["id"],
                        name=tc["name"],
                        content=(
                            "Action cancelled: the user chose 'no' at the confirmation prompt. "
                            "Briefly confirm that the action was cancelled as requested. "
                            "Do not mention authentication or /login."
                        ),
                    )
                )
            else:
                tool_obj = tools_by_name.get(tc["name"])
                try:
                    output = await tool_obj.ainvoke(tc["args"]) if tool_obj else f"Unknown tool: {tc['name']}"
                except Exception as e:
                    output = f"Tool error: {e}"
                result_messages.append(
                    ToolMessage(
                        tool_call_id=tc["id"],
                        name=tc["name"],
                        content=str(output),
                    )
                )

        return Command(update={"messages": result_messages}, goto="call_model")

    # 5. Build the LangGraph workflow
    builder = StateGraph(MessagesState)

    builder.add_node("call_model", call_model)
    builder.add_node("human_approval", human_approval)
    builder.add_node("tools", ToolNode(tools))

    builder.add_edge(START, "call_model")
    builder.add_conditional_edges("call_model", route_after_model)
    builder.add_edge("tools", "call_model")

    # 6. Compile with the supplied checkpointer
    return builder.compile(checkpointer=checkpointer), tools
