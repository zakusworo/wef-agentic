"""Agents package."""
from wef_agentic.agents.base import Agent, AgentOutput
from wef_agentic.agents.coordinator import CoordinatorAgent
from wef_agentic.agents.critic import CriticAgent
from wef_agentic.agents.energy import EnergyAgent
from wef_agentic.agents.food import FoodAgent
from wef_agentic.agents.water import WaterAgent

__all__ = [
    "Agent",
    "AgentOutput",
    "CoordinatorAgent",
    "CriticAgent",
    "EnergyAgent",
    "FoodAgent",
    "WaterAgent",
]
