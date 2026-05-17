"""Pre-defined scenarios — location-agnostic, 5 scenarios (Phase 1)."""
from __future__ import annotations

SCENARIOS = {
    "S1_BAU_2030": {
        "name": "S1 — BAU 2030",
        "description": "Business-as-usual: tren existing tanpa intervensi tambahan",
        "location_query": "sleman",
        "climate": "Baseline (trend extrapolation)",
        "policy": "RUPTL existing, LP2B moderate, no extra intervention",
        "delta_precip_pct": -2.0,
        "delta_temp_c": 0.7,
        "energy_scenario": "BAU",
        "renewable_share_2030": 0.23,
        "water_stress_fraction": 0.05,
        "lp2b_protection": "moderate",
        "horizon": 2030,
        "water_baseline_year": 2023,
        "water_station": None,
        "food_crop": "padi",
    },
    "S2_JETP_Aligned": {
        "name": "S2 — JETP-Aligned 2030",
        "description": "Aligned dengan JETP CIPP pathway",
        "location_query": "sleman",
        "climate": "Baseline + warming SSP2-4.5",
        "policy": "EBT 34% by 2030, LP2B moderate, induction cooker partial",
        "delta_precip_pct": -3.0,
        "delta_temp_c": 1.0,
        "energy_scenario": "JETP_Aligned",
        "renewable_share_2030": 0.34,
        "water_stress_fraction": 0.07,
        "lp2b_protection": "moderate",
        "horizon": 2030,
        "water_baseline_year": 2023,
        "water_station": None,
        "food_crop": "padi",
    },
    "S3_NetZero_2045": {
        "name": "S3 — Net-Zero 2045",
        "description": "PLTS rooftop masif + LP2B strict + EV/induction transition",
        "location_query": "sleman",
        "climate": "Baseline + warming SSP1-2.6",
        "policy": "EBT 45% by 2030, LP2B strict, EV+induction full transition",
        "delta_precip_pct": -1.0,
        "delta_temp_c": 0.5,
        "energy_scenario": "NetZero_Sleman_2045",
        "renewable_share_2030": 0.45,
        "water_stress_fraction": 0.04,
        "lp2b_protection": "strict",
        "horizon": 2045,
        "water_baseline_year": 2023,
        "water_station": None,
        "food_crop": "padi",
    },
    "S4_Climate_Stress": {
        "name": "S4 — Climate Stress 2030",
        "description": "SSP5-8.5 + ENSO-induced drought + erupsi Merapi VEI 3 di T+3",
        "location_query": "sleman",
        "climate": "Severe warming SSP5-8.5 + drought",
        "policy": "Inertia (no climate adaptation), water stress amplified",
        "delta_precip_pct": -15.0,
        "delta_temp_c": 1.8,
        "energy_scenario": "BAU",
        "renewable_share_2030": 0.23,
        "water_stress_fraction": 0.25,
        "lp2b_protection": "moderate",
        "horizon": 2030,
        "water_baseline_year": 2023,
        "water_station": None,
        "food_crop": "padi",
        "hazard": "Merapi VEI 3 di year+3, lahar dingin disrupts intake PDAM + irigasi",
    },
    "S5_Tourism_Boom": {
        "name": "S5 — KSPN Borobudur Boom 2030",
        "description": "2 juta+ wisatawan/tahun, konversi LP2B → hospitality, water demand naik",
        "location_query": "sleman",
        "climate": "Baseline + warming SSP2-4.5",
        "policy": "Pariwisata-prioritas, LP2B lax, water extraction hotel ↑",
        "delta_precip_pct": -3.0,
        "delta_temp_c": 1.0,
        "energy_scenario": "BAU",
        "renewable_share_2030": 0.25,
        "water_stress_fraction": 0.18,
        "lp2b_protection": "lax",
        "horizon": 2030,
        "water_baseline_year": 2023,
        "water_station": None,
        "food_crop": "padi",
        "context": "Beban hidrolik pariwisata Borobudur-Prambanan-Merapi trail",
    },
}


def get_scenario(scenario_id: str, location_query: str | None = None) -> dict:
    """Get scenario template. Optional override location_query (untuk custom city)."""
    if scenario_id not in SCENARIOS:
        raise KeyError(f"Unknown scenario: {scenario_id}. Available: {list(SCENARIOS)}")
    sc = SCENARIOS[scenario_id].copy()
    if location_query:
        sc["location_query"] = location_query
    return sc


def list_scenarios() -> list[dict]:
    return [{"id": k, **v} for k, v in SCENARIOS.items()]
