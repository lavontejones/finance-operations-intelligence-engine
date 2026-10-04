import csv
from datetime import date
from pathlib import Path
from .controls import categorize, find_anomalies, find_duplicates, reconcile
from .forecasting import ar_aging, thirteen_week_cash, rolling_twelve_month
from .models import AuditEvent, Transaction
from .reporting import budget_variance, kpis, management_package

ROOT = Path(__file__).resolve().parents[2]


def read_transactions(filename: str) -> list[Transaction]:
    with (ROOT / "data" / "raw" / filename).open(newline="") as handle:
        return [Transaction(row["transaction_id"], date.fromisoformat(row["posted_on"]), row["source"],
                row["description"], float(row["amount"]), row["account"], row["reference"])
                for row in csv.DictReader(handle)]


def read_invoices() -> list[dict]:
    with (ROOT / "data" / "raw" / "invoices.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


def source_inventory() -> dict[str, int]:
    """Show each synthetic intake feed included in the demonstration."""
    counts = {}
    for filename in ("bank_transactions.csv", "ledger_transactions.csv", "invoices.csv", "payroll.csv", "recurring_expenses.csv"):
        with (ROOT / "data" / "raw" / filename).open(newline="") as handle:
            counts[filename.removesuffix(".csv")] = sum(1 for _ in csv.DictReader(handle))
    return counts


def build_demo() -> dict:
    bank = read_transactions("bank_transactions.csv")
    ledger = read_transactions("ledger_transactions.csv")
    reviews = find_duplicates(bank) + find_anomalies(bank)
    classified = [{"transaction_id": tx.transaction_id, "category": categorize(tx.description)[0],
                   "confidence": categorize(tx.description)[1]} for tx in bank]
    for item in reviews:
        classified.append({"transaction_id": item.transaction_id, "category": item.reason,
                           "confidence": item.confidence, "review_status": item.status})
    cash = thirteen_week_cash(1_250_000, [480000] * 13, [430000, 440000, 445000, 450000, 460000, 455000, 465000, 470000, 460000, 475000, 480000, 470000, 490000])
    months = rolling_twelve_month([2100000] * 12, [1760000] * 12)
    ar = ar_aging(read_invoices(), date(2026, 4, 30))
    variance = budget_variance({"Materials": 680000, "Payroll": 430000, "Vehicle and Fuel": 64000}, {"Materials": 650000, "Payroll": 440000, "Vehicle and Fuel": 60000})
    metric = kpis(2_100_000, 340_000, sum(ar.values()), cash[0]["ending_cash"], 850_000)
    audit = [AuditEvent("audit-001", "2026-04-30T09:00:00Z", "demo.pipeline", "ingested", tx.transaction_id, tx.source).as_dict() for tx in bank]
    return {"company": "Northstar Build & Fabrication LLC (fictional)", "source_inventory": source_inventory(), "reconciliation": reconcile(bank, ledger),
            "classification_results": classified, "approval_queue": [x.as_dict() for x in reviews],
            "ar_aging": ar, "cash_forecast": cash, "rolling_forecast": months,
            "budget_variance": variance, "kpis": metric, "audit_trail": audit,
            "management_package": management_package(metric, cash, [x.as_dict() for x in reviews]),
            "close_checklist": [{"task": "Reconcile bank and card accounts", "owner": "Controller", "status": "in_progress"}, {"task": "Review AR aging", "owner": "AR Lead", "status": "open"}, {"task": "Review capex and debt schedules", "owner": "FP&A", "status": "open"}]}
