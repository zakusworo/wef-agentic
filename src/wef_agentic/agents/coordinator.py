"""Coordinator Agent — orchestrator utama."""
from __future__ import annotations

from typing import Any

from wef_agentic.agents.base import Agent, AgentOutput


class CoordinatorAgent(Agent):
    name = "coordinator"
    system_prompt = (
        "Anda adalah Coordinator dalam sistem multi-agent untuk WEF Nexus governance "
        "Kabupaten Sleman, D.I. Yogyakarta. Tugas Anda:\n\n"
        "1. Menerima query/skenario dari user/analis Bappeda.\n"
        "2. Menyintesis hasil analisis dari Water Agent, Energy Agent, Food Agent, "
        "dan Critic Agent menjadi narasi koheren dalam Bahasa Indonesia formal.\n"
        "3. Eksplisit menonjolkan TRADE-OFF antar sektor (water vs energy vs food).\n"
        "4. Eksplisit menyebutkan ketidakpastian dan limitasi data.\n\n"
        "Konteks: Sleman adalah lumbung padi DIY dengan 5 'reality fires':\n"
        "(1) krisis air tanah Sleman Tengah-Selatan; (2) alih fungsi LP2B; "
        "(3) beban grid pasca-subsidi; (4) ancaman Merapi VEI 3+ recurrent; "
        "(5) tekanan hidrolik pariwisata Borobudur-Prambanan-Merapi.\n\n"
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
    ) -> AgentOutput:
        prompt = (
            f"## Skenario Dianalisis\n\n"
            f"- Nama: **{scenario.get('name', 'UNNAMED')}**\n"
            f"- Iklim: {scenario.get('climate', 'baseline')}\n"
            f"- Policy: {scenario.get('policy', 'BAU')}\n"
            f"- LP2B protection: {scenario.get('lp2b_protection', 'moderate')}\n"
            f"- Horizon: {scenario.get('horizon', 2050)}\n\n"
            "## Hasil per Sektor\n\n"
            f"### Water Agent\n{water_output.content}\n\n"
            f"### Energy Agent\n{energy_output.content}\n\n"
            f"### Food Agent\n{food_output.content}\n\n"
            "## Audit dari Critic Agent\n\n"
            f"{critic_output.content}\n\n"
            "---\n\n"
            "Sintesis hasil di atas menjadi analisis koheren. Soroti trade-off, "
            "uncertainty, dan rekomendasi prioritas untuk Bappeda Sleman."
        )
        response = await self._call_llm(prompt)
        return AgentOutput(
            agent=self.name,
            content=response.content,
            usage_input_tokens=response.usage.input_tokens,
            usage_output_tokens=response.usage.output_tokens,
            provider=response.provider,
            model=response.model,
        )
