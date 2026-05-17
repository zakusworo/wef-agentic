"""Tools package — auto-register saat di-import."""
from wef_agentic.tools.energy_tools import *  # noqa: F403
from wef_agentic.tools.food_tools import *  # noqa: F403
from wef_agentic.tools.registry import (
    call_tool,
    get_tool,
    list_tool_names,
    list_tools,
)
from wef_agentic.tools.water_tools import *  # noqa: F403

__all__ = ["call_tool", "get_tool", "list_tool_names", "list_tools"]
