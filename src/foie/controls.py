"""Deterministic control rules. Output is proposed work, never a ledger posting."""
from collections import defaultdict
from .models import ReviewItem, Transaction


def confidence_action(confidence: float) -> str:
    if confidence >= 0.90:
        return "propose_controlled_result"
    if confidence >= 0.60:
        return "human_review"
    return "investigate"


def find_duplicates(transactions: list[Transaction]) -> list[ReviewItem]:
    seen: dict[tuple, Transaction] = {}
    items = []
    for tx in transactions:
        key = (tx.posted_on, round(tx.amount, 2), tx.reference or tx.description)
        if key in seen:
            items.append(ReviewItem(f"dup-{tx.transaction_id}", tx.transaction_id,
                         f"Matches {seen[key].transaction_id} on date, amount, and reference",
                         0.98, "human_review", tx.source))
        else:
            seen[key] = tx
    return items


def find_anomalies(transactions: list[Transaction]) -> list[ReviewItem]:
    by_account: dict[str, list[float]] = defaultdict(list)
    for tx in transactions:
        by_account[tx.account].append(abs(tx.amount))
    items = []
    for tx in transactions:
        values = [abs(peer.amount) for peer in transactions
                  if peer.account == tx.account and peer.transaction_id != tx.transaction_id]
        if not values:
            continue
        baseline = sum(values) / len(values)
        if abs(tx.amount) > baseline * 2.5:
            items.append(ReviewItem(f"anomaly-{tx.transaction_id}", tx.transaction_id,
                         "Amount exceeds 2.5 times the account average", 0.55,
                         "investigate", tx.source))
    return items


def reconcile(bank: list[Transaction], ledger: list[Transaction]) -> dict:
    ledger_keys = {(x.posted_on, round(x.amount, 2), x.reference) for x in ledger}
    unmatched = [x.transaction_id for x in bank if (x.posted_on, round(x.amount, 2), x.reference) not in ledger_keys]
    return {"bank_records": len(bank), "ledger_records": len(ledger), "unmatched_bank_records": unmatched,
            "matched": len(bank) - len(unmatched)}


def categorize(description: str) -> tuple[str, float]:
    text = description.lower()
    rules = [("payroll", "Payroll", 0.99), ("steel", "Materials", 0.96),
             ("fuel", "Vehicle and Fuel", 0.94), ("customer payment", "Accounts Receivable", 0.98),
             ("loan", "Debt Service", 0.97), ("transfer", "Internal Allocation", 0.72)]
    for token, category, confidence in rules:
        if token in text:
            return category, confidence
    return "Unclassified", 0.30
