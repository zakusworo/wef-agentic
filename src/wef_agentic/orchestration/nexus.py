"""Deterministic nexus pre-computation.

Runs every physical model once per scenario, couples the sectors, and performs
screening consistency checks — all before any LLM is called. Agents then only
interpret `NexusState`; they never produce the numbers.

    climate Δ → water balance (scenario + baseline climate)
      ├─ water stress after irrigation → crop yield → production → SSL
      ├─ irrigation groundwater pumping (scenario − baseline) → electricity demand
      └─ electricity demand × renewable share → emissions + power-sector water
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from wef_agentic.config.settings import load_nexus_config
from wef_agentic.data.country_defaults import GRID_EMISSION_FACTOR, get_default
from wef_agentic.geo import Location, remember_location
from wef_agentic.physics.coupling import (
    irrigation_pumping,
    power_sector_water_m3,
    stress_after_irrigation,
)
from wef_agentic.physics.energy_demand import SCENARIOS as ENERGY_SCENARIOS
from wef_agentic.tools import call_tool
from wef_agentic.tools._common import resolve_or_raise, resolve_packet

OK, WARN, FAIL = "ok", "warn", "fail"


@dataclass
class NexusState:
    scenario_name: str
    location: dict
    location_context: dict
    climate_summary: dict
    water_balance: dict
    water_balance_baseline: dict
    irrigation: dict
    coupling: dict
    electricity_history: dict
    energy_projection: dict
    emissions: dict
    food_history: dict
    crop_projection: dict
    food_ssl: dict | None
    provenance: list[dict] = field(default_factory=list)
    checks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def food_available(self) -> bool:
        return bool(self.crop_projection.get("available"))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def key_figures(self) -> dict[str, Any]:
        """Compact numbers every agent (and the critic) can cite and be checked against."""
        wb = self.water_balance["summary"]
        c = self.coupling
        pump = c.get("pumping_scenario") or {}
        ep = self.energy_projection["endpoints"]
        crop = self.crop_projection
        return {
            "lokasi": self.location.get("name"),
            "tahun_dasar_air": self.water_balance.get("year"),
            "horizon": self.energy_projection.get("horizon"),
            "air": {
                "hujan_mm": round(wb["total_precip_mm"], 1),
                "pet_mm": round(wb["total_pet_mm"], 1),
                "eta_mm": round(wb["total_eta_mm"], 1),
                "surplus_mm": round(wb["total_surplus_mm"], 1),
                "defisit_mm": round(wb["total_deficit_mm"], 1),
                "water_stress_tanpa_irigasi": c["water_stress_raw"],
                "water_stress_setelah_irigasi": c["water_stress_effective"],
                "kebutuhan_irigasi_bruto_mm": round(self.irrigation["irrigation_demand_mm"], 1),
                "air_tanah_dipompa_juta_m3": (round(pump["groundwater_volume_m3"] / 1e6, 3)
                                              if pump else None),
            },
            "energi": {
                "demand_tahun_dasar_gwh": _r(ep.get("demand_base_gwh")),
                "demand_2030_gwh": _r(ep.get("demand_2030_gwh")),
                "demand_horizon_gwh": _r(ep.get("demand_horizon_gwh")),
                "tambahan_pompa_irigasi_akibat_iklim_gwh": round(c["extra_pumping_demand_gwh"], 3),
                "porsi_ebt_2030": self.emissions["renewable_share"],
                "faktor_emisi_grid_kg_per_kwh": self.emissions["grid_emission_factor_kg_co2_per_kwh"],
                "emisi_2030_mt_co2": self.emissions["co2_emissions_mt"],
                "air_konsumsi_pembangkit_2030_juta_m3_offsite": round(
                    c["power_sector_water_m3_2030"] / 1e6, 2),
            },
            "pangan": (
                {
                    "tersedia": True,
                    "luas_panen_dasar_ha": _r(crop["assumptions"]["base_area_ha"]),
                    "luas_panen_horizon_ha": _r(crop["endpoints"]["area_horizon_ha"]),
                    "yield_model_t_ha": round(crop["endpoints"]["yield_t_ha"], 2),
                    "yield_observasi_t_ha": crop.get("observed_yield_t_ha"),
                    "produksi_2030_t": _r(crop["endpoints"]["production_2030_t"]),
                    "produksi_horizon_t": _r(crop["endpoints"]["production_horizon_t"]),
                    "ssl_2030": self.food_ssl["ssl"] if self.food_ssl else None,
                    "populasi_2030": self.food_ssl["population"] if self.food_ssl else None,
                }
                if self.food_available
                else {"tersedia": False, "alasan": crop.get("reason")}
            ),
        }


def _r(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def compute_nexus(scenario: dict, location: Location | None = None) -> NexusState:
    """Run all deterministic models for `scenario`. Blocking (network/file IO)."""
    cfg = load_nexus_config()
    irr_cfg = cfg.get("irrigation") or {}
    psw_cfg = cfg.get("power_sector_water") or {}

    query = scenario.get("location_query", "sleman")
    if location is not None:
        remember_location(query, location)
    loc = resolve_or_raise(query)

    year = scenario.get("water_baseline_year", 2023)
    horizon = scenario.get("horizon", 2050)
    energy_scenario = scenario.get("energy_scenario", "BAU")
    renewable_share = scenario.get("renewable_share_2030", 0.23)
    warnings: list[str] = []

    # ── Water ────────────────────────────────────────────────────────────────
    wb_kwargs: dict[str, Any] = {"location_query": query, "year": year}
    if scenario.get("water_station"):
        wb_kwargs["station"] = scenario["water_station"]
    climate = call_tool("get_climate_summary", location_query=query)
    wb_baseline = call_tool("run_water_balance", **wb_kwargs)
    wb = call_tool(
        "run_water_balance", **wb_kwargs,
        delta_precip_pct=scenario.get("delta_precip_pct", 0.0),
        delta_temp_c=scenario.get("delta_temp_c", 0.0),
    )
    irrigation = call_tool(
        "compute_irrigation_demand",
        deficit_mm=wb["summary"]["total_deficit_mm"],
        application_efficiency=irr_cfg.get("application_efficiency", 0.65),
    )

    # ── Water → food ─────────────────────────────────────────────────────────
    raw_stress = wb["water_stress_raw"]
    supply_fraction = irr_cfg.get("supply_fraction", 0.6)
    effective_stress = round(stress_after_irrigation(raw_stress, supply_fraction), 4)
    if scenario.get("water_stress_override") is not None:
        effective_stress = float(scenario["water_stress_override"])
        warnings.append(
            f"water_stress_override={effective_stress} dipakai; coupling air→pangan dinonaktifkan."
        )

    food_history = call_tool("get_food_history", location_query=query)
    crop = call_tool(
        "project_crop_yield",
        location_query=query,
        crop=scenario.get("food_crop", "padi"),
        scenario=scenario.get("name", energy_scenario),
        water_stress_fraction=effective_stress,
        lp2b_protection=scenario.get("lp2b_protection", "moderate"),
        horizon=horizon,
    )
    warnings.extend(crop.get("warnings", []))

    # ── Water → energy (irrigation pumping, climate-driven delta) ────────────
    pumping_scenario = pumping_baseline = None
    extra_pumping_gwh = 0.0
    physical_area_ha = None
    if crop.get("available"):
        physical_area_ha = crop["endpoints"]["area_horizon_ha"] / irr_cfg.get("cropping_intensity", 2.0)
        pump_kwargs = {
            "physical_area_ha": physical_area_ha,
            "application_efficiency": irr_cfg.get("application_efficiency", 0.65),
            "supply_fraction": supply_fraction,
            "groundwater_share": irr_cfg.get("groundwater_share", 0.3),
            "head_m": irr_cfg.get("pump_head_m", 30.0),
            "pump_efficiency": irr_cfg.get("pump_efficiency", 0.45),
        }
        pumping_scenario = irrigation_pumping(deficit_mm=wb["summary"]["total_deficit_mm"], **pump_kwargs)
        pumping_baseline = irrigation_pumping(
            deficit_mm=wb_baseline["summary"]["total_deficit_mm"], **pump_kwargs
        )
        extra_pumping_gwh = pumping_scenario["pumping_energy_gwh"] - pumping_baseline["pumping_energy_gwh"]
    else:
        warnings.append(
            "Luas lahan irigasi tidak diketahui → coupling air→energi (pompa irigasi) tidak dihitung."
        )

    # ── Energy ───────────────────────────────────────────────────────────────
    electricity_history = call_tool("get_electricity_history", location_query=query)
    energy = call_tool(
        "project_energy_demand",
        location_query=query,
        scenario=energy_scenario,
        horizon=horizon,
        extra_demand_at_horizon_gwh=extra_pumping_gwh,
    )
    demand_2030 = energy["endpoints"]["demand_2030_gwh"] or energy["endpoints"]["demand_horizon_gwh"]
    grid_packet = resolve_packet("grid.emission_factor_kg_co2_per_kwh", loc)
    grid_factor = (float(grid_packet.value) if grid_packet
                   else float(get_default(GRID_EMISSION_FACTOR, loc.country_code)))
    emissions = call_tool(
        "estimate_emissions",
        demand_gwh=demand_2030,
        renewable_share=renewable_share,
        country_code=loc.country_code or "ID",
        grid_emission_factor=grid_factor,
    )

    # ── Food self-sufficiency (same population pathway as energy) ────────────
    food_ssl = None
    if crop.get("available"):
        food_ssl = call_tool(
            "compute_food_ssl",
            production_t=crop["endpoints"]["production_2030_t"] or crop["endpoints"]["production_horizon_t"],
            location_query=query,
            year=2030,
            pop_growth_pct=ENERGY_SCENARIOS[energy_scenario]["pop_growth_pct"],
        )

    coupling = {
        "water_stress_raw": raw_stress,
        "irrigation_supply_fraction": supply_fraction,
        "water_stress_effective": effective_stress,
        "irrigated_physical_area_ha": physical_area_ha,
        "pumping_scenario": pumping_scenario,
        "pumping_baseline_climate": pumping_baseline,
        "extra_pumping_demand_gwh": extra_pumping_gwh,
        "power_sector_water_m3_2030": power_sector_water_m3(
            demand_2030, renewable_share,
            psw_cfg.get("fossil_m3_per_mwh", 2.6), psw_cfg.get("renewable_m3_per_mwh", 0.1),
        ),
        "parameters": {"irrigation": irr_cfg, "power_sector_water": psw_cfg},
    }

    provenance = []
    for payload in (electricity_history, energy, crop, food_ssl or {}):
        provenance.extend(payload.get("provenance", []))
    if grid_packet is not None:
        provenance.append(grid_packet.to_dict())

    state = NexusState(
        scenario_name=scenario.get("name", "UNNAMED"),
        location=loc.to_dict(),
        location_context={
            "display": loc.display,
            "has_local_data": loc.has_local_data,
            "sub_das": loc.metadata.get("sub_das", []),
            "fires": loc.metadata.get("fires", []),
        },
        climate_summary=climate,
        water_balance=wb,
        water_balance_baseline=wb_baseline,
        irrigation=irrigation,
        coupling=coupling,
        electricity_history=electricity_history,
        energy_projection=energy,
        emissions=emissions,
        food_history=food_history,
        crop_projection=crop,
        food_ssl=food_ssl,
        provenance=_dedupe(provenance),
        warnings=warnings,
    )
    state.checks = run_checks(state, cfg.get("checks") or {})
    return state


def _dedupe(packets: list[dict]) -> list[dict]:
    seen, out = set(), []
    for p in packets:
        key = (p.get("variable"), p.get("source"))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def run_checks(state: NexusState, cfg: dict) -> list[dict]:
    """Screening checks the critic must address. Deterministic, no LLM."""
    checks = []
    wb = state.water_balance["summary"]

    residual = wb["mass_balance_residual_mm"]
    checks.append(_check(
        "water_mass_balance",
        OK if abs(residual) < 0.5 else FAIL,
        f"P − ETa − surplus − ΔS = {residual:.3f} mm",
    ))

    monthly = state.water_balance["monthly"]
    wet = [m["month"] for m in monthly if m["surplus_mm"] > 0]
    dry = [m["month"] for m in monthly if m["deficit_mm"] > 0]
    if dry and wet:
        checks.append(_check(
            "seasonal_mismatch", WARN,
            f"Surplus tahunan {wb['total_surplus_mm']:.0f} mm terjadi di bulan {wet}, defisit "
            f"{wb['total_deficit_mm']:.0f} mm di bulan {dry}: surplus tahunan tidak menutup "
            "defisit musim kering tanpa tampungan atau air tanah.",
        ))
    elif dry:
        checks.append(_check("seasonal_mismatch", WARN,
                             f"Defisit {wb['total_deficit_mm']:.0f} mm tanpa surplus sama sekali."))
    else:
        checks.append(_check("seasonal_mismatch", OK, "Tidak ada bulan defisit."))

    pump = state.coupling.get("pumping_scenario")
    if pump:
        surplus = wb["total_surplus_mm"]
        gw = pump["groundwater_mm"]
        frac = cfg.get("groundwater_warn_fraction_of_surplus", 0.25)
        if gw > surplus:
            status = FAIL
        elif gw > frac * surplus:
            status = WARN
        else:
            status = OK
        checks.append(_check(
            "groundwater_vs_recharge_proxy", status,
            f"Air tanah dipompa {gw:.0f} mm/tahun di lahan irigasi vs surplus (proxy recharge "
            f"maksimum) {surplus:.0f} mm; ambang peringatan {frac:.0%}.",
        ))

    energy_pop = state.energy_projection["assumptions"].get("base_population")
    if state.food_ssl:
        food_pop = state.food_ssl["population_base"]
        same = energy_pop and abs(energy_pop - food_pop) / energy_pop < 0.01
        checks.append(_check(
            "population_consistency", OK if same else FAIL,
            f"Populasi dasar sektor energi {energy_pop:,} vs pangan {food_pop:,}.",
        ))

    crop = state.crop_projection
    if crop.get("available") and crop.get("observed_yield_t_ha"):
        modelled = crop["endpoints"]["yield_t_ha"]
        observed = crop["observed_yield_t_ha"]
        tol = cfg.get("yield_plausibility_tolerance", 0.25)
        rel = abs(modelled - observed) / observed
        checks.append(_check(
            "yield_plausibility", OK if rel <= tol else WARN,
            f"Yield model {modelled:.2f} t/ha vs observasi {observed:.2f} t/ha (selisih {rel:.0%}).",
        ))
    if not crop.get("available"):
        checks.append(_check("food_data_available", WARN, crop.get("reason", "")))

    threshold = cfg.get("low_confidence_threshold", 0.6)
    low = [f"{p['variable']} ({p['source']}, conf {p['confidence']})"
           for p in state.provenance if p.get("confidence", 1.0) < threshold]
    checks.append(_check(
        "low_confidence_inputs", WARN if low else OK,
        "; ".join(low) if low else f"Semua input ≥ confidence {threshold}.",
    ))

    missing = [k for k, v in state.energy_projection["endpoints"].items()
               if v is None and k in ("demand_2030_gwh", "demand_horizon_gwh")]
    if missing:
        checks.append(_check("horizon_endpoints", WARN, f"Endpoint kosong: {missing}"))
    return checks
