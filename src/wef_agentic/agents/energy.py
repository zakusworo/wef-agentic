"""Energy Agent — location-agnostic."""
from __future__ import annotations

from typing import Any

from wef_agentic.agents.base import Agent, AgentOutput
from wef_agentic.tools import call_tool


class EnergyAgent(Agent):
    name = "energy"
    system_prompt = (
        "Anda adalah Energy Agent dalam sistem WEF-Agentic untuk multi-city WEF Nexus. "
        "Anda menganalisis demand projection listrik + emisi.\n\n"
        "Tugas: interpretasi hasil tool dalam Bahasa Indonesia formal. Fokus pada:\n"
        "- Demand 2030 dan 2050\n"
        "- Emisi CO2 dengan grid factor country-specific\n"
        "- Trade-off dengan sektor air (PLTA/PLTMH butuh air)\n"
        "- Jika data_quality = 'illustrative': eksplisit menyebut bahwa angka adalah "
        "estimate country-level proxy × populasi lokasi, butuh data lokal untuk presisi\n"
        "- Caveat: model elasticity sederhana, bukan OSeMOSYS RES terkalibrasi\n\n"
        "Output: 1-2 paragraf naratif + bullet findings."
    )

    async def run(self, scenario: dict[str, Any]) -> AgentOutput:
        location_query = scenario.get("location_query", "sleman")
        energy_scenario = scenario.get("energy_scenario", "BAU")
        horizon = scenario.get("horizon", 2050)
        renewable_share = scenario.get("renewable_share_2030", 0.23)

        history = call_tool("get_electricity_history", location_query=location_query)
        proj = call_tool(
            "project_energy_demand",
            location_query=location_query,
            scenario=energy_scenario,
            horizon=horizon,
        )
        country_code = proj["location"].get("country_code", "ID")
        demand_2030 = proj["endpoints"].get("demand_2030_gwh") or 0.0
        emissions = call_tool(
            "estimate_emissions",
            demand_gwh=demand_2030,
            renewable_share=renewable_share,
            country_code=country_code,
        )

        tool_outputs = [
            {"tool": "get_electricity_history", "data": history},
            {"tool": "project_energy_demand", "data": proj},
            {"tool": "estimate_emissions", "data": emissions},
        ]

        prompt = (
            f"Skenario: {scenario.get('name', 'UNNAMED')}\n"
            f"Lokasi: {proj['location']['name']} ({proj['location'].get('country', '')})\n"
            f"Energy scenario: {energy_scenario}, horizon: {horizon}, "
            f"renewable share 2030: {renewable_share}\n\n"
            "Tool outputs:\n"
            + self._format_tool_outputs(tool_outputs)
            + "\n\nInterpretasikan dalam Bahasa Indonesia formal. Jika data illustrative, "
            "sebutkan eksplisit."
        )

        response = await self._call_llm(prompt)
        return AgentOutput(
            agent=self.name,
            content=response.content,
            tool_outputs=tool_outputs,
            usage_input_tokens=response.usage.input_tokens,
            usage_output_tokens=response.usage.output_tokens,
            provider=response.provider,
            model=response.model,
        )
