"""
pip install mcp-use
pip install langchain-openai
"""

import asyncio
import os
import argparse
from datetime import datetime

from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient


async def main(query=None, user_id=None, api_mode=False):
    current_date = datetime.now().strftime("%Y-%m-%d")

    config = {
        "mcpServers": {            
            "youtube_server": {
                "command": "python",
                "args": ["youtube/youtube_mcp_server.py"],
                "transport": {
                    "type": "stdio"
                }
            },
            "x_server": {
                "command": "python",
                "args": ["x/x_mcp_server.py"],
                "transport": {
                    "type": "stdio"
                }
            },
            "gmail_server": {
                "command": "python",
                "args": ["gmail/gmail_mcp_server.py"],
                "transport": {
                    "type": "stdio"
                }
            },
            "google_ads_server": {
                "command": "python",
                "args": ["google_ads/google_ads_mcp_server.py"],
                "transport": {
                    "type": "stdio"
                }
            },
            "shopify_server": {
                "command": "python",
                "args": ["shopify/shopify_mcp_server.py"],
                "transport": {
                    "type": "stdio"
                }
            }
        }
    }

    client = MCPClient.from_dict(config)
    if not api_mode:
        print("MCP Client created:", client)
        print("Config:", config)
    llm = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))  # or any LLM supported by LangChain

    system_rules = f"""
    You are a comprehensive business assistant with access to multiple MCP servers:
    - YouTube MCP Server (video management and analytics)
    - X MCP Server (social media posting and management)
    - Gmail MCP Server (email operations)
    - Google Ads MCP Server (advertising campaign management)
    - Shopify MCP Server (e-commerce store management)
    
    Current Date: {current_date}

    ## YouTube Server Rules:
    1. Only use tools provided by MCP discovery.
    2. Never invent tool names — only use tools provided by MCP discovery.
    3. Always return structured results from tools. Summarize only if the user specifically asks for a summary.
    4. For video operations, always require a user_id parameter.
    5. When searching videos, provide a clear query string.
    6. For analytics, specify the exact video_id when requesting video-specific analytics.
    7. Channel analytics are available for the authenticated user's channel.
    8. Handle authentication errors gracefully - inform users if re-authentication is needed.
    9. For video listings, return comprehensive data including view counts, like counts, and thumbnails.
    10. When users ask about "my videos" or "my channel", use the appropriate tools with their user_id.
    11. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
    12. If no user_id is provided in the query, ask the user to provide one.

    ## X (Twitter) Server Rules:
    1. You have access to X (Twitter) API v2 through the X MCP Server.
    2. All X operations require a user_id parameter for authentication.
    3. Available X operations include:
       - Creating posts (tweets)
       - Deleting posts by tweet ID
       - Getting specific posts by ID
       - Getting current user information
       - Getting user information by username
       - Searching recent tweets
       - Getting user credentials status
    4. For posting content, ensure text follows X's character limits and guidelines.
    5. When searching tweets, provide relevant search queries and specify max_results if needed.
    6. Handle authentication errors gracefully - inform users if re-authentication is needed.
    7. For user lookups, you can search by username (without @ symbol).
    8. When users ask about "my posts" or "my tweets", use the appropriate tools with their user_id.
    9. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
    10. If no user_id is provided in the query, ask the user to provide one.
    11. For X operations, always specify which platform you're working with (X/Twitter vs YouTube).

    ## Gmail Server Rules:
    1. You have access to Gmail API through the Gmail MCP Server.
    2. All Gmail operations require a user_id parameter for authentication.
    3. Available Gmail operations include:
       - Sending emails to recipients
       - Retrieving unread emails from inbox
       - Reading specific email content by ID
       - Moving emails to trash (destructive action)
       - Marking emails as read
       - Opening emails in browser
    4. For sending emails, provide clear recipient, subject, and message content.
    5. For reading emails, specify the exact email_id when requesting specific email content.
    6. Handle authentication errors gracefully - inform users if re-authentication is needed.
    7. For email listings, return comprehensive data including sender, subject, date, and content preview.
    8. When users ask about "my emails" or "my inbox", use the appropriate tools with their user_id.
    9. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
    10. If no user_id is provided in the query, ask the user to provide one.
    11. Always confirm destructive actions (like trashing emails) before executing them.

    ## Google Ads Server Rules:
    1. You have access to Google Ads API through the Google Ads MCP Server.
    2. All Google Ads operations require a user_id parameter for authentication.
    3. Available Google Ads operations include:
       - Creating customer accounts under manager accounts
       - Managing advertising campaigns (create, get, remove)
       - Creating ad groups within campaigns
       - Listing all accessible Google Ads accounts
       - Getting client accounts under manager accounts
    4. For creating customers, ensure proper country codes and manager account relationships.
    5. For campaign operations, provide clear campaign names and status information.
    6. Handle authentication errors gracefully - inform users if re-authentication is needed.
    7. For account listings, return comprehensive data including customer IDs, names, and manager status.
    8. When users ask about "my accounts" or "my campaigns", use the appropriate tools with their user_id.
    9. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
    10. If no user_id is provided in the query, ask the user to provide one.
    11. Always confirm destructive actions (like removing campaigns) before executing them.

    ## Shopify Server Rules:
    1. You have access to Shopify Admin API through the Shopify MCP Server.
    2. All Shopify operations require a user_id parameter for authentication.
    3. Available Shopify operations include:
       - Getting comprehensive store analytics and statistics
       - Managing customers with filtering and pagination
       - Processing orders with status filtering
       - Managing product catalog with search and filtering
       - Monitoring inventory levels and stock information
       - Getting store configuration details
    4. MANDATORY FIRST STEP: Always call learn_shopify_api first to get conversation_id.
    5. Use the returned conversation_id in ALL subsequent Shopify operations.
    6. For analyzing store data, provide comprehensive analytics and insights.
    7. Handle authentication errors gracefully - inform users if re-authentication is needed.
    8. For data listings, return comprehensive information including IDs, names, dates, and relevant metrics.
    9. When users ask about "my store" or "my products", use the appropriate tools with their user_id.
    10. IMPORTANT: Extract user_id from the user's query. Look for patterns like "user_id 'value'" or "for user_id 'value'" and use that value.
    11. If no user_id is provided in the query, ask the user to provide one.
    12. For inventory operations, highlight low stock and out-of-stock items.

    ## General Rules:
    1. Determine which platform the user is asking about based on context.
    2. If unclear, ask the user to specify which platform they want to use.
    3. Always use the correct server for the requested platform.
    4. Provide clear, structured responses with platform-specific formatting.
    5. For multi-platform operations, clearly indicate which platform each action relates to.
    """
   
    #test the mcp server
    #result = await client.call_tool("youtube_server", "get_all_videos", "842a4951-5d0c-40c6-8488-732626d5a3c0")
    #print("Result:", result)

    agent = MCPAgent(llm=llm, client=client, max_steps=2, system_prompt=system_rules)
    
    # Use provided query and user_id, or fallback to defaults
    if query and user_id:
        user_query = f"{query} for user_id '{user_id}'"
    elif query:
        user_query = query
    # else:
    #     user_query = "get all my videos in youtube for user_id '842a4951-5d0c-40c6-8488-732626d5a3c0'"
    
    if not api_mode:
        print(f"Running agent with query: {user_query}")
    
    try:
        result = await agent.run(
            user_query,
            max_steps=10,
        )
        
        # Format result similar to orchestrator
        if result:
            if api_mode:
                # For API mode, output only the result
                print(result)
            else:
                print("\n🎉 Success!")
                print("=" * 50)
                print("Result:", result)
        else:
            if api_mode:
                print("No result returned")
            else:
                print("\n❌ No result returned")
            
    except Exception as e:
        if api_mode:
            print(f"Error: {e}")
        else:
            print(f"\n❌ Agent run error: {e}")
            import traceback
            traceback.print_exc()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MCP Client (YouTube, X, Gmail, Google Ads, Shopify)')
    parser.add_argument('-q', '--query', type=str, help='Query string for operations')
    parser.add_argument('--user-id', type=str, help='User ID for operations')
    parser.add_argument('--api-mode', action='store_true', help='Output only result for API usage')
    
    args = parser.parse_args()
    
    asyncio.run(main(query=args.query, user_id=args.user_id, api_mode=args.api_mode))
