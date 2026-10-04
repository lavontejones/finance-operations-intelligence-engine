from datetime import date

from foie.controls import confidence_action, find_duplicates, reconcile
from foie.models import Transaction


def transaction(identifier, amount, reference):
    return Transaction(identifier, date(2026, 1, 1), "bank", "fuel", amount, "fuel", reference)


def test_duplicate_detection():
    assert len(find_duplicates([transaction("a", -25, "x"), transaction("b", -25, "x")])) == 1


def test_confidence_policy():
    assert confidence_action(0.90) == "propose_controlled_result"
    assert confidence_action(0.60) == "human_review"
    assert confidence_action(0.59) == "investigate"


def test_reconciliation_shows_unmatched_items():
    result = reconcile([transaction("a", -25, "x")], [])
    assert result["unmatched_bank_records"] == ["a"]
