import asyncio
import os
from typing import Optional

from dotenv import load_dotenv
from agents.tools.filesystem import (
    get_file_contents,
    get_file_info,
    run_python_file,
    write_file,
)
from agents.tools.planning import create_development_plan
from agent_framework.anthropic import AnthropicClient
from anthropic import AsyncAnthropicFoundry

load_dotenv()

ANTHROPIC_FOUNDRY_ENDPOINT = os.getenv("ANTHROPIC_FOUNDRY_ENDPOINT")
ANTHROPIC_FOUNDRY_DEPLOYMENT = os.getenv("ANTHROPIC_FOUNDRY_DEPLOYMENT")
ANTHROPIC_FOUNDRY_API_KEY = os.getenv("ANTHROPIC_FOUNDRY_API_KEY")

def build_coder_prompt(requirement_text: str) -> str:
    return (
        "You are a senior front-end engineer. Produce clean, maintainable code\n"
        "that satisfies the following requirements. If something is unclear,\n"
        "state the assumptions you are making.\n\n"
        f"Requirements:\n{requirement_text}\n"
    )

"""
Tools:
    1. create_development_plan: summarize requirements before coding.
    2. get_file_info: verify directories/files exist and inspect their shape.
    3. get_file_contents: read existing source files to understand the codebase.
    4. write_file: create or overwrite source files according to the plan.
    5. run_python_file: execute scripts (e.g., tests, linters) to validate output.
"""

async def run_coder_agent(prompt: str, *, instructions: Optional[str] = None) -> None:
    required = {
        "ANTHROPIC_FOUNDRY_ENDPOINT": ANTHROPIC_FOUNDRY_ENDPOINT,
        "ANTHROPIC_FOUNDRY_DEPLOYMENT": ANTHROPIC_FOUNDRY_DEPLOYMENT,
        "ANTHROPIC_FOUNDRY_API_KEY": ANTHROPIC_FOUNDRY_API_KEY,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
        return

    client = AnthropicClient(
        model_id=ANTHROPIC_FOUNDRY_DEPLOYMENT,
        anthropic_client=AsyncAnthropicFoundry(
            api_key=ANTHROPIC_FOUNDRY_API_KEY,
            base_url=ANTHROPIC_FOUNDRY_ENDPOINT,
        ),
    )

    instructions = instructions or (
    "You are a coding agent that translates natural language product"
    " requirements into concrete web application source files. Begin by"
    " calling create_development_plan, then inspect the workspace with"
    " get_file_info/get_file_contents before writing code updates. Use"
    " write_file for modifications and run_python_file to validate when"
    " applicable. Return concise, well-commented output and note any"
    " follow-up questions."
    )

    async with client.create_agent(
        name="CoderAgent",
        instructions=instructions,
        tools=[
            create_development_plan,
            get_file_info,
            get_file_contents,
            write_file,
            run_python_file,
        ],
        allow_multiple_tool_calls=True,
    ) as agent:
        thread = agent.get_new_thread()
        print("Agent: ", end="", flush=True)
        async for chunk in agent.run_stream(prompt, thread=thread):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print()


if __name__ == "__main__":
    requirements = """
    Build a responsive marketing home page with a hero section, three feature
    highlights, and a testimonials carousel. Include navigation links for Home,
    Features, Pricing, and Contact. Ensure all interactive elements have unique
    data-testid attributes for Playwright tests.
    """

    coder_prompt = build_coder_prompt(requirements)
    asyncio.run(run_coder_agent(coder_prompt))
