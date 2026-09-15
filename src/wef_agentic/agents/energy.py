"""Energy Agent — location-agnostic."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wef_agentic.agents.base import NUMBERS_ARE_GIVEN_NOTE, Agent, AgentOutput

if TYPE_CHECKING:
    from wef_agentic.orchestration.nexus import NexusState


class EnergyAgent(Agent):
    name = "energy"
    system_prompt = (
        "Anda adalah Energy Agent dalam sistem WEF-Agentic untuk multi-city WEF Nexus. "
        "Anda menginterpretasi proyeksi demand listrik + emisi yang sudah dihitung framework.\n\n"
        "Tugas: interpretasi dalam Bahasa Indonesia formal. Fokus pada:\n"
        "- Demand tahun dasar, 2030, dan tahun horizon skenario\n"
        "- Tambahan demand pompa irigasi akibat perubahan iklim (coupling air→energi)\n"
        "- Emisi CO2 dengan grid factor yang diberikan\n"
        "- Konsumsi air pembangkit (off-site) — trade-off energi→air\n"
        "- Jika data_quality = 'illustrative': eksplisit menyebut bahwa angka adalah "
        "estimate country-level proxy × populasi lokasi, butuh data lokal untuk presisi\n"
        "- Caveat: model elasticity sederhana, bukan OSeMOSYS RES terkalibrasi\n\n"
        "Output: 1-2 paragraf naratif + bullet findings."
    )

    async def run(self, scenario: dict[str, Any], nexus: NexusState) -> AgentOutput:
        c = nexus.coupling
        tool_outputs = [
            {"tool": "get_electricity_history", "data": nexus.electricity_history},
            {"tool": "project_energy_demand", "data": nexus.energy_projection},
            {"tool": "estimate_emissions", "data": nexus.emissions},
            {"tool": "nexus_coupling_energy", "data": {
                "extra_pumping_demand_at_horizon_gwh": c["extra_pumping_demand_gwh"],
                "pumping_scenario": c["pumping_scenario"],
                "pumping_baseline_climate": c["pumping_baseline_climate"],
                "power_sector_water_m3_2030_offsite": c["power_sector_water_m3_2030"],
            }},
        ]

        prompt = (
            self._scenario_header(scenario, nexus) + "\n"
            f"Energy scenario: {scenario.get('energy_scenario', 'BAU')}, "
            f"renewable share 2030: {scenario.get('renewable_share_2030', 0.23)}\n\n"
            f"{NUMBERS_ARE_GIVEN_NOTE}\n\n"
            "Tool outputs:\n"
            + self._format_tool_outputs(tool_outputs)
            + "\n\nInterpretasikan dalam Bahasa Indonesia formal. Jika data illustrative, "
            "sebutkan eksplisit."
        )

        response = await self._call_llm(prompt)
        return self._output(response, tool_outputs)
