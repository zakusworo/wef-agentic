"""Tool registry — universal mapping (name → callable + schema).

Agen memanggil tool via `call_tool(name, **kwargs)`. Schema disediakan untuk
future native LLM tool-calling (Phase 1+).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from wef_agentic.llm.types import ToolSchema


@dataclass
class Tool:
    schema: ToolSchema
    fn: Callable[..., Any]


_REGISTRY: dict[str, Tool] = {}


def register(name: str, description: str, parameters: dict):
    """Decorator untuk register tool."""
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        _REGISTRY[name] = Tool(
            schema=ToolSchema(name=name, description=description, parameters=parameters),
            fn=fn,
        )
        return fn
    return deco


def get_tool(name: str) -> Tool:
    if name not in _REGISTRY:
        raise KeyError(f"Tool not registered: {name}. Available: {list(_REGISTRY)}")
    return _REGISTRY[name]


def call_tool(name: str, **kwargs: Any) -> Any:
    return get_tool(name).fn(**kwargs)


def list_tools() -> list[ToolSchema]:
    return [t.schema for t in _REGISTRY.values()]


def list_tool_names() -> list[str]:
    return list(_REGISTRY.keys())
