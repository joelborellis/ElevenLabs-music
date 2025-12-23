"""
Interactive agent using OpenAI Agents SDK with postgres-mcp server.
The agent can answer questions about the PostgreSQL database using MCP tools.

Requirements:
    pip install openai python-dotenv

Before running:
    1. Start the MCP server with SSE:
       $env:DATABASE_URI = "postgresql://user:pass@host:port/db"
       uv run postgres-mcp --transport sse
    
    2. Set your OpenAI API key in .env file:
       OPENAI_API_KEY=your-api-key
    
    3. Run this script:
       uv run python examples/interactive_agent.py
"""
import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
from mcp import ClientSession
from mcp.client.sse import sse_client

# Load environment variables from .env file
load_dotenv()


class PostgresAgent:
    """Interactive agent that uses postgres-mcp tools via OpenAI."""
    
    def __init__(self, mcp_server_url: str = "https://postgres-mcp.happyfield-b563d6f8.westus2.azurecontainerapps.io/sse"):
        self.mcp_server_url = mcp_server_url
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.session = None
        self.tools = []
        self.conversation_history = []
        
    async def connect_to_mcp(self):
        """Connect to the MCP server and get available tools."""
        print("Connecting to postgres-mcp server...")
        self.sse_context = sse_client(self.mcp_server_url)
        read, write = await self.sse_context.__aenter__()
        
        self.session_context = ClientSession(read, write)
        self.session = await self.session_context.__aenter__()
        
        # Initialize the connection
        await self.session.initialize()
        
        # Get available tools
        tools_response = await self.session.list_tools()
        self.tools = tools_response.tools
        
        print(f"Connected! Found {len(self.tools)} tools available.")
        print("Tools:", ", ".join([tool.name for tool in self.tools]))
        print()
        
    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.session_context:
            await self.session_context.__aexit__(None, None, None)
        if self.sse_context:
            await self.sse_context.__aexit__(None, None, None)
    
    def _convert_mcp_tools_to_openai_format(self):
        """Convert MCP tools to OpenAI function calling format."""
        openai_tools = []
        for tool in self.tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                }
            }
            
            # Add input schema if available
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                openai_tool["function"]["parameters"] = tool.inputSchema
            else:
                openai_tool["function"]["parameters"] = {
                    "type": "object",
                    "properties": {}
                }
            
            openai_tools.append(openai_tool)
        
        return openai_tools
    
    async def _call_mcp_tool(self, tool_name: str, arguments: dict):
        """Call an MCP tool and return the result."""
        try:
            result = await self.session.call_tool(tool_name, arguments=arguments)
            
            # Extract text content from result
            response_text = ""
            for content in result.content:
                if hasattr(content, 'text'):
                    response_text += content.text
                else:
                    response_text += str(content)
            
            return response_text
        except Exception as e:
            return f"Error calling tool {tool_name}: {str(e)}"
    
    async def chat(self, user_message: str):
        """Send a message to the agent and get a response."""
        # Add user message to conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Prepare OpenAI tools
        openai_tools = self._convert_mcp_tools_to_openai_format()
        
        # Call OpenAI with tool support
        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful database assistant. You have access to PostgreSQL database tools through MCP. Use these tools to help users analyze their database, run queries, check health, and optimize performance. Always explain what you're doing and present results in a clear, user-friendly way."
                },
                *self.conversation_history
            ],
            tools=openai_tools,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        
        # Check if the model wants to call tools
        if assistant_message.tool_calls:
            # Add assistant's tool call message to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = eval(tool_call.function.arguments)  # Parse JSON string to dict
                
                print(f"\n🔧 Calling tool: {tool_name}")
                if tool_args:
                    print(f"   Arguments: {tool_args}")
                
                # Call the MCP tool
                tool_result = await self._call_mcp_tool(tool_name, tool_args)
                
                # Add tool result to conversation history
                self.conversation_history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })
            
            # Get final response from the model with tool results
            final_response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful database assistant. You have access to PostgreSQL database tools through MCP. Use these tools to help users analyze their database, run queries, check health, and optimize performance. Always explain what you're doing and present results in a clear, user-friendly way."
                    },
                    *self.conversation_history
                ]
            )
            
            final_message = final_response.choices[0].message.content
            self.conversation_history.append({
                "role": "assistant",
                "content": final_message
            })
            
            return final_message
        else:
            # No tool calls, just return the response
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message.content
            })
            return assistant_message.content


async def main():
    """Run the interactive agent."""
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY environment variable not set.")
        print("Please set it with: $env:OPENAI_API_KEY = 'your-api-key'")
        return
    
    agent = PostgresAgent()
    
    try:
        # Connect to MCP server
        await agent.connect_to_mcp()
        
        print("=" * 70)
        print("🤖 PostgreSQL Database Assistant")
        print("=" * 70)
        print("Ask me anything about your database!")
        print("Examples:")
        print("  - What's the health status of my database?")
        print("  - List all schemas")
        print("  - What are the top queries by execution time?")
        print("  - Show me tables in the public schema")
        print()
        print("Type 'quit' or 'exit' to end the conversation.")
        print("=" * 70)
        print()
        
        # Interactive loop
        while True:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            # Get response from agent
            response = await agent.chat(user_input)
            print(f"\n🤖 Assistant: {response}\n")
    
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        await agent.disconnect()


if __name__ == "__main__":
    asyncio.run(main())