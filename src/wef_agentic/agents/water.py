"""Water Agent — location-agnostic."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wef_agentic.agents.base import NUMBERS_ARE_GIVEN_NOTE, Agent, AgentOutput

if TYPE_CHECKING:
    from wef_agentic.orchestration.nexus import NexusState


class WaterAgent(Agent):
    name = "water"
    system_prompt = (
        "Anda adalah Water Agent dalam sistem WEF-Agentic untuk multi-city WEF Nexus governance. "
        "Anda menginterpretasi hasil Thornthwaite-Mather monthly water balance (depletion "
        "eksponensial) dan coupling irigasi yang sudah dihitung framework.\n\n"
        "Tugas: interpretasi dalam Bahasa Indonesia formal. Fokus pada:\n"
        "- Surplus vs defisit tahunan DAN musiman (surplus musim hujan tidak otomatis menutup "
        "defisit musim kemarau)\n"
        "- Water stress sebelum vs sesudah irigasi, dan kebutuhan irigasi\n"
        "- Volume air tanah yang dipompa untuk irigasi\n"
        "- Risiko fisik dari skenario (climate delta)\n"
        "- Konteks spesifik lokasi (gunakan isu kunci & sub-DAS jika diberikan)\n"
        "- Apa yang BELUM bisa dianalisis dengan model simplified (caveat)\n\n"
        "Output: 1-2 paragraf naratif + bullet findings."
    )

    async def run(self, scenario: dict[str, Any], nexus: NexusState) -> AgentOutput:
        c = nexus.coupling
        tool_outputs = [
            {"tool": "get_climate_summary", "data": nexus.climate_summary},
            {"tool": "run_water_balance", "data": nexus.water_balance},
            {"tool": "compute_irrigation_demand", "data": nexus.irrigation},
            {"tool": "nexus_coupling_water", "data": {
                "water_stress_raw": c["water_stress_raw"],
                "irrigation_supply_fraction": c["irrigation_supply_fraction"],
                "water_stress_effective": c["water_stress_effective"],
                "irrigated_physical_area_ha": c["irrigated_physical_area_ha"],
                "pumping_scenario": c["pumping_scenario"],
                "baseline_climate_deficit_mm":
                    nexus.water_balance_baseline["summary"]["total_deficit_mm"],
            }},
        ]

        prompt = (
            self._scenario_header(scenario, nexus) + "\n"
            f"Climate delta: precip {scenario.get('delta_precip_pct', 0.0):+.1f}%, "
            f"temp {scenario.get('delta_temp_c', 0.0):+.1f}°C terhadap tahun "
            f"{nexus.water_balance['year']}\n\n"
            f"{NUMBERS_ARE_GIVEN_NOTE}\n\n"
            "Tool outputs:\n"
            + self._format_tool_outputs(tool_outputs)
            + "\n\nInterpretasikan dalam Bahasa Indonesia formal. Soroti water stress, "
            "ketidaksesuaian musiman, dan kebutuhan irigasi untuk lokasi spesifik."
        )

        response = await self._call_llm(prompt)
        return self._output(response, tool_outputs)
