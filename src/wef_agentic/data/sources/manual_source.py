"""Manual override source — load JSON file dari user."""
from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from wef_agentic.config.settings import EXTERNAL_DIR
from wef_agentic.data.sources.base import DataPacket, DataSource, DataSourceUnavailable
from wef_agentic.geo.location import Location


class ManualOverrideSource(DataSource):
    """Load data dari file JSON user-provided.

    File location: data/external/override_<slug>.json
    Format per registry.manual_override_schema()
    """

    name = "manual-override"
    tier = 1   # treated as primary jika user provide (assumed accurate)
    supported_variables: ClassVar[set[str]] = set()  # dynamic — depends on file content

    def _file_path(self, location: Location) -> Path:
        return EXTERNAL_DIR / f"override_{location.slug}.json"

    def _load(self, location: Location) -> dict:
        path = self._file_path(location)
        if not path.exists():
            raise DataSourceUnavailable(f"No override file: {path.name}")
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            raise DataSourceUnavailable(f"Failed to parse {path.name}: {e}") from e

    def supports(self, variable: str, location: Location) -> bool:
        try:
            data = self._load(location)
        except DataSourceUnavailable:
            return False
        return variable in (data.get("variables") or {})

    def fetch(self, variable: str, location: Location) -> DataPacket:
        data = self._load(location)
        var_data = (data.get("variables") or {}).get(variable)
        if var_data is None:
            raise DataSourceUnavailable(f"Variable {variable} not in override file")

        return DataPacket(
            variable=variable,
            value=var_data.get("value"),
            location=location.to_dict(),
            source=f"manual:{var_data.get('source', 'user-provided')}",
            year=var_data.get("year"),
            unit=var_data.get("unit", ""),
            confidence=0.99,    # user-curated = highest confidence
            tier=1,
            note=var_data.get("note", "Manual override dari user JSON."),
        )
