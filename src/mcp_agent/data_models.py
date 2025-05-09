from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from enum import Enum


@dataclass
class MCPConnectionContext:
    """
    Represents a connection to an MCP server with associated resources.
    
    Attributes:
        exit_stack: Context manager for proper resource cleanup
        session: The active MCP client session, if established
    """
    exit_stack: AsyncExitStack
    session: Optional[ClientSession] = None


@dataclass
class ToolDefinition:
    """
    Defines a tool available through the MCP framework.
    
    Attributes:
        name: The unique identifier for the tool
        description: Human-readable description of the tool's purpose
        input_schema: JSON schema defining the tool's input parameters
        connection: Connection context for accessing the tool
    """
    name: str
    description: str
    input_schema: Dict[str, Any]
    connection: MCPConnectionContext

    def to_openai_format(self) -> Dict[str, Any]:
        """
        Convert the tool definition to OpenAI's function calling format.
        
        Returns:
            Dict containing the OpenAI-compatible tool definition
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            }
        }


@dataclass
class ExecutionStepResult:
    """
    Result of a single step in the agent's execution.
    
    Attributes:
        messages: List of message objects generated during this step
        finished: Whether the agent has completed its task
        total_tokens: Token usage for this step, if available
    """
    messages: List[Dict[str, Any]]
    finished: bool
    total_tokens: Optional[int] = None


class StepType(str, Enum):
    """
    Classifies the type of an agent execution step.
    """
    ASSISTANT = "ASSISTANT"
    TOOL_RESULT = "TOOL_RESULT"


@dataclass
class ExecutionStep:
    """
    Details of a single step in the agent's execution process.
    
    Attributes:
        type: Classification of this step (assistant or tool result)
        step_number: Sequential number of this step in the execution
        content: Text content produced in this step
        tokens_used: Token usage for this step
    """
    type: StepType
    step_number: int
    content: str
    tokens_used: int


@dataclass
class AgentExecutionResult:
    """
    Complete results of an agent's execution run.
    
    Attributes:
        total_steps: Number of steps executed
        steps: Detailed information for each execution step
        total_tokens_used: Cumulative token usage across all steps
    """
    total_steps: int
    steps: List[ExecutionStep]
    total_tokens_used: int


@dataclass
class MCPServerConfig:
    """
    Configuration for an MCP server.
    
    Attributes:
        command: The executable command to start the server
        args: Command line arguments for the server
        env: Environment variables to set for the server process
    """
    command: str
    args: List[str]
    env: Optional[Dict[str, str]] = None

    def to_stdio_parameters(self) -> StdioServerParameters:
        """
        Convert the configuration to MCP StdioServerParameters.
        
        Returns:
            StdioServerParameters object for starting the server
        """
        return StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env
        )


__all__ = [
    "MCPConnectionContext",
    "ToolDefinition",
    "ExecutionStepResult",
    "StepType",
    "ExecutionStep",
    "AgentExecutionResult",
    "MCPServerConfig"
]