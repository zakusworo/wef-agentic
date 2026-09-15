"""Coordinator Agent — synthesis across sectors."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from wef_agentic.agents.base import Agent, AgentOutput
from wef_agentic.agents.critic import format_checks

if TYPE_CHECKING:
    from wef_agentic.orchestration.nexus import NexusState


class CoordinatorAgent(Agent):
    name = "coordinator"
    system_prompt = (
        "Anda adalah Coordinator dalam sistem multi-agent untuk WEF Nexus governance "
        "tingkat sub-nasional. Tugas Anda:\n\n"
        "1. Menyintesis hasil analisis dari Water Agent, Energy Agent, Food Agent, "
        "dan Critic Agent menjadi narasi koheren dalam Bahasa Indonesia formal.\n"
        "2. Eksplisit menonjolkan TRADE-OFF antar sektor (water vs energy vs food), "
        "berdasarkan coupling yang dihitung framework.\n"
        "3. Eksplisit menyebutkan ketidakpastian, limitasi data, dan temuan Critic.\n"
        "4. Hanya mengutip angka dari angka kunci; jangan mengarang angka.\n\n"
        "Gunakan isu kunci lokasi jika diberikan; jangan membawa konteks wilayah lain.\n\n"
        "Format output: ringkasan eksekutif (2-3 paragraf) + bullet-point findings "
        "+ rekomendasi prioritas + caveat."
    )

    async def synthesize(
        self,
        scenario: dict[str, Any],
        water_output: AgentOutput,
        energy_output: AgentOutput,
        food_output: AgentOutput,
        critic_output: AgentOutput,
        nexus: NexusState,
    ) -> AgentOutput:
        prompt = (
            "## Skenario Dianalisis\n\n"
            + self._scenario_header(scenario, nexus)
            + f"\nIklim: {scenario.get('climate', 'baseline')}\n"
            f"Policy: {scenario.get('policy', 'BAU')}\n"
            f"LP2B protection: {scenario.get('lp2b_protection', 'moderate')}\n\n"
            "## Angka Kunci (deterministik)\n\n"
            f"```json\n{json.dumps(nexus.key_figures(), indent=2, ensure_ascii=False)}\n```\n\n"
            "## Pemeriksaan Deterministik\n\n"
            f"{format_checks(nexus.checks)}\n\n"
            "## Hasil per Sektor\n\n"
            f"### Water Agent\n{water_output.content}\n\n"
            f"### Energy Agent\n{energy_output.content}\n\n"
            f"### Food Agent\n{food_output.content}\n\n"
            "## Audit dari Critic Agent\n\n"
            f"{critic_output.content}\n\n"
            "---\n\n"
            "Sintesis hasil di atas menjadi analisis koheren. Soroti trade-off, "
            f"uncertainty, dan rekomendasi prioritas untuk pemerintah daerah "
            f"{nexus.location_context['display']}."
        )
        response = await self._call_llm(prompt)
        return self._output(response)
