"""Critic Agent — WAJIB CORE per WEF (2026a) governance untuk low-readiness functions."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from wef_agentic.agents.base import Agent, AgentOutput

if TYPE_CHECKING:
    from wef_agentic.orchestration.nexus import NexusState


def format_checks(checks: list[dict]) -> str:
    icon = {"ok": "✓", "warn": "⚠", "fail": "✗"}
    return "\n".join(
        f"- {icon.get(c['status'], '?')} [{c['status'].upper()}] {c['name']}: {c['detail']}"
        for c in checks
    )


class CriticAgent(Agent):
    name = "critic"
    system_prompt = (
        "Anda adalah Critic Agent — auditor internal sistem multi-agent WEF Nexus. "
        "Tugas Anda KRITIS karena framework ini menarget functions di area LOW-READINESS "
        "menurut WEF (2026a): #43 Policy forecasting, #55 Policy impact prediction.\n\n"
        "Anda menerima (a) angka kunci deterministik, (b) hasil pemeriksaan konsistensi "
        "deterministik, dan (c) narasi tiga agen domain.\n\n"
        "Tugas spesifik:\n"
        "1. **Fidelity angka**: apakah setiap angka yang dikutip agen sama dengan angka kunci? "
        "Sebut angka yang salah kutip atau dikarang.\n"
        "2. **Konsistensi internal**: apakah klaim Water Agent kontradiktif dengan Energy / Food?\n"
        "3. **Pemeriksaan deterministik**: tanggapi setiap item WARN/FAIL — apakah agen "
        "menyadarinya, dan apa implikasinya?\n"
        "4. **Bias check**: apakah ada bias sektoral yang tidak di-acknowledge?\n"
        "5. **Error consequence**: identifikasi klaim yang error-nya akan punya konsekuensi besar "
        "(WEF 2026a sub-criterion 3.2).\n"
        "6. **Limitations transparency**: apakah agen lain JUJUR tentang limitasi model & data?\n\n"
        "Format output:\n"
        "- ✓ KONSISTEN: <hal-hal yang sudah baik>\n"
        "- ⚠ INKONSISTEN: <kontradiksi, salah kutip angka, atau gap>\n"
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
        nexus: NexusState,
    ) -> AgentOutput:
        warnings = "\n".join(f"- {w}" for w in nexus.warnings) or "- (tidak ada)"
        prompt = (
            "## Skenario Diaudit\n"
            + self._scenario_header(scenario, nexus)
            + "\n\n## Angka Kunci (deterministik — sumber kebenaran)\n\n"
            f"```json\n{json.dumps(nexus.key_figures(), indent=2, ensure_ascii=False)}\n```\n\n"
            "## Pemeriksaan Deterministik\n\n"
            f"{format_checks(nexus.checks)}\n\n"
            "## Peringatan Framework\n\n"
            f"{warnings}\n\n"
            "## Output Water Agent\n\n"
            f"{water_output.content}\n\n"
            "## Output Energy Agent\n\n"
            f"{energy_output.content}\n\n"
            "## Output Food Agent\n\n"
            f"{food_output.content}\n\n"
            "---\n\n"
            "Audit ketiga output di atas terhadap angka kunci dan pemeriksaan deterministik. "
            "Berikan hasil dalam format yang diminta."
        )

        response = await self._call_llm(prompt)
        return self._output(response)
