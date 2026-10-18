import json
from datetime import date
from decimal import Decimal

import pytest

from foie.assessment import assess
from foie.batch_cli import transactions
from foie.controls import find_duplicates, reconcile
from foie.documents import parse_invoice_text, process_folder, validate_documents
from foie.forecasting import ar_aging, thirteen_week_cash
from foie.models import Transaction
from foie.money import csv_cell, money
from foie.reporting import kpis
from foie.reviewed_batch import approved_export, digest, write_reviewed_csv, write_run


def tx(identifier="b",account="cash",reference="r",amount="0.30"):
    return Transaction(identifier,date(2026,1,1),"bank","fuel",amount,account,reference)

@pytest.mark.parametrize("value",["NaN","Infinity","bad","0.001","1000000000001"])
def test_money_rejects_invalid(value):
    with pytest.raises(ValueError): money(value)

def test_exact_decimal_and_cash_bridges():
    assert money("0.10")+money("0.20")==Decimal("0.30")
    cash=Decimal("0.10")
    for row in thirteen_week_cash(cash,["0.20"]*13,["0.10"]*13):
        assert row["ending_cash"]==cash+Decimal("0.10")
        assert row["opening_cash"]+row["inflows"]-row["outflows"]==row["ending_cash"]
        cash=row["ending_cash"]
    assert cash==Decimal("1.40")

def test_ambiguous_many_to_one_is_held():
    r=reconcile([tx("b1"),tx("b2")],[tx("l1")])
    assert r["matched"]==0
    assert r["ambiguous_bank_records"]==["b1","b2"]
    assert r["unmatched_ledger_records"]==["l1"]

def test_same_account_and_nonblank_reference_required():
    assert reconcile([tx()],[tx("l",account="other")])["matched"]==0
    assert reconcile([tx(reference="")],[tx("l",reference="")])["matched"]==0
    assert not find_duplicates([tx(),tx("x",account="other")])

def test_unique_pair_and_duplicate_ids():
    assert reconcile([tx()],[tx("l")])["matched_pairs"]==[{"bank_id":"b","ledger_id":"l"}]
    with pytest.raises(ValueError): reconcile([tx(),tx()],[])

def test_aging_boundaries_and_credits():
    rows=[{"due_date":"2026-01-01","open_amount":"0.10"},{"due_date":"2026-01-02","open_amount":"0.20"}]
    assert ar_aging(rows,date(2026,2,1))["31_60"]==Decimal("0.10")
    assert ar_aging(rows,date(2026,2,1))["1_30"]==Decimal("0.20")
    with pytest.raises(ValueError): ar_aging([{"due_date":"2026-01-01","open_amount":"-1"}],date(2026,2,1))

def invoice(**changes):
    return {"document_type":"invoice","document_id":"I1","vendor":"Synthetic Vendor","invoice_date":"2026-10-01",
            "currency":"USD","subtotal":"100.00","tax":"8.00","total":"108.00",**changes}

def decision(r,**changes):
    return {"record_id":r["record_id"],"record_digest":digest(r),"decision":"approve","reviewer":"Synthetic Reviewer",
            "reason":"Compared to fictional source","reviewed_at":"2026-10-14T14:00:00+00:00",**changes}

def test_duplicate_all_members_held_and_mismatch():
    rows=validate_documents([(invoice(),[]),(invoice(),[]),(invoice(document_id="I2",total="109"),[])])
    assert all(r["blocking_reasons"] for r in rows)
    with pytest.raises(ValueError): approved_export(rows,[decision(rows[0])])
    assert "total_mismatch" in rows[2]["blocking_reasons"]

@pytest.mark.parametrize("changes",[{"currency":"EUR"},{"total":"NaN"},{"invoice_date":"bad"},{"vendor":""},{"total":"0.001"},{"total":"-1"}])
def test_invalid_documents_blocked(changes):
    assert validate_documents([(invoice(**changes),[])])[0]["blocking_reasons"]

def test_bound_approval_and_output(tmp_path):
    rows=validate_documents([(invoice(),[])])
    d=decision(rows[0])
    approved=approved_export(rows,[d])
    assert len(approved)==1 and approved[0]["posting_permitted"] is False
    with pytest.raises(ValueError): approved_export(rows,[dict(d,record_digest="stale")])
    with pytest.raises(ValueError): approved_export(rows,[dict(d,reviewer="")])
    with pytest.raises(ValueError): approved_export(rows,[dict(d,reviewed_at="2026-10-14T14:00:00")])
    with pytest.raises(ValueError): approved_export(rows,[d,d])
    write_reviewed_csv(tmp_path/"reviewed.csv",approved)
    assert "False" in (tmp_path/"reviewed.csv").read_text()
    with pytest.raises(FileExistsError): write_reviewed_csv(tmp_path/"reviewed.csv",approved)
    write_run(tmp_path/"run",{"records.json":rows})
    assert json.loads((tmp_path/"run"/"manifest.json").read_text())["files"]
    with pytest.raises(FileExistsError): write_run(tmp_path/"run",{"records.json":rows})

def test_text_parser_limits_and_duplicate_labels(tmp_path):
    p=tmp_path/"invoice.txt"
    p.write_text("\n".join(k+": "+v for k,v in invoice().items()))
    rows=process_folder(tmp_path)
    assert not rows[0]["blocking_reasons"]
    p.write_text(p.read_text()+"\ntotal: 108.00")
    assert "repeated_field:total" in parse_invoice_text(p)[1]
    p.write_text("x"*65537)
    with pytest.raises(ValueError): parse_invoice_text(p)
    p.unlink()
    (tmp_path/"scan.pdf").write_text("unsupported")
    with pytest.raises(ValueError): process_folder(tmp_path)

def test_symlink_output_refused(tmp_path):
    (tmp_path/"link").symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(ValueError): write_run(tmp_path/"link"/"run",{"records.json":[]})

@pytest.mark.parametrize("text",["=CMD()"," +CMD()","@SUM(A1)","-CMD()","\t=CMD()"])
def test_csv_injection_escaped(text):
    assert csv_cell(text).startswith("'")

def finding(**changes):
    return {"finding_id":"F1","domain":"operations","severity":4,"confidence":"high","evidence":["synthetic time study"],
            "symptom":"rekey","root_cause":"duplicate fields","treatment":"field map","owner":"Synthetic Ops",
            "monthly_volume":"300","minutes_per_case":"8","loaded_hourly_cost":"35","realization_fraction":"0.5",**changes}

def test_assessment_evidence_gate_and_no_benefit_sum():
    r=assess([finding(),finding(finding_id="F2",evidence=[],confidence="low")])
    assert r["findings"][0]["annual_capacity_value_scenario"]=="8400.00"
    assert r["findings"][1]["decision"]=="validate_evidence_before_recommendation"
    assert r["readiness_certification"] is False
    with pytest.raises(ValueError): assess([finding(realization_fraction="1.1")])
    with pytest.raises(ValueError): assess([finding(),finding()])

def test_dso_uses_supplied_revenue_period():
    assert kpis(100,20,50,10,5,revenue_period_days=30)["days_sales_outstanding"]==15
    with pytest.raises(ValueError): kpis(100,20,50,10,5,revenue_period_days=0)

def test_client_file_requires_currency_and_rejects_nonusd(tmp_path):
    p=tmp_path/"bank.csv"
    p.write_text("transaction_id,posted_on,source,description,amount,account,reference,currency\nb,2026-01-01,bank,fuel,0.30,cash,r,USD\n")
    assert transactions(p)[0].amount==Decimal("0.30")
    p.write_text(p.read_text().replace("USD","EUR"))
    with pytest.raises(ValueError): transactions(p)
