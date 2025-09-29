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
            "chart_server": {
                "command": "python",
                "args": ["mcp_chart.py"],
            }
        }
    }

    client = MCPClient.from_dict(config)
    llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

    system_rules = f"""
    You are a chart generation assistant. You have access to tools for creating pie charts, bar charts, area charts, line charts, scatter charts, box plots, column charts, dual axis charts, funnel charts, radar charts, sankey charts, tree maps and managing chart images.

    Current Date: {current_date}

    Rules:
    1. Only use tools provided by MCP discovery.
    2. Never invent tool names — only use tools provided by MCP discovery.
    3. Always return structured results from tools. Summarize only if the user specifically asks for a summary.
    4. When users ask to generate pie charts, use the available chart generation tools.
    5. The available tools are:
       - pie_chart: Generate a pie chart from data and save it as PNG
       - bar_chart: Generate a bar chart from data and save it as PNG
       - area_chart: Generate an area chart from data and save it as PNG
       - line_chart: Generate a line chart from data and save it as PNG
       - scatter_chart: Generate a scatter chart from data and save it as PNG
       - box_plot: Generate a box plot from data and save it as PNG
       - column_chart: Generate a column chart from data and save it as PNG
       - dual_axis_chart: Generate a dual axis chart from data and save it as PNG
       - funnel_chart: Generate a funnel chart from data and save it as PNG
       - radar_chart: Generate a radar chart from data and save it as PNG
       - sankey_chart: Generate a sankey chart from data and save it as PNG
       - tree_map: Generate a tree map from data and save it as PNG
       - list_saved_charts: List all saved chart images

    Available Tools:
    - pie_chart: Use for creating pie charts with data, title, and filename
    - bar_chart: Use for creating horizontal bar charts with data, title, and filename
    - area_chart: Use for creating area charts with data, title, and filename
    - line_chart: Use for creating line charts with data, title, and filename
    - scatter_chart: Use for creating scatter charts with data, title, and filename
    - box_plot: Use for creating box plots with data, title, and filename
    - column_chart: Use for creating column charts with data, title, and filename
    - dual_axis_chart: Use for creating dual axis charts with data, title, and filename
    - funnel_chart: Use for creating funnel charts with data, title, and filename
    - radar_chart: Use for creating radar charts with data, title, and filename
    - sankey_chart: Use for creating sankey charts with data, title, and filename
    - tree_map: Use for creating tree maps with data, title, and filename
    - list_saved_charts: Use for viewing all saved chart images

    Chart Generation Guidelines:
    - Always provide meaningful titles for charts
    - Use descriptive filenames that reflect the chart content
    - Ensure data is properly formatted as key-value pairs
    - Consider using custom colors for better visual appeal
    
    """

    agent = MCPAgent(llm=llm, client=client, max_steps=5, system_prompt=system_rules)

    result = await agent.run(
        "Generate a treemap of world population by continent with labels Asia, Africa, Europe, North America, South America, Oceania and values 4600, 1400, 750, 600, 430, 42",
        max_steps=10,
    )
    print("Result:", result)


if __name__ == "__main__":
    asyncio.run(main())