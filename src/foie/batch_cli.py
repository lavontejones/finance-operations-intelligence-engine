"""Offline client-file preflight and immutable outputs; no hosted service."""
import argparse
import csv
import json
from datetime import date
from pathlib import Path

from .assessment import assess
from .documents import process_folder
from .models import Transaction
from .provenance import finance_payload
from .reviewed_batch import approved_export, verify_run, write_run


def load_csv(path, required):
    path=Path(path)
    if path.is_symlink() or path.stat().st_size>2_000_000:
        raise ValueError("Provide regular CSV files under 2 MB")
    with path.open(newline="",encoding="utf-8-sig") as h:
        reader=csv.DictReader(h)
        if not required <= set(reader.fieldnames or []):
            raise ValueError("Required source columns missing")
        rows=list(reader)
    if len(rows)>10000:
        raise ValueError("10,000-row intake ceiling")
    return rows


def transactions(path):
    required={"transaction_id","posted_on","source","description","amount","account","reference","currency"}
    rows=load_csv(path,required)
    if any(r["currency"]!="USD" for r in rows):
        raise ValueError("Only approved USD mapping supported")
    return [Transaction(r["transaction_id"],date.fromisoformat(r["posted_on"]),r["source"],r["description"],
                        r["amount"],r["account"],r["reference"]) for r in rows]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    for cmd in ("assessment","documents","export"):
        a=sub.add_parser(cmd)
        a.add_argument("--input",type=Path,required=True)
        a.add_argument("--output",type=Path,required=True)
        if cmd=="export": a.add_argument("--decisions",type=Path,required=True)
    a=sub.add_parser("split-pdf")
    a.add_argument("--input",type=Path,required=True)
    a.add_argument("--plan",type=Path,required=True)
    a.add_argument("--output",type=Path,required=True)
    a=sub.add_parser("finance")
    for name in ("bank","ledger","invoices","output"):
        a.add_argument("--"+name,type=Path,required=True)
    a.add_argument("--as-of",type=date.fromisoformat,required=True)
    a.add_argument("--config",type=Path,required=True)
    a.add_argument("--controls",type=Path,required=True)
    args=p.parse_args()
    try:
        if args.command=="split-pdf":
            from .pdf_intake import split_packet
            split_packet(args.input,json.loads(args.plan.read_text()),args.output)
            print(json.dumps({"status":"complete","external_actions":0,"mode":"reviewer_defined_split"}))
            return
        if args.command=="assessment":
            output={"assessment.json":assess(json.loads(args.input.read_text()))}
        elif args.command=="documents":
            output={"records.json":process_folder(args.input)}
        elif args.command=="export":
            verify_run(args.input.parent)
            output={"approved-proposals.json":approved_export(json.loads(args.input.read_text()),json.loads(args.decisions.read_text()))}
        else:
            output=finance_payload(args.bank,args.ledger,args.invoices,args.config,args.controls,args.as_of)
        write_run(args.output,output)
        print(json.dumps({"status":"complete","external_actions":0,"output":str(args.output)}))
    except (ValueError,OSError,KeyError,TypeError) as error:
        p.exit(2,f"Preflight failed: {type(error).__name__}; inspect source contract locally.\n")

if __name__=="__main__": main()
