"""Critic Agent — WAJIB CORE per WEF (2026a) governance untuk low-readiness functions."""
from __future__ import annotations

from typing import Any

from wef_agentic.agents.base import Agent, AgentOutput


class CriticAgent(Agent):
    name = "critic"
    system_prompt = (
        "Anda adalah Critic Agent — auditor internal sistem multi-agent WEF Nexus Sleman. "
        "Tugas Anda KRITIS karena framework ini menarget functions di area LOW-READINESS "
        "menurut WEF (2026a): #43 Policy forecasting, #55 Policy impact prediction.\n\n"
        "Tugas spesifik:\n"
        "1. **Konsistensi internal**: apakah klaim Water Agent kontradiktif dengan Energy / Food?\n"
        "2. **Mass-balance check**: apakah air yang dipakai irigasi + PLTA + PDAM masuk akal?\n"
        "3. **Bias check**: apakah ada bias sektoral yang tidak di-acknowledge?\n"
        "4. **Error consequence**: identifikasi klaim yang error-nya akan punya konsekuensi besar "
        "(WEF 2026a sub-criterion 3.2).\n"
        "5. **Limitations transparency**: apakah agen lain JUJUR tentang limitasi model?\n\n"
        "Format output:\n"
        "- ✓ KONSISTEN: <hal-hal yang sudah baik>\n"
        "- ⚠ INKONSISTEN: <kontradiksi atau gap>\n"
        "- ⚙ MISSING: <hal yang belum di-cover>\n"
        "- 🚩 ERROR CONSEQUENCE HIGH: <klaim yang harus di-flag untuk review manusia>\n\n"
        "Bahasa Indonesia formal. Maksimal 1 halaman."
    )

    async def audit(
        self,
        scenario: dict[str, Any],
        water_output: AgentOutput,
        energy_output: AgentOutput,
        food_output: AgentOutput,
    ) -> AgentOutput:
        prompt = (
            f"## Skenario Diaudit\n"
            f"Nama: {scenario.get('name', 'UNNAMED')}\n\n"
            "## Output Water Agent\n\n"
            f"{water_output.content}\n\n"
            "## Output Energy Agent\n\n"
            f"{energy_output.content}\n\n"
            "## Output Food Agent\n\n"
            f"{food_output.content}\n\n"
            "---\n\n"
            "Audit ketiga output di atas. Berikan hasil dalam format yang diminta."
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
