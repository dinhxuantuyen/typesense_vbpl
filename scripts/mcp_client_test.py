"""Test nhanh MCP server: initialize -> list tools -> call vai tool."""
import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/mcp"


async def main():
    async with streamablehttp_client(URL) as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])

            r = await session.call_tool("collection_stats", {})
            print("\nSTATS:", r.content[0].text)

            r = await session.call_tool("search_legal_articles",
                                        {"query": "nhiem vu quyen han cua ban kiem soat", "top_k": 2})
            print("\nSEARCH:", r.content[0].text[:800])

            # get_legal_article tren 1 Dieu dai (bi sub-chunk) -> kiem tra ghep part
            r = await session.call_tool("get_legal_article", {"chunk_id": "709806-dieu-18"})
            txt = r.content[0].text
            print("\nGET_ARTICLE (dau):", txt[:300])
            print("... (do dai content ghep lai =", len(txt), "ky tu)")


if __name__ == "__main__":
    asyncio.run(main())
