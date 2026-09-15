"""Manual smoke check — single agent call against a real local Ollama.

Not collected by pytest (needs `ollama serve` + the model pulled).

    python scripts/smoke_llm.py [model]      # default llama3.2:1b
"""
from __future__ import annotations

import asyncio
import sys

from wef_agentic.agents import WaterAgent
from wef_agentic.llm.ollama_provider import OllamaProvider
from wef_agentic.llm.types import Message
from wef_agentic.orchestration import compute_nexus, get_scenario


async def main(model: str) -> None:
    provider = OllamaProvider(model=model, max_tokens=256, temperature=0.1)
    response = await provider.chat([
        Message(role="system", content="Anda adalah asisten singkat."),
        Message(role="user", content="Sebutkan 1 sungai di Sleman dengan satu kata saja."),
    ])
    print(f"Provider: {response.provider}, model: {response.model}, done_reason: {response.done_reason}")
    print(f"Response: {response.content[:200]!r}")
    assert response.content.strip(), "empty completion"
    print("✓ Ollama local responds")

    scenario = get_scenario("S1_BAU_2030")
    nexus = await asyncio.to_thread(compute_nexus, scenario)
    agent = WaterAgent(provider=OllamaProvider(model=model, max_tokens=1024))
    output = await agent.run(scenario, nexus)
    print(f"\nWater Agent output ({len(output.content)} chars, {output.meta['attempts']} attempt(s)):")
    print(output.content[:500])
    print("✓ Water Agent end-to-end works")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "llama3.2:1b"))
