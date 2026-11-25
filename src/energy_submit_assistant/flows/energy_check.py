"""能源用量校核工作流。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from energy_submit_assistant.modules.validator import validate_record
from energy_submit_assistant.modules.workbook_reader import load_energy_records


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def run_check(workbook_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    raw_by_year = load_energy_records(workbook_path)
    return {
        "tolerance_relative": config["app"].get("tolerance_relative", 0.01),
        "sheets": {
            year: [validate_record(row, config) for row in rows]
            for year, rows in raw_by_year.items()
        },
    }
