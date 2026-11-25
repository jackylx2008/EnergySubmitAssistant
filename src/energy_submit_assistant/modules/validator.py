"""能源标准煤与二氧化碳计算及相对误差核对。"""

from __future__ import annotations

from typing import Any


def _number(value: Any) -> float | None:
    if value is None or value == "":
        # 原始工作簿中的空白按零参与计算和一致性比较。
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _check(calculated: float | None, reported: Any, tolerance: float) -> dict[str, Any]:
    actual = _number(reported)
    if calculated is None:
        return {"status": "unavailable", "relative_error": None, "reported": actual}
    if actual == 0:
        relative_error = 0.0 if calculated == 0 else None
        status = "一致" if calculated == 0 else "不一致"
        return {"status": status, "relative_error": relative_error, "reported": actual}
    relative_error = abs(calculated - actual) / abs(actual)
    return {
        "status": "一致" if relative_error <= tolerance else "不一致",
        "relative_error": relative_error,
        "reported": actual,
    }


def validate_record(record: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """使用实物量、能源规则和工作簿汇总值生成一条校核结果。"""
    calculation = config["calculation"]
    energy = str(record.get("能源类型") or "")
    category = energy.split("（", 1)[0].split("(", 1)[0].strip()
    factors = calculation["factors"].get(category)
    own_quantity = _number(record.get("自用实物量"))
    total_quantity = _number(record.get("总实物量"))
    excluded_coal = set(calculation.get("excluded_from_coal", []))
    excluded_co2 = set(calculation.get("excluded_from_co2", []))

    def calc(quantity: float | None, factor_name: str, excluded: set[str]) -> float | None:
        if category in excluded:
            return 0.0
        if quantity is None or factors is None or factor_name not in factors:
            return None
        return quantity * float(factors[factor_name])

    tolerance = float(config["app"].get("tolerance_relative", 0.01))
    coal_own = calc(own_quantity, "coal", excluded_coal)
    coal_total = calc(total_quantity, "coal", excluded_coal)
    co2_own = calc(own_quantity, "co2", excluded_co2)
    co2_total = calc(total_quantity, "co2", excluded_co2)
    return {
        **record,
        "_category": category,
        "_computed": {
            "coal_self": coal_own,
            "coal_total": coal_total,
            "co2_self": co2_own,
            "co2_total": co2_total,
        },
        "_checks": {
            "coal_self": _check(coal_own, record.get("自用综合能耗（标准煤）"), tolerance),
            "coal_total": _check(coal_total, record.get("总综合能耗（吨标煤）"), tolerance),
            "co2_self": _check(co2_own, record.get("自用二氧化碳排放量（吨二氧化碳）"), tolerance),
            "co2_total": _check(co2_total, record.get("总二氧化碳排放量（吨二氧化碳）"), tolerance),
        },
    }
