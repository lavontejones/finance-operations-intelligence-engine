import json
from datetime import date

import pytest

from foie.provenance import finance_payload
from foie.reviewed_batch import digest, verify_run, write_run


def inputs(tmp_path):
    config={"version":"synthetic-v1","data_classification":"synthetic","approved_by":"Synthetic Reviewer",
       "approved_at":"2026-10-14T15:00:00+00:00","account_map":{"bank":{"Bank 1":"cash-1"},"ledger":{"Operating Bank":"cash-1"}}}
    controls={"configuration_digest":digest(config),"reviewed_by":"Synthetic Reviewer","reviewed_at":"2026-10-14T15:00:00+00:00",
       "bank":{"row_count":2,"signed_total":"-30.00"},"ledger":{"row_count":1,"signed_total":"-10.00"},"invoices":{"row_count":1,"open_total":"108.00"}}
    files={"bank":"transaction_id,posted_on,source,description,amount,account,reference,currency\nB1,2026-10-01,bank,fuel,-10.00,Bank 1,R1,USD\nB2,2026-10-01,bank,fuel,-20.00,Bank 1,R2,USD\n",
       "ledger":"transaction_id,posted_on,source,description,amount,account,reference,currency\nL1,2026-10-01,ledger,fuel,-10.00,Operating Bank,R1,USD\n",
       "invoices":"invoice_id,due_date,open_amount,currency\nI1,2026-10-01,108.00,USD\n"}
    for k,v in files.items():(tmp_path/(k+".csv")).write_text(v)
    (tmp_path/"config.json").write_text(json.dumps(config));(tmp_path/"controls.json").write_text(json.dumps(controls))
    return config,controls

def run(tmp_path):
    return finance_payload(*(tmp_path/n for n in ("bank.csv","ledger.csv","invoices.csv","config.json","controls.json")),date(2026,10,14))

def test_source_hashes_row_lineage_and_same_run_after_relocation(tmp_path):
    import shutil
    inputs(tmp_path);result=run(tmp_path)
    assert result["reconciliation.json"]["matched"]==1
    row=result["records.json"][0]
    assert row["source_row"]==2 and row["source_sha256"]
    assert result["source-provenance.json"]["configuration_version"]=="synthetic-v1"
    dst=tmp_path/"restored";dst.mkdir()
    for p in tmp_path.glob("*.csv"):shutil.copy2(p,dst/p.name)
    for p in tmp_path.glob("*.json"):shutil.copy2(p,dst/p.name)
    restored=run(dst)
    assert restored["records.json"]==result["records.json"]
    assert restored["source-provenance.json"]["run_id"]==result["source-provenance.json"]["run_id"]

@pytest.mark.parametrize("change",["wrong_total","wrong_count","missing_account","stale_config","repeated_header","wrong_feed","credit","subcent"])
def test_source_control_failures_stop_intake(tmp_path,change):
    config,controls=inputs(tmp_path)
    if change=="wrong_total":controls["bank"]["signed_total"]="0.00"
    if change=="wrong_count":controls["bank"]["row_count"]=3
    if change=="missing_account":config["account_map"]["bank"]={}
    if change=="stale_config":config["version"]="new"
    if change in {"missing_account","stale_config"}:(tmp_path/"config.json").write_text(json.dumps(config))
    if change=="repeated_header":
        p=tmp_path/"bank.csv";p.write_text(p.read_text().replace("currency\n","currency,currency\n",1))
    if change=="wrong_feed":
        p=tmp_path/"bank.csv";p.write_text(p.read_text().replace(",bank,",",ledger,"))
    if change=="credit":
        p=tmp_path/"invoices.csv";p.write_text(p.read_text().replace("108.00","-108.00"));controls["invoices"]["open_total"]="-108.00"
    if change=="subcent":
        p=tmp_path/"bank.csv";p.write_text(p.read_text().replace("-10.00","-10.001"))
    (tmp_path/"controls.json").write_text(json.dumps(controls))
    with pytest.raises(ValueError):run(tmp_path)

def test_verified_run_rejects_tampering_and_unknown_files(tmp_path):
    inputs(tmp_path);result=run(tmp_path);write_run(tmp_path/"run",result)
    assert verify_run(tmp_path/"run")["files"]
    p=tmp_path/"run"/"records.json";p.write_text("[]")
    with pytest.raises(ValueError):verify_run(tmp_path/"run")

def test_manifest_cannot_be_supplied_as_payload(tmp_path):
    with pytest.raises(ValueError):write_run(tmp_path/"run",{"manifest.json":{}})
