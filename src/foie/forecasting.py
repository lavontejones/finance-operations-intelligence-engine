from datetime import date, timedelta


def thirteen_week_cash(opening_cash: float, weekly_inflows: list[float], weekly_outflows: list[float]) -> list[dict]:
    if len(weekly_inflows) != 13 or len(weekly_outflows) != 13:
        raise ValueError("Provide exactly 13 weekly inflow and outflow values")
    rows, cash = [], opening_cash
    start = date(2026, 1, 5)
    for index, (inflow, outflow) in enumerate(zip(weekly_inflows, weekly_outflows), start=1):
        cash += inflow - outflow
        rows.append({"week": index, "week_of": str(start + timedelta(days=(index - 1) * 7)),
                     "inflows": inflow, "outflows": outflow, "ending_cash": cash})
    return rows


def rolling_twelve_month(revenue: list[float], operating_cost: list[float]) -> list[dict]:
    if len(revenue) != 12 or len(operating_cost) != 12:
        raise ValueError("Provide exactly 12 months")
    return [{"month": index + 1, "revenue": r, "operating_cost": c, "ebitda": r - c}
            for index, (r, c) in enumerate(zip(revenue, operating_cost))]


def ar_aging(invoices: list[dict], as_of: date) -> dict[str, float]:
    buckets = {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "61_90": 0.0, "over_90": 0.0}
    for invoice in invoices:
        days = max((as_of - date.fromisoformat(invoice["due_date"])).days, 0)
        bucket = "current" if days == 0 else "1_30" if days <= 30 else "31_60" if days <= 60 else "61_90" if days <= 90 else "over_90"
        buckets[bucket] += float(invoice["open_amount"])
    return buckets
