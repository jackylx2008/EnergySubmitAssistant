"""读取能源基础信息工作簿并转换为前端使用的结构化记录。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook


SHEETS = {
    "2026": "2026年会投能源用量基础信息表",
    "2025": "2025年会投能源用量基础信息",
}


def load_energy_records(path: Path) -> dict[str, list[dict[str, Any]]]:
    """读取目标工作表，按表头名称提取字段。"""
    if not path.is_file():
        raise FileNotFoundError(f"找不到输入工作簿：{path}")

    workbook = load_workbook(path, read_only=True, data_only=True)
    result: dict[str, list[dict[str, Any]]] = {}
    try:
        for year, sheet_name in SHEETS.items():
            if sheet_name not in workbook.sheetnames:
                raise ValueError(f"工作簿缺少工作表：{sheet_name}")
            sheet = workbook[sheet_name]
            rows = sheet.iter_rows(values_only=True)
            headers = [str(value).strip() if value is not None else "" for value in next(rows, ())]
            records: list[dict[str, Any]] = []
            for row_number, values in enumerate(rows, start=2):
                row = {headers[index]: values[index] if index < len(values) else None
                       for index in range(len(headers)) if headers[index]}
                # 跳过分组汇总或空白行，保留真实的零值明细。
                if not row.get("能源类型") or not row.get("月份"):
                    continue
                row["_row"] = row_number
                records.append(row)
            result[year] = records
    finally:
        workbook.close()
    return result
