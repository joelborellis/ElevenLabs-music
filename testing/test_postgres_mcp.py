"""
Simple script to connect to the postgres-mcp server and run analyze_db_health tool.
Uses SSE transport - requires the server to be running with --transport sse

To start the server:
    $env:DATABASE_URI = "postgresql://user:pass@host:port/db"
    uv run postgres-mcp --transport sse
"""
import asyncio
import json
from mcp import ClientSession
from mcp.client.sse import sse_client


async def main():
    """Connect to the MCP server and run analyze_db_health tool."""
    # Connect to the MCP server using SSE
    #server_url = "http://localhost:8000/sse"
    server_url = "https://postgres-mcp.happyfield-b563d6f8.westus2.azurecontainerapps.io/sse"
    
    try:
        # Add timeout to the SSE client
        print("Connecting to MCP server...")
        print("=" * 50)
        
        async with sse_client(server_url) as (read, write):
            print("✓ SSE connection established")
            
            async with ClientSession(read, write) as session:
                # Initialize the connection
                print("Initializing session...")
                await session.initialize()
                print("✓ Session initialized")
                print()
                
                # List available tools first
                tools = await session.list_tools()
                print("Available tools:")
                print("=" * 50)
                for tool in tools.tools:
                    print(f"  - {tool.name}")
                print("=" * 50)
                print()
                
                # Run the list_schemas tool with a shorter timeout test
                print("Running list_schemas tool...")
                print("=" * 50)
                
                # Create a timeout for the tool call
                try:
                    result = await asyncio.wait_for(
                        session.call_tool(
                            "list_schemas",
                            arguments={}  # No arguments needed
                        ),
                        timeout=60.0  # 60 second timeout
                    )
                    
                    # Display the results
                    print("✓ Tool execution completed")
                    for content in result.content:
                        if hasattr(content, 'text'):
                            print(content.text)
                        else:
                            print(content)
                    
                except asyncio.TimeoutError:
                    print("✗ Tool call timed out after 60 seconds")
                    print("This likely means the database connection on the server side is failing")
                    print("\nPossible causes:")
                    print("  1. DATABASE_URI not configured on the server")
                    print("  2. Database server is unreachable from the MCP server")
                    print("  3. Database credentials are invalid")
                    print("  4. Connection pool exhausted or not properly initialized")
                
                print("=" * 50)
                
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        print("\nTroubleshooting steps:")
        print("  1. Verify the MCP server is running")
        print("  2. Check if DATABASE_URI environment variable is set on the server")
        print("  3. Test database connectivity directly from the server")
        print("  4. Check server logs for detailed error messages")


if __name__ == "__main__":
    asyncio.run(main())
