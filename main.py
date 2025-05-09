import os
import asyncio
from openai import AsyncOpenAI
from src.mcp_agent import MCPAgent, MCPServerConfig, ExecutionStep, StepType


async def main():
    model = "google/gemini-2.5-flash-preview"
    llm = AsyncOpenAI(base_url="https://openrouter.ai/api/v1/", api_key=os.getenv("OPENROUTER_API_KEY"))

    playwright = MCPServerConfig(
        command="npx",
        args=["@playwright/mcp@latest"],
        env=None
    )

    query = """Search about Rodrigo Baron - Machine Learning Engineer:
1. Fetch web page content
2. Analyze the content
3. Extract key information
4. Generate a summary report
"""

    agent = MCPAgent(model=model, client=llm, servers=[playwright])

    try:
        async for step in agent.execute(query):
            if not isinstance(step, ExecutionStep):
                continue
            if step.type == StepType.ASSISTANT:
                print(f"[ASSISTANT]: {step.content}")
            else:
                print(f"[TOOL]:\n{step.content}")
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
