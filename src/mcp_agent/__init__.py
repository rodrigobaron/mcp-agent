"""
MCP Agent Framework
==================

A framework for creating agents that can use Model-Client-Protocol (MCP) tools
with large language models. This package provides:

- Tool integration with MCP servers
- Multi-step reasoning with LLMs
- Dynamic tool calling
- Streaming execution results

Example usage:
```python
import asyncio
from mcp_agent import MCPAgent, MCPServerConfig

async def main():
    # Define tool servers
    servers = [
        MCPServerConfig(
            command="python",
            args=["-m", "my_tool_server"]
        )
    ]
    
    # Create agent
    agent = MCPAgent(
        model="gpt-4-turbo",
        instruction="Help the user with data analysis",
        servers=servers
    )
    
    # Run the agent
    async for step in agent.execute("Analyze my sales data"):
        print(step)
        
    # Clean up resources
    await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```
"""

from .agent import MCPAgent
from .client import MCPToolClient
from .data_models import (
    MCPConnectionContext,
    MCPServerConfig,
    ToolDefinition,
    ExecutionStepResult,
    StepType,
    ExecutionStep, 
    AgentExecutionResult
)

__version__ = "0.1.0"
__author__ = "Your Name"

__all__ = [
    # Main classes
    "MCPAgent",
    "MCPToolClient",
    
    # Data models
    "MCPConnectionContext",
    "MCPServerConfig",
    "ToolDefinition",
    "ExecutionStepResult",
    "StepType",
    "ExecutionStep",
    "AgentExecutionResult",
]