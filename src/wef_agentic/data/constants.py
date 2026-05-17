"""Sleman geography & static parameters."""
from __future__ import annotations

# Kabupaten Sleman, D.I. Yogyakarta
# Sumber: BIG / GADM
SLEMAN_BBOX = {
    "lat_min": -7.92,
    "lat_max": -7.55,
    "lon_min": 110.20,
    "lon_max": 110.50,
}

SLEMAN_CENTROID = {"lat": -7.73, "lon": 110.36}  # approx

# Stasiun virtual (representatif) untuk Open-Meteo query
# Pilih 3 titik: Pakem (utara, dekat Merapi), Mlati (tengah), Prambanan (timur-selatan)
SLEMAN_STATIONS = [
    {"name": "Pakem", "lat": -7.66, "lon": 110.42, "zone": "Utara (Merapi slope)"},
    {"name": "Mlati", "lat": -7.74, "lon": 110.34, "zone": "Tengah (urban-irrigation)"},
    {"name": "Prambanan", "lat": -7.75, "lon": 110.49, "zone": "Timur-Selatan (rice belt)"},
]

# Sub-DAS yang melewati Sleman (cek HydroSHEDS untuk koordinat presisi)
SLEMAN_SUB_DAS = ["Code", "Opak", "Kuning", "Boyong"]

# Komoditas dominan
SLEMAN_CROPS = ["padi", "jagung"]

# Default historical date range untuk Open-Meteo
DEFAULT_START = "1991-01-01"
DEFAULT_END = "2024-12-31"
