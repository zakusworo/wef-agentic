"""Universal types untuk LLM provider abstraction."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "user", "assistant", "tool"]


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
    model: str
    meta: dict[str, Any] = field(default_factory=dict)
