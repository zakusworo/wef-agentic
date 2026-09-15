"""Food Agent — location-agnostic."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wef_agentic.agents.base import NUMBERS_ARE_GIVEN_NOTE, Agent, AgentOutput

if TYPE_CHECKING:
    from wef_agentic.orchestration.nexus import NexusState


class FoodAgent(Agent):
    name = "food"
    system_prompt = (
        "Anda adalah Food Agent dalam sistem WEF-Agentic untuk multi-city WEF Nexus. "
        "Anda menginterpretasi proyeksi produksi pangan + ketahanan pangan (SSL) yang sudah "
        "dihitung framework.\n\n"
        "Tugas: interpretasi dalam Bahasa Indonesia formal. Fokus pada:\n"
        "- Produksi 2030 & tahun horizon dengan asumsi LP2B protection\n"
        "- Water stress berasal dari water balance setelah irigasi (coupling air→pangan), "
        "bukan asumsi skenario\n"
        "- SSL: surplus atau defisit?\n"
        "- Trade-off dengan sektor air (padi = water-intensive, pompa air tanah)\n"
        "- Jika project_crop_yield.available = false: jelaskan kesenjangan data dan data apa "
        "yang dibutuhkan; JANGAN mengarang angka produksi atau SSL\n"
        "- Caveat: Doorenbos-Kassam empirical, bukan DSSAT/AquaCrop terkalibrasi\n\n"
        "Output: 1-2 paragraf naratif + bullet findings."
    )

    async def run(self, scenario: dict[str, Any], nexus: NexusState) -> AgentOutput:
        c = nexus.coupling
        tool_outputs = [
            {"tool": "get_food_history", "data": nexus.food_history},
            {"tool": "project_crop_yield", "data": nexus.crop_projection},
        ]
        if nexus.food_ssl is not None:
            tool_outputs.append({"tool": "compute_food_ssl", "data": nexus.food_ssl})
        tool_outputs.append({"tool": "nexus_coupling_food", "data": {
            "water_stress_raw": c["water_stress_raw"],
            "irrigation_supply_fraction": c["irrigation_supply_fraction"],
            "water_stress_effective": c["water_stress_effective"],
        }})

        prompt = (
            self._scenario_header(scenario, nexus) + "\n"
            f"Crop: {scenario.get('food_crop', 'padi')}, "
            f"LP2B: {scenario.get('lp2b_protection', 'moderate')}\n\n"
            f"{NUMBERS_ARE_GIVEN_NOTE}\n\n"
            "Tool outputs:\n"
            + self._format_tool_outputs(tool_outputs)
            + "\n\nInterpretasikan dalam Bahasa Indonesia formal. Jika data illustrative "
            "atau tidak tersedia, sebutkan eksplisit."
        )

        response = await self._call_llm(prompt)
        return self._output(response, tool_outputs)
