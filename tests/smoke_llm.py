"""Smoke test — single agent call with LLM. Tests provider integration."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wef_agentic.llm.provider import get_provider_for_agent
from wef_agentic.llm.types import Message


async def test_ollama_local_basic():
    """Verify Ollama local responds to simple chat."""
    # Use smallest available model untuk smoke test cepat
    from wef_agentic.llm.ollama_provider import OllamaProvider
    provider = OllamaProvider(model="llama3.2:1b", max_tokens=64, temperature=0.1)

    response = await provider.chat([
        Message(role="system", content="Anda adalah asisten singkat."),
        Message(role="user", content="Sebutkan 1 sungai di Sleman dengan satu kata saja."),
    ])
    print(f"Provider: {response.provider}, model: {response.model}")
    print(f"Response: {response.content[:200]}")
    print(f"Tokens: in={response.usage.input_tokens}, out={response.usage.output_tokens}")
    assert len(response.content) > 0
    print("✓ Ollama local responds")


async def test_water_agent_single():
    """Run single Water Agent untuk skenario S1."""
    from wef_agentic.agents import WaterAgent
    from wef_agentic.orchestration import get_scenario
    from wef_agentic.llm.ollama_provider import OllamaProvider

    # Override provider untuk smoke test
    agent = WaterAgent(provider=OllamaProvider(model="llama3.2:1b", max_tokens=512))
    scenario = get_scenario("S1_BAU_2030")
    output = await agent.run(scenario)

    print(f"Water Agent output ({len(output.content)} chars):")
    print(output.content[:500])
    print(f"Tool calls: {len(output.tool_outputs)}")
    assert len(output.content) > 0
    print("✓ Water Agent end-to-end works")


if __name__ == "__main__":
    print("=" * 60)
    print("WEF-Agentic smoke test (with LLM via Ollama local)")
    print("=" * 60)

    try:
        asyncio.run(test_ollama_local_basic())
        print()
        asyncio.run(test_water_agent_single())
        print()
        print("=" * 60)
        print("LLM smoke tests passed ✓")
        print("=" * 60)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
