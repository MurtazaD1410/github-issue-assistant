import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    server_params= StdioServerParameters(
        command= "python",
        args= [ "server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            
            # Initialize mcp connection
            await session.initialize()

            # Discover available tools
            tools= await session.list_tools()

            print("Available tools:")
            for tool in tools.tools:
                print(f"- {tool.name}: {tool.description}")
            
            # Call our Github issue tool
            result= await session.call_tool(
                "get_issues",
                arguments={
                    "owner": "asmeurer",
                    "repo": "GitHub-Issues-Test"
                }
            )

            print("\n Tool result:")
            for content in result.content:
                if content.type=="text":
                    print(content.text)

if __name__ == "__main__":
    asyncio.run(main())
