"""Location abstraction — universal kontainer untuk titik geografis."""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Location:
    """Lokasi yang bisa diproses agen — Sleman preset atau custom city apapun."""

    name: str
    lat: float
    lon: float
    country: str = ""
    country_code: str = ""
    admin1: str = ""           # provinsi/state
    admin2: str = ""           # kabupaten/county
    population: int | None = None
    timezone: str = "UTC"
    elevation_m: float | None = None
    source: str = "manual"     # "preset" | "geocoded" | "manual"
    metadata: dict = field(default_factory=dict)

    @property
    def slug(self) -> str:
        """Filesystem-safe slug untuk caching."""
        slug = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        return f"{slug}_{self.lat:.3f}_{self.lon:.3f}"

    @property
    def is_indonesia(self) -> bool:
        return self.country_code.upper() in {"ID", "IDN"}

    @property
    def display(self) -> str:
        parts = [self.name]
        if self.admin1 and self.admin1 != self.name:
            parts.append(self.admin1)
        if self.country and self.country != self.name:
            parts.append(self.country)
        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "country": self.country,
            "country_code": self.country_code,
            "admin1": self.admin1,
            "admin2": self.admin2,
            "population": self.population,
            "timezone": self.timezone,
            "elevation_m": self.elevation_m,
            "source": self.source,
        }
