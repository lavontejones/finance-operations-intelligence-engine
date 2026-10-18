"""Read once, hash exact input bytes, and validate signed-off source controls."""
import csv
import hashlib
import io
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from .controls import categorize, reconcile
from .forecasting import ar_aging
from .models import Transaction
from .money import money
from .reviewed_batch import digest


def read_bytes(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Regular non-symlink source required")
    raw=path.read_bytes()
    if len(raw)>2_000_000:
        raise ValueError("Source exceeds 2 MB")
    return raw,{"filename":path.name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}


def read_json_snapshot(path):
    raw,info=read_bytes(path)
    return json.loads(raw.decode("utf-8-sig")),info


def read_csv_snapshot(path,required):
    raw,info=read_bytes(path)
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig"),newline=""))
    fields=reader.fieldnames or []
    if len(fields)!=len(set(fields)) or not required <= set(fields):
        raise ValueError("Missing or repeated source columns")
    rows=list(reader)
    if not rows or len(rows)>10000 or any(None in r or any(v is None for v in r.values()) for r in rows):
        raise ValueError("Empty, excessive or malformed source rows")
    info["row_count"]=len(rows)
    return rows,info


def finance_payload(bank_path,ledger_path,invoices_path,config_path,controls_path,as_of):
    config,ci=read_json_snapshot(config_path)
    controls,ki=read_json_snapshot(controls_path)
    if not isinstance(config,dict) or set(config)!={"version","data_classification","approved_by","approved_at","account_map"}:
        raise ValueError("Unsupported finance configuration")
    if not isinstance(config["version"],str) or not config["version"].strip() or config["data_classification"] not in {"synthetic","private"}:
        raise ValueError("Version and explicit data classification required")
    if not isinstance(config["approved_by"],str) or not config["approved_by"].strip() or datetime.fromisoformat(config["approved_at"]).tzinfo is None:
        raise ValueError("Mapping reviewer and aware timestamp required")
    if not isinstance(config["account_map"],dict) or set(config["account_map"])!={"bank","ledger"} or any(not isinstance(v,dict) for v in config["account_map"].values()):
        raise ValueError("Both source account maps required")
    if controls.get("configuration_digest")!=digest(config) or not controls.get("reviewed_by","").strip():
        raise ValueError("Source controls must bind to the approved configuration")
    if datetime.fromisoformat(controls["reviewed_at"]).tzinfo is None:
        raise ValueError("Aware source-control review timestamp required")
    required={"transaction_id","posted_on","source","description","amount","account","reference","currency"}
    sources,metadata={},{}
    for source,path in (("bank",bank_path),("ledger",ledger_path)):
        rows,info=read_csv_snapshot(path,required)
        expected=controls[source]
        total=sum((money(r["amount"]) for r in rows),Decimal("0.00"))
        if type(expected["row_count"]) is not int or expected["row_count"]!=len(rows) or money(expected["signed_total"])!=total:
            raise ValueError("Transaction source controls differ")
        transactions=[]
        for index,r in enumerate(rows,2):
            if r["currency"]!="USD" or r["source"]!=source:
                raise ValueError("USD and correct feed identity required")
            account=config["account_map"][source].get(r["account"])
            if not isinstance(account,str) or not account.strip():
                raise ValueError("Account absent from approved mapping")
            transactions.append(Transaction(r["transaction_id"],date.fromisoformat(r["posted_on"]),source,r["description"],r["amount"],account,r["reference"]))
        info["signed_total"]=str(total)
        sources[source]=(rows,transactions)
        metadata[source]=info
    invoices,info=read_csv_snapshot(invoices_path,{"invoice_id","due_date","open_amount","currency"})
    if len({r["invoice_id"] for r in invoices})!=len(invoices) or any(not r["invoice_id"].strip() or r["currency"]!="USD" for r in invoices):
        raise ValueError("Unique invoice IDs and USD required")
    total=sum((money(r["open_amount"]) for r in invoices),Decimal("0.00"))
    if controls["invoices"]["row_count"]!=len(invoices) or money(controls["invoices"]["open_total"])!=total:
        raise ValueError("AR source controls differ")
    info["open_total"]=str(total);metadata["invoices"]=info
    bank,ledger=sources["bank"][1],sources["ledger"][1]
    result=reconcile(bank,ledger)
    matches={r["bank_id"] for r in result["matched_pairs"]}
    context={"sources":metadata,"configuration":ci,"control_file":ki,"configuration_version":config["version"],"as_of":str(as_of)}
    run_id="FIN-"+digest(context)[:20]
    records=[]
    for line,tx in enumerate(bank,2):
        category,score=categorize(tx.description)
        blocks=[] if tx.transaction_id in matches else ["unreconciled"]
        if category=="Unclassified" or score<0.9: blocks.append("category_requires_source_correction")
        records.append({"record_id":tx.transaction_id,"run_id":run_id,"source_row":line,
                        "source_sha256":metadata["bank"]["sha256"],"configuration_digest":ci["sha256"],
                        "amount":str(tx.amount),"posted_on":str(tx.posted_on),"currency":"USD","account":tx.account,
                        "reference":tx.reference,"category_proposal":category,"category_score_is_probability":False,
                        "approval_required":True,"posting_permitted":False,"blocking_reasons":blocks})
    code_hash=hashlib.sha256()
    for p in sorted(Path(__file__).parent.glob("*.py")):
        code_hash.update(p.name.encode());code_hash.update(p.read_bytes())
    lineage={"schema_version":"finance-review-v2","run_id":run_id,"created_at":datetime.now(UTC).isoformat(),
             **context,"configuration":config,"configuration_file":ci,"control_file":ki,"source_controls":controls,
             "code_sha256":code_hash.hexdigest(),"approval_trust_boundary":"authorized offline operator; reviewer strings are not authenticated signatures"}
    return {"records.json":records,"reconciliation.json":result,"ar-aging.json":ar_aging(invoices,as_of),
            "source-provenance.json":lineage}
