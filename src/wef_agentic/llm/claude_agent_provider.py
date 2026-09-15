"""Claude Agent SDK provider — pakai Claude Code subscription via claude-agent-sdk."""
from __future__ import annotations

from wef_agentic.llm.provider import LLMProvider
from wef_agentic.llm.types import LLMResponse, Message, ToolSchema, Usage

# Anthropic stop_reason → normalized done_reason (matches Ollama's vocabulary)
_STOP_REASON_MAP = {"end_turn": "stop", "stop_sequence": "stop", "max_tokens": "length"}


class ClaudeAgentSDKProvider(LLMProvider):
    """Wraps claude-agent-sdk untuk mengakses Claude via Claude Code subscription.

    Tidak butuh ANTHROPIC_API_KEY — uses subscription billing.
    One-shot query() per call: no tools, one turn, no user/project settings, so the
    agent is a pure reasoning step and runs are reproducible across machines.

    `temperature` is not exposed by the SDK and is ignored (recorded in meta).
    """

    name = "claude-agent-sdk"

    def __init__(self, model: str, max_tokens: int = 4096, temperature: float = 0.2):
        super().__init__(model=model, max_tokens=max_tokens, temperature=temperature)
        # Lazy import — SDK butuh Claude Code CLI installed
        try:
            import claude_agent_sdk as sdk  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "claude-agent-sdk tidak ter-install. Jalankan: pip install -e '.[claude]'"
            ) from e
        self._sdk = sdk
        self._query = sdk.query

    def build_options(self, system_prompt: str | None):
        return self._sdk.ClaudeAgentOptions(
            model=self.model,
            system_prompt=system_prompt,
            tools=[],             # `--tools ""` disables all built-ins (allowed_tools=[] does not)
            max_turns=1,
            setting_sources=[],   # don't inject the user's CLAUDE.md / settings into the prompt
            env={"CLAUDE_CODE_MAX_OUTPUT_TOKENS": str(self.max_tokens)},
        )

    async def chat(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None,
    ) -> LLMResponse:
        # Claude Agent SDK pattern: system_prompt + single prompt string
        system_parts: list[str] = []
        prompt_parts: list[str] = []

        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            elif m.role == "user":
                prompt_parts.append(m.content)
            elif m.role == "assistant":
                # Untuk one-shot query, kita inline conversation history sebagai context
                prompt_parts.append(f"[Previous assistant turn]: {m.content}")

        system_prompt = "\n\n".join(system_parts) if system_parts else None
        prompt = "\n\n".join(prompt_parts) if prompt_parts else ""
        options = self.build_options(system_prompt)

        content_chunks: list[str] = []
        thinking_chunks: list[str] = []
        reported_model = ""
        stop_reason: str | None = None
        usage = Usage()

        async for msg in self._query(prompt=prompt, options=options):
            if isinstance(msg, self._sdk.AssistantMessage):
                reported_model = msg.model or reported_model
                stop_reason = msg.stop_reason or stop_reason
                for block in msg.content or []:
                    if isinstance(block, self._sdk.TextBlock):
                        content_chunks.append(block.text)
                    elif isinstance(block, self._sdk.ThinkingBlock):
                        thinking_chunks.append(block.thinking)
            elif isinstance(msg, self._sdk.ResultMessage):
                if msg.is_error:
                    detail = "; ".join(msg.errors or []) or msg.subtype
                    raise RuntimeError(f"Claude Agent SDK call failed ({self.model}): {detail}")
                stop_reason = msg.stop_reason or stop_reason
                u = msg.usage or {}
                # Cached prompt tokens are still processed tokens for footprint purposes
                usage = Usage(
                    input_tokens=(u.get("input_tokens", 0)
                                  + u.get("cache_creation_input_tokens", 0)
                                  + u.get("cache_read_input_tokens", 0)),
                    output_tokens=u.get("output_tokens", 0),
                )

        return LLMResponse(
            content="".join(content_chunks),
            usage=usage,
            provider=self.name,
            model=reported_model or self.model,
            done_reason=_STOP_REASON_MAP.get(stop_reason or "", stop_reason),
            thinking="".join(thinking_chunks),
            meta={"temperature_applied": False},
        )
