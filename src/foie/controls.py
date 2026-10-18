"""Deterministic control rules. Output is proposed work, never a ledger posting."""
from collections import defaultdict
from decimal import Decimal

from .models import ReviewItem, Transaction
from .money import money


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
        key = (tx.account, tx.posted_on, money(tx.amount), tx.reference.strip() or tx.description.strip())
        if key in seen:
            items.append(ReviewItem(f"dup-{tx.transaction_id}", tx.transaction_id,
                         f"Matches {seen[key].transaction_id} on date, amount, and reference",
                         0.98, "human_review", tx.source))
        else:
            seen[key] = tx
    return items


def find_anomalies(transactions: list[Transaction]) -> list[ReviewItem]:
    by_account: dict[str, list[Decimal]] = defaultdict(list)
    for tx in transactions:
        by_account[tx.account].append(abs(tx.amount))
    items = []
    for tx in transactions:
        values = [abs(peer.amount) for peer in transactions
                  if peer.account == tx.account and peer.transaction_id != tx.transaction_id]
        if not values:
            continue
        baseline = sum(values) / len(values)
        if abs(tx.amount) > baseline * Decimal("2.5"):
            items.append(ReviewItem(f"anomaly-{tx.transaction_id}", tx.transaction_id,
                         "Amount exceeds 2.5 times the account average", 0.55,
                         "investigate", tx.source))
    return items


def reconcile(bank: list[Transaction], ledger: list[Transaction]) -> dict:
    """Exact one-to-one, same-account linkage; blank references never auto-match."""
    for records in (bank, ledger):
        if len({x.transaction_id for x in records}) != len(records):
            raise ValueError("Duplicate transaction IDs")
    def key(x):
        return (x.account.strip(), x.posted_on, money(x.amount), x.reference.strip())
    bkeys, lkeys = defaultdict(list), defaultdict(list)
    for x in bank: bkeys[key(x)].append(x)
    for x in ledger: lkeys[key(x)].append(x)
    matched, ambiguous = [], []
    for k, rows in bkeys.items():
        peers = lkeys.get(k, [])
        if not k[-1]: continue
        if len(rows) == len(peers) == 1:
            matched.append({"bank_id": rows[0].transaction_id, "ledger_id": peers[0].transaction_id})
        elif peers:
            ambiguous.extend(x.transaction_id for x in rows)
    ids = {x["bank_id"] for x in matched}
    lids = {x["ledger_id"] for x in matched}
    return {"bank_records": len(bank), "ledger_records": len(ledger),
            "unmatched_bank_records": [x.transaction_id for x in bank if x.transaction_id not in ids],
            "unmatched_ledger_records": [x.transaction_id for x in ledger if x.transaction_id not in lids],
            "ambiguous_bank_records": ambiguous, "matched_pairs": matched, "matched": len(matched),
            "bank_control_total": str(sum((x.amount for x in bank), Decimal("0.00"))),
            "ledger_control_total": str(sum((x.amount for x in ledger), Decimal("0.00")))}


def categorize(description: str) -> tuple[str, float]:
    text = description.lower()
    rules = [("payroll", "Payroll", 0.99), ("steel", "Materials", 0.96),
             ("fuel", "Vehicle and Fuel", 0.94), ("customer payment", "Accounts Receivable", 0.98),
             ("loan", "Debt Service", 0.97), ("transfer", "Internal Allocation", 0.72)]
    for token, category, confidence in rules:
        if token in text:
            return category, confidence
    return "Unclassified", 0.30

