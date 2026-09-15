"""Universal types untuk LLM provider abstraction."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


class EmptyCompletionError(RuntimeError):
    """Model returned no answer text (e.g. a reasoning model spent its budget thinking)."""


@dataclass
class Message:
    role: Role
    content: str


@dataclass
class ToolSchema:
    """JSON-Schema based tool definition (universal across providers)."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema object


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class LLMResponse:
    content: str
    usage: Usage
    provider: str
    model: str                       # model the backend reports it actually used
    done_reason: str | None = None   # normalized: "stop" | "length" | backend-specific
    thinking: str = ""               # reasoning trace, if the backend exposes it
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def truncated(self) -> bool:
        return self.done_reason == "length"
