"""Base DataSource abstraction + DataPacket dengan provenance lengkap."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar

from wef_agentic.geo.location import Location


@dataclass
class DataPacket:
    """Satu nilai variable dengan provenance lengkap untuk audit."""

    variable: str                       # mis. "climate.precip_mm_annual"
    value: Any                          # number, list, dict — tergantung variable
    location: dict                      # location.to_dict()
    source: str                         # mis. "open-meteo-historical"
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    year: int | None = None             # tahun referensi data (jika applicable)
    unit: str = ""                      # mis. "mm/year"
    confidence: float = 1.0             # 0-1, semakin tinggi semakin authoritative
    tier: int = 1                       # 1=primary, 2=secondary, 3=manual/proxy
    note: str = ""                      # caveat atau catatan tambahan
    raw: dict = field(default_factory=dict)  # untuk audit lengkap

    def to_dict(self) -> dict:
        return {
            "variable": self.variable,
            "value": self.value,
            "location": self.location,
            "source": self.source,
            "fetched_at": self.fetched_at.isoformat() if isinstance(self.fetched_at, datetime) else self.fetched_at,
            "year": self.year,
            "unit": self.unit,
            "confidence": self.confidence,
            "tier": self.tier,
            "note": self.note,
        }


class DataSourceUnavailable(Exception):  # noqa: N818
    """Raised saat source tidak bisa serve variable untuk location ini."""


class DataSource(ABC):
    """Base class untuk semua data sources.

    Setiap source declare:
    - name: identifier unique
    - tier: 1 (primary, authoritative), 2 (secondary, less authoritative), 3 (manual/proxy)
    - supported_variables: set of variable names yang bisa di-serve
    - supported_regions: filter geografis (e.g. only Indonesia)
    """

    name: ClassVar[str] = "abstract"
    tier: ClassVar[int] = 3
    supported_variables: ClassVar[set[str]] = set()
    supported_regions: ClassVar[set[str] | None] = None   # None = global

    def supports(self, variable: str, location: Location) -> bool:
        """Apakah source ini bisa serve variable untuk location ini?"""
        if variable not in self.supported_variables:
            return False
        if self.supported_regions and location.country_code.upper() not in self.supported_regions:
            return False
        return True

    @abstractmethod
    def fetch(self, variable: str, location: Location) -> DataPacket:
        """Sync fetch — raise DataSourceUnavailable jika gagal."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} tier={self.tier}>"
