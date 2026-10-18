from .money import money


def budget_variance(actual: dict[str, float], budget: dict[str, float]) -> list[dict]:
    names = sorted(set(actual) | set(budget))
    return [{"account": name, "actual": actual.get(name, 0), "budget": budget.get(name, 0),
             "variance": money(actual.get(name, 0)) - money(budget.get(name, 0))} for name in names]


def kpis(revenue: float, gross_profit: float, ar: float, cash: float, current_liabilities: float, revenue_period_days: int = 30) -> dict:
    if type(revenue_period_days) is not int or revenue_period_days <= 0:
        raise ValueError("Positive revenue coverage days required")
    revenue, gross_profit, ar, cash, current_liabilities = map(money, (revenue, gross_profit, ar, cash, current_liabilities))
    return {"gross_margin_pct": round(gross_profit / revenue * 100, 1) if revenue else 0,
            "days_sales_outstanding": round(ar / revenue * revenue_period_days, 1) if revenue else 0,
            "cash_ratio": round(cash / current_liabilities, 2) if current_liabilities else 0}


def management_package(kpi_values: dict, cash_forecast: list[dict], reviews: list[dict]) -> dict:
    return {"title": "Northstar Build & Fabrication | Synthetic CFO Package",
            "kpis": kpi_values, "week_13_cash": cash_forecast[-1]["ending_cash"],
            "open_control_items": len(reviews),
            "note": "Illustrative information only. Not a financial statement."}

