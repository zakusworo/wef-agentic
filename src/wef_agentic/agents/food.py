"""Food Agent — location-agnostic."""
from __future__ import annotations

from typing import Any

from wef_agentic.agents.base import Agent, AgentOutput
from wef_agentic.tools import call_tool


class FoodAgent(Agent):
    name = "food"
    system_prompt = (
        "Anda adalah Food Agent dalam sistem WEF-Agentic untuk multi-city WEF Nexus. "
        "Anda menganalisis produksi pangan + ketahanan pangan (SSL).\n\n"
        "Tugas: interpretasi hasil tool dalam Bahasa Indonesia formal. Fokus pada:\n"
        "- Produksi 2030 & 2050 dengan asumsi water stress + LP2B protection\n"
        "- SSL: surplus atau defisit?\n"
        "- Trade-off dengan sektor air (rice = water-intensive)\n"
        "- Jika data_quality = 'illustrative': sebutkan bahwa parameter Sleman di-proxy ke "
        "lokasi lain, butuh FAOSTAT/national survey untuk presisi\n"
        "- Caveat: Doorenbos-Kassam empirical, bukan DSSAT terkalibrasi\n\n"
        "Output: 1-2 paragraf naratif + bullet findings."
    )

    async def run(self, scenario: dict[str, Any]) -> AgentOutput:
        location_query = scenario.get("location_query", "sleman")
        crop = scenario.get("food_crop", "padi")
        food_scenario = scenario.get("energy_scenario", "BAU")
        water_stress = scenario.get("water_stress_fraction", 0.05)
        lp2b = scenario.get("lp2b_protection", "moderate")
        horizon = scenario.get("horizon", 2050)

        history = call_tool("get_food_history", location_query=location_query)
        proj = call_tool(
            "project_crop_yield",
            location_query=location_query,
            crop=crop,
            scenario=food_scenario,
            water_stress_fraction=water_stress,
            lp2b_protection=lp2b,
            horizon=horizon,
        )
        production_2030 = proj["endpoints"].get("production_2030_t") or 0.0
        ssl = call_tool(
            "compute_food_ssl",
            production_t=production_2030,
            location_query=location_query,
            year=2030,
        )

        tool_outputs = [
            {"tool": "get_food_history", "data": history},
            {"tool": "project_crop_yield", "data": proj},
            {"tool": "compute_food_ssl", "data": ssl},
        ]

        prompt = (
            f"Skenario: {scenario.get('name', 'UNNAMED')}\n"
            f"Lokasi: {proj['location']['name']} ({proj['location'].get('country', '')})\n"
            f"Crop: {crop}, scenario: {food_scenario}, water stress: {water_stress}, "
            f"LP2B: {lp2b}\n\n"
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
