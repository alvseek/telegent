"""The LLM brain: a pydantic-ai Agent on an OpenRouter (OpenAI-compatible) model.

This is the only file that knows about the model. Swapping the brain (different
provider/model, or adding tools later) happens here without touching the
Telegram bridge or the memory store.
"""
from __future__ import annotations

from typing import List, Tuple

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

Turn = Tuple[str, str]  # (role, content)


def build_agent(
    model: str, base_url: str, api_key: str, system_prompt: str
) -> Agent:
    """Construct an Agent bound to an OpenAI-compatible endpoint (OpenRouter)."""
    provider = OpenAIProvider(base_url=base_url, api_key=api_key)
    llm = OpenAIChatModel(model, provider=provider)
    return Agent(llm, system_prompt=system_prompt)


def _to_history(history: List[Turn]) -> List[ModelMessage]:
    """Map stored (role, content) turns into pydantic-ai message history."""
    messages: List[ModelMessage] = []
    for role, content in history:
        if role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=content)]))
    return messages


async def answer(agent: Agent, history: List[Turn], user_msg: str) -> str:
    """Run the agent for one user message, given prior conversation history."""
    result = await agent.run(user_msg, message_history=_to_history(history))
    return result.output
