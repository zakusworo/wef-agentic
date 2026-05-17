"""Water Agent — location-agnostic."""
from __future__ import annotations

from typing import Any

from wef_agentic.agents.base import Agent, AgentOutput
from wef_agentic.tools import call_tool


class WaterAgent(Agent):
    name = "water"
    system_prompt = (
        "Anda adalah Water Agent dalam sistem WEF-Agentic untuk multi-city WEF Nexus governance. "
        "Anda menganalisis ketersediaan air dan kebutuhan irigasi berdasarkan "
        "Thornthwaite-Mather monthly water balance dengan data Open-Meteo realtime.\n\n"
        "Tugas: interpretasi hasil tool dalam Bahasa Indonesia formal. Fokus pada:\n"
        "- Surplus vs deficit annual\n"
        "- Implikasi terhadap irigasi pertanian\n"
        "- Risiko fisik dari skenario (climate delta)\n"
        "- Konteks spesifik lokasi (jika Sleman: sub-DAS Code/Opak/Kuning/Boyong + krisis air tanah; "
        "lainnya: konteks geografis sesuai negara/wilayah)\n"
        "- Apa yang BELUM bisa dianalisis dengan model simplified (caveat)\n\n"
        "Output: 1-2 paragraf naratif + bullet findings."
    )

    async def run(self, scenario: dict[str, Any]) -> AgentOutput:
        location_query = scenario.get("location_query", "sleman")
        station = scenario.get("water_station")  # None = auto pilih sesuai location
        year = scenario.get("water_baseline_year", 2023)
        delta_p = scenario.get("delta_precip_pct", 0.0)
        delta_t = scenario.get("delta_temp_c", 0.0)

        climate_summary = call_tool("get_climate_summary", location_query=location_query)
        wb_kwargs = {
            "location_query": location_query,
            "year": year,
            "delta_precip_pct": delta_p,
            "delta_temp_c": delta_t,
        }
        if station:
            wb_kwargs["station"] = station
        wb = call_tool("run_water_balance", **wb_kwargs)
        irr_demand = call_tool(
            "compute_irrigation_demand",
            deficit_mm=wb["summary"]["total_deficit_mm"],
        )

        tool_outputs = [
            {"tool": "get_climate_summary", "data": climate_summary},
            {"tool": "run_water_balance", "data": wb},
            {"tool": "compute_irrigation_demand", "data": irr_demand},
        ]

        loc_display = wb["location"]["name"]
        country = wb["location"].get("country", "")
        prompt = (
            f"Skenario: {scenario.get('name', 'UNNAMED')}\n"
            f"Lokasi: {loc_display}{' (' + country + ')' if country else ''}\n"
            f"Climate delta: precip {delta_p:+.1f}%, temp {delta_t:+.1f}°C\n"
            f"Year analyzed: {year}\n\n"
            "Tool outputs:\n"
            + self._format_tool_outputs(tool_outputs)
            + "\n\nInterpretasikan dalam Bahasa Indonesia formal. Soroti water stress + "
            "irrigation demand untuk lokasi spesifik."
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
