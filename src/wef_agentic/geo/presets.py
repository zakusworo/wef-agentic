"""Preset locations — sudah ada cache fixture untuk smoke test."""
from __future__ import annotations

from wef_agentic.geo.location import Location

# Sleman = case study utama, sudah di-cache via fixture
SLEMAN = Location(
    name="Sleman",
    lat=-7.73,
    lon=110.36,
    country="Indonesia",
    country_code="ID",
    admin1="D.I. Yogyakarta",
    admin2="Kabupaten Sleman",
    population=1142528,
    timezone="Asia/Jakarta",
    elevation_m=200.0,
    source="preset",
    metadata={
        "has_static_socioeconomic_data": True,  # BPS data tersedia
        "stations": [
            {"name": "Pakem", "lat": -7.66, "lon": 110.42, "zone": "Utara (Merapi slope)"},
            {"name": "Mlati", "lat": -7.74, "lon": 110.34, "zone": "Tengah (urban-irrigation)"},
            {"name": "Prambanan", "lat": -7.75, "lon": 110.49, "zone": "Timur-Selatan (rice belt)"},
        ],
        "sub_das": ["Code", "Opak", "Kuning", "Boyong"],
        "crops": ["padi", "jagung"],
        "fires": [
            "krisis air tanah Sleman Tengah-Selatan",
            "alih fungsi LP2B (~280 ha/tahun)",
            "beban grid pasca-subsidi listrik",
            "ancaman Merapi VEI 3+ recurrent",
            "tekanan hidrolik pariwisata Borobudur-Prambanan-Merapi",
        ],
    },
)


PRESETS: dict[str, Location] = {
    "sleman": SLEMAN,
}


def get_preset(key: str) -> Location | None:
    return PRESETS.get(key.lower())


def list_presets() -> list[Location]:
    return list(PRESETS.values())
