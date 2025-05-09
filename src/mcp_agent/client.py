from contextlib import AsyncExitStack
import json
import logging
from typing import Dict, List, Optional, Any

import backoff
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

from .data_models import MCPConnectionContext, ToolDefinition, ExecutionStepResult

logger = logging.getLogger(__name__)


class MCPToolClient:
    """
    Client for managing MCP tool servers and executing LLM queries with tool support.
    
    This class handles:
    - Connecting to MCP tool servers
    - Registering available tools
    - Executing LLM queries with tool calling
    - Managing tool execution and results
    
    Attributes:
        model: The LLM model identifier to use for queries
        client: The AsyncOpenAI client instance
        available_tools: Dictionary of registered tools by name
    """
    
    def __init__(self, model: str, openai_client: Optional[AsyncOpenAI] = None):
        """
        Initialize the MCP tool client.
        
        Args:
            model: Identifier for the LLM model to use
            client: Optional AsyncOpenAI client instance, created if not provided
        """
        self.model = model
        self.openai_client = openai_client or AsyncOpenAI()
        self.available_tools: Dict[str, ToolDefinition] = {}

    async def register_server(self, server_params: StdioServerParameters) -> None:
        """
        Connect to an MCP server and register its available tools.
        
        Args:
            server_params: Configuration for connecting to the server
        
        Raises:
            ConnectionError: If unable to connect to the server
        """
        session: Optional[ClientSession] = None
        exit_stack = AsyncExitStack()

        try:
            stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await exit_stack.enter_async_context(ClientSession(stdio, write))
            
            await session.initialize()
            
            response = await session.list_tools()
            logger.info("Connected to server with tools: %s", 
                        [tool.name for tool in response.tools])

            connection = MCPConnectionContext(exit_stack=exit_stack, session=session)
            
            for tool in response.tools:
                self.available_tools[tool.name] = ToolDefinition(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.inputSchema,
                    connection=connection
                )
        except Exception as e:
            await exit_stack.aclose()
            logger.error("Failed to connect to MCP server: %s", str(e))
            raise ConnectionError(f"Failed to connect to MCP server: {str(e)}")

    @backoff.on_exception(
        backoff.constant,
        Exception,
        max_tries=3,
        interval=0.5,
        on_backoff=lambda details: logger.info(
            f"API error, retrying in {details['wait']:.2f} seconds... (attempt {details['tries']})"
        ),
    )
    async def execute_step(self, messages: List[Dict[str, Any]]) -> ExecutionStepResult:
        """
        Execute a single step in the agent's reasoning process, including any tool calls.
        
        Args:
            messages: List of conversation messages to send to the LLM
        
        Returns:
            ExecutionStepResult containing new messages and completion status
        
        Raises:
            ValueError: If the LLM returns an empty or invalid response
        """
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=[tool.to_openai_format() for tool in self.available_tools.values()],
            tool_choice="auto"
        )

        if response.choices is None:
            import pdb; pdb.set_trace()
            raise ValueError("Empty response from LLM provider")

        result_messages = []
        content = response.choices[0].message.content
        tool_calls = response.choices[0].message.tool_calls or []
        total_tokens = response.usage.total_tokens

        if content:
            result_messages.append({"role": "assistant", "content": content})

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

            result_messages.append({
                "role": "assistant",
                "content": f"Calling {tool_name} with arguments: {tool_args}",
                "tool_calls": [tool_call]
            })

            tool = self.available_tools.get(tool_name)
            if not tool or not tool.connection.session:
                logger.warning(f"Tool '{tool_name}' not found or session not established")
                break

            try:
                session = tool.connection.session
                result = await session.call_tool(tool_name, tool_args)
                
                result_messages.append({
                    "role": "user",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": result.content
                })
            except Exception as e:
                logger.error(f"Error executing tool '{tool_name}': {str(e)}")
                result_messages.append({
                    "role": "user",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": f"Error: {str(e)}"
                })

        return ExecutionStepResult(
            messages=result_messages, 
            finished=len(tool_calls) == 0,
            total_tokens=total_tokens
        )

    async def cleanup(self) -> None:
        """
        Release all resources and close connections.
        """
        for tool in self.available_tools.values():
            if tool.connection:
                try:
                    await tool.connection.exit_stack.aclose()
                except Exception as e:
                    logger.warning(f"Error during cleanup: {str(e)}")


__all__ = ["MCPToolClient"]