import asyncio
import os
from typing import Optional

from dotenv import load_dotenv

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

'''
Tools:
    1. create_development_plan: navigate to requirement/feature_request.md and create a development plan.
    2. get_file_info: Checks that the artifacts folder is present and other essential things.
    3. get_file_contents: If already project is created or some files are available then read those files and understand the codebase.
    4. write_file: according to the plan overwrite the files or create new files and code.
    5. run_python_file: this tool will run the code and check for any errors or linter warnings.
'''

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

    try:
        from agent_framework.anthropic import AnthropicClient  # type: ignore
        from anthropic import AsyncAnthropicFoundry  # type: ignore
    except ImportError as exc:  # pragma: no cover - dependency missing
        raise RuntimeError(
            "agent_framework[anthropic] and anthropic packages must be installed"
        ) from exc

    client = AnthropicClient(
        model_id=ANTHROPIC_FOUNDRY_DEPLOYMENT,
        anthropic_client=AsyncAnthropicFoundry(
            api_key=ANTHROPIC_FOUNDRY_API_KEY,
            base_url=ANTHROPIC_FOUNDRY_ENDPOINT,
        ),
    )

    instructions = instructions or (
        "You are a coding agent that translates natural language product"
        " requirements into concrete web application source files. Return"
        " concise, well-commented code and note any follow-up questions."
    )

    async with client.create_agent(
        name="CoderAgent",
        instructions=instructions,
        tools=[],
        allow_multiple_tool_calls=False,
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
