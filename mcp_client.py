"""
pip install mcp-use
pip install langchain-openai
pip install matplotlib
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

# Load environment variables from .env file
load_dotenv()


async def main():
    current_date = datetime.now().strftime("%Y-%m-%d")

    config = {
        "mcpServers": {
            "google_search_console_server": {
                "command": "python",
                "args": ["google_search_console/server.py"],
            }
        }
    }

    client = MCPClient.from_dict(config)
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

    system_rules = f"""
        You are an MCP agent with access to the Google Search Console tools.

        CURRENT DATE: 30-09-2025
        CURRENT MONTH: September 2025
        CURRENT YEAR: 2025
        CURRENT DAY: 30

         Google Search Console Rules:
         1. If the question relates to site performance, queries, clicks, impressions, or position, use the GSC tools.
         2. If a site (property) is mentioned, you must provide the property ID in the format required (`sc-domain:example.com` or full URL).
         3. For "top queries", "pages", or "countries", use the appropriate discovery tools (e.g., search_analytics).
         4. Always return the raw data (clicks, impressions, CTR, position) unless the user requests a summary.
         5. If unsure, first list available resources from the GSC server before attempting queries.

            ##  DIMENSION DETECTION RULES
                 Auto-detect dimensions from user queries:
                 - "by query" / "queries" / "search terms" / "keywords" → include "query"
                 - "by page" / "pages" / "URLs" / "landing pages" → include "page"
                 - "by country" / "countries" / mention of specific countries → include "country"
                 - "by device" / "mobile" / "desktop" / "tablet" / "device-wise" → include "device"
                 - "daily" / "day-wise" / "trends" / "by date" → include "date"
                 Multi-dimensional queries:
                 - "by query and device" → dimensions: ["query", "device"]
                 - "by page and country" → dimensions: ["page", "country"]
                 - "query performance by device" → dimensions: ["query", "device"]
                 - "country and device breakdown" → dimensions: ["country", "device"]
                 - "page + query + country" → dimensions: ["page", "query", "country"]
    
    """

    agent = MCPAgent(llm=llm, client=client, max_steps=5, system_prompt=system_rules)

    result = await agent.run(
        "Which search terms are trending compared to last month?",
        max_steps=10,
    )
    print("Result:", result)


if __name__ == "__main__":
    asyncio.run(main())