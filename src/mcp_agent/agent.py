from typing import Dict, List, Optional, Union, AsyncGenerator, Any

from .client import MCPToolClient
from .data_models import (
    MCPServerConfig, 
    ExecutionStep, 
    AgentExecutionResult, 
    StepType,
    ExecutionStepResult
)
from .prompts import SYSTEM_PROMPT, USER_INSTRUCTIONS_PROMPT
from .utils import extract_message_content


class MCPAgent:
    """
    An agent that executes MCP tools.
    
    The agent handles:
    - Initializing connections to tool servers
    - Managing conversation context
    - Executing multi-step reasoning with tool calls
    - Streaming results during execution
    
    Attributes:
        model: The LLM model identifier
        client: Optional custom OpenAI client
        instruction: Custom instructions for the agent
        servers: List of tool servers to connect to
        max_steps: Maximum number of steps to execute
        tool_client: Client for managing tools and LLM interaction
    """

    def __init__(
            self, 
            model: str, 
            client=None, 
            instruction: Optional[str] = None,
            servers: Optional[List[MCPServerConfig]] = None,
            max_steps: int = 10,
        ):
        """
        Initialize the MCP Agent.
        
        Args:
            model: Identifier for the LLM model
            client: Optional AsyncOpenAI client
            instruction: Custom instructions for the agent
            servers: List of tool server configurations
            max_steps: Maximum number of reasoning steps to perform
        """
        self.servers = [server.to_stdio_parameters() for server in servers or []]
        
        self.instruction = USER_INSTRUCTIONS_PROMPT.format(user_instruction=instruction) \
                            if instruction else ""
        
        self.tool_client = MCPToolClient(model=model, openai_client=client)
        self.max_steps = max_steps
        self._initialized = False

    async def execute(self, input_query: str) -> AsyncGenerator[Union[ExecutionStep, AgentExecutionResult], None]:
        """
        Execute the agent on the given input query.
        
        This method:
        1. Initializes tool connections if needed
        2. Sets up the conversation context
        3. Iteratively executes steps until completion or max steps reached
        4. Yields each step as it completes
        5. Yields the final result summary
        
        Args:
            input_query: The user's query to process
            
        Yields:
            ExecutionStep objects for each step of execution
            AgentExecutionResult when execution completes
        
        Raises:
            RuntimeError: If tool connections fail to initialize
        """
        if not self._initialized:
            for server in self.servers:
                try:
                    await self.tool_client.register_server(server)
                except ConnectionError as e:
                    raise RuntimeError(f"Failed to initialize tool connections: {str(e)}")
            self._initialized = True

        conversation_history = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(instruction=self.instruction)
            },
            {
                "role": "user",
                "content": input_query
            }
        ]

        result_messages = []
        execution_steps = []
        total_tokens_used = 0

        step_number = 0
        while step_number < self.max_steps:
            step_number += 1
            
            step_result: ExecutionStepResult = await self.tool_client.execute_step(
                conversation_history + result_messages
            )
            
            for msg in step_result.messages:
                tokens_used = step_result.total_tokens or 0
                step_type = StepType.ASSISTANT if msg["role"] == "assistant" else StepType.TOOL_RESULT
                
                execution_step = ExecutionStep(
                    type=step_type,
                    step_number=step_number, 
                    content=extract_message_content(msg),
                    tokens_used=tokens_used
                )
                
                result_messages.append(msg)
                execution_steps.append(execution_step)
                total_tokens_used += tokens_used
                
                yield execution_step

            if step_result.finished:
                break

        yield AgentExecutionResult(
            total_steps=step_number,
            steps=execution_steps,
            total_tokens_used=total_tokens_used
        )

    async def cleanup(self) -> None:
        """
        Release all resources and connections.
        
        Should be called when the agent is no longer needed.
        """
        await self.tool_client.cleanup()


__all__ = ["MCPAgent"]