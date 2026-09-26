import pytest

from tests.conftest import FakeProvider
from wef_agentic.agents import CriticAgent
from wef_agentic.config.settings import load_llm_config
from wef_agentic.llm.ollama_provider import OllamaProvider
from wef_agentic.llm.provider import get_provider_for_agent
from wef_agentic.llm.types import EmptyCompletionError, Message, TruncatedCompletionError


def test_provider_override_uses_provider_specific_model_and_agent_budget(monkeypatch):
    monkeypatch.setenv("WEF_AGENTIC_PROVIDER_OVERRIDE", "ollama-local")
    p = get_provider_for_agent("critic")
    assert isinstance(p, OllamaProvider)
    assert p.model == "gemma4:e4b"
    assert p.max_tokens == 12000


def test_critic_default_cloud_model_is_glm_flash():
    assert load_llm_config()["agents"]["critic"]["model"] == "glm-5.3-flash:cloud"


def test_model_override_wins(monkeypatch):
    monkeypatch.setenv("WEF_AGENTIC_PROVIDER_OVERRIDE", "ollama-local")
    monkeypatch.setenv("WEF_AGENTIC_MODEL_OVERRIDE", "llama3.2:1b")
    assert get_provider_for_agent("water").model == "llama3.2:1b"


async def test_ollama_exposes_thinking_and_truncation():
    p = OllamaProvider(model="kimi-k2.6:cloud")

    class Client:
        async def chat(self, **kwargs):
            assert kwargs["options"]["num_predict"] == p.max_tokens
            return {
                "model": "kimi-k2.6", "done_reason": "length",
                "message": {"content": "", "thinking": "menimbang..."},
                "prompt_eval_count": 7, "eval_count": 3000,
            }

    p.client = Client()
    r = await p.chat([Message("user", "hi")])
    assert r.truncated
    assert r.thinking == "menimbang..."
    assert r.usage.output_tokens == 3000
    assert r.model == "kimi-k2.6"


async def test_empty_truncated_answer_is_retried_with_larger_budget():
    prov = FakeProvider(replies=[("", "length"), ("jawaban", "stop")], max_tokens=3000)
    r = await CriticAgent(provider=prov)._call_llm("audit")
    assert r.content == "jawaban"
    assert [c["max_tokens"] for c in prov.calls] == [3000, 6000]
    assert prov.max_tokens == 3000
    assert (r.usage.input_tokens, r.usage.output_tokens) == (20, 10)  # both attempts counted
    assert r.meta["attempts"] == 2
    assert r.meta["prompt_sha256"]


async def test_retry_budget_is_capped():
    prov = FakeProvider(replies=[("", "length"), ("ok", "stop")], max_tokens=12000)
    await CriticAgent(provider=prov)._call_llm("audit")
    assert prov.calls[1]["max_tokens"] == 16000


async def test_nonempty_truncated_answer_is_replaced_with_complete_retry():
    prov = FakeProvider(replies=[("partial", "length"), ("complete", "stop")], max_tokens=4096)
    r = await CriticAgent(provider=prov)._call_llm("audit")
    assert r.content == "complete"
    assert not r.truncated
    assert [c["max_tokens"] for c in prov.calls] == [4096, 8192]
    assert prov.max_tokens == 4096
    assert (r.usage.input_tokens, r.usage.output_tokens) == (20, 10)
    assert r.meta["attempts"] == 2


@pytest.mark.parametrize("budget", [12000, 16000, 20000])
async def test_still_truncated_raises_and_restores_budget(budget):
    prov = FakeProvider(replies=[("partial", "length"), ("partial again", "length")],
                        max_tokens=budget)
    with pytest.raises(TruncatedCompletionError, match=r"critic.*after 2 attempts"):
        await CriticAgent(provider=prov)._call_llm("audit")
    assert len(prov.calls) == 2
    assert prov.calls[1]["max_tokens"] == max(budget, 16000)
    assert prov.max_tokens == budget


async def test_still_empty_raises_instead_of_passing_on_nothing():
    prov = FakeProvider(replies=[("", "length"), ("  ", "length")])
    with pytest.raises(EmptyCompletionError, match="critic"):
        await CriticAgent(provider=prov)._call_llm("audit")


async def test_claude_provider_pins_model_and_disables_tools():
    sdk = pytest.importorskip("claude_agent_sdk")
    from wef_agentic.llm.claude_agent_provider import ClaudeAgentSDKProvider

    p = ClaudeAgentSDKProvider(model="claude-sonnet-4-6", max_tokens=1234)
    captured = {}

    async def fake_query(prompt, options):
        captured["prompt"], captured["options"] = prompt, options
        yield sdk.AssistantMessage(content=[sdk.TextBlock(text="halo")],
                                   model="claude-sonnet-4-6-20260101", stop_reason="end_turn")
        yield sdk.ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
                                num_turns=1, session_id="s",
                                usage={"input_tokens": 5, "cache_read_input_tokens": 100,
                                       "output_tokens": 7})

    p._query = fake_query
    r = await p.chat([Message("system", "sys"), Message("user", "hi")])

    opts = captured["options"]
    assert opts.model == "claude-sonnet-4-6"
    assert opts.tools == []
    assert opts.max_turns == 1
    assert opts.setting_sources == []
    assert opts.env["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] == "1234"
    assert r.content == "halo"
    assert r.model == "claude-sonnet-4-6-20260101"
    assert (r.usage.input_tokens, r.usage.output_tokens) == (105, 7)
    assert r.done_reason == "stop"


async def test_claude_provider_raises_on_error_result():
    sdk = pytest.importorskip("claude_agent_sdk")
    from wef_agentic.llm.claude_agent_provider import ClaudeAgentSDKProvider

    p = ClaudeAgentSDKProvider(model="claude-sonnet-4-6")

    async def fake_query(prompt, options):
        yield sdk.ResultMessage(subtype="error_during_execution", duration_ms=1, duration_api_ms=1,
                                is_error=True, num_turns=1, session_id="s", errors=["boom"])

    p._query = fake_query
    with pytest.raises(RuntimeError, match="boom"):
        await p.chat([Message("user", "hi")])


async def test_claude_provider_reports_authentication_error_in_result_text():
    sdk = pytest.importorskip("claude_agent_sdk")
    from wef_agentic.llm.claude_agent_provider import ClaudeAgentSDKProvider

    p = ClaudeAgentSDKProvider(model="claude-sonnet-4-6")
    closed = []

    async def fake_query(prompt, options):
        try:
            yield sdk.ResultMessage(subtype="success", duration_ms=1, duration_api_ms=0,
                                    is_error=True, num_turns=1, session_id="s",
                                    result="Failed to authenticate: OAuth session expired")
        finally:
            closed.append(True)

    p._query = fake_query
    with pytest.raises(RuntimeError, match="OAuth session expired"):
        await p.chat([Message("user", "hi")])
    assert closed == [True]
