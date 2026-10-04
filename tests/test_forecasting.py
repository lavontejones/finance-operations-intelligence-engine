import pytest

from foie.forecasting import thirteen_week_cash
from foie.pipeline import build_demo


def test_cash_forecast_has_thirteen_weeks():
    rows = thirteen_week_cash(100, [10] * 13, [5] * 13)
    assert len(rows) == 13
    assert rows[-1]["ending_cash"] == 165


def test_cash_forecast_rejects_wrong_period_count():
    with pytest.raises(ValueError):
        thirteen_week_cash(100, [10], [5])


def test_demo_has_lineage_and_review_queue():
    demo = build_demo()
    assert demo["audit_trail"]
    assert demo["approval_queue"]
