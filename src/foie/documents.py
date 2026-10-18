"""Narrow deterministic extraction of labeled UTF-8 invoice text.

Digital labeled PDF is optional. No OCR, arbitrary document understanding, or model calls.
"""
import re
from datetime import date
from pathlib import Path

from .money import money
from .reviewed_batch import digest

FIELDS = {"document_type", "document_id", "vendor", "invoice_date", "currency", "subtotal", "tax", "total"}


def parse_invoice_text(path):
    path = Path(path)
    if path.is_symlink() or path.suffix.lower() != ".txt" or path.stat().st_size > 65536:
        raise ValueError("Only regular UTF-8 TXT invoices up to 64 KiB")
    return parse_labeled_text(path.read_text(encoding="utf-8"))


def parse_labeled_text(text):
    data, errors = {}, []
    for line in text.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            errors.append("unsupported_line")
            continue
        key, value = line.split(":", 1)
        key = re.sub(r"\s+", "_", key.strip().lower())
        if key not in FIELDS:
            errors.append("unsupported_field")
        elif key in data:
            errors.append("repeated_field:"+key)
        else:
            data[key] = value.strip()
    return data, sorted(set(errors))


def validate_documents(items):
    """Validate extracted records; preserve bad rows as blocked review items."""
    out = []
    ids, keys = {}, {}
    for index, (data, parse_errors) in enumerate(items):
        reasons = list(parse_errors)
        for key in FIELDS:
            if not str(data.get(key, "")).strip():
                reasons.append("missing:"+key)
        if data.get("document_type") != "invoice":
            reasons.append("unsupported_document_type")
        if data.get("currency") != "USD":
            reasons.append("unsupported_currency")
        try:
            date.fromisoformat(data.get("invoice_date", ""))
        except ValueError:
            reasons.append("invalid_date")
        try:
            subtotal, tax, total = [money(data.get(k, "")) for k in ("subtotal","tax","total")]
            if min(subtotal, tax, total) < 0:
                reasons.append("credit_requires_separate_workflow")
            if subtotal + tax != total:
                reasons.append("total_mismatch")
            data = {**data, "subtotal": str(subtotal), "tax": str(tax), "total": str(total)}
        except ValueError:
            reasons.append("invalid_money")
        rid = f"DOC-{index+1:03d}"
        record = {"record_id": rid, **data, "blocking_reasons": sorted(set(reasons)),
                  "source_digest": digest(data), "category": "invoice_candidate",
                  "approval_required": True, "posting_permitted": False}
        out.append(record)
        content_key = digest(data)
        keys.setdefault(content_key, []).append(record)
        business_key = (str(data.get("vendor","")).strip().casefold(), str(data.get("document_id","")).strip().casefold())
        if all(business_key):
            ids.setdefault(business_key, []).append(record)
    # Block every member; never arbitrarily select a primary document.
    for groups, reason in ((keys,"duplicate_content"),(ids,"duplicate_business_key")):
        for group in groups.values():
            if len(group)>1:
                for r in group:
                    r["blocking_reasons"] = sorted(set(r["blocking_reasons"]+[reason]))
    return out


def process_folder(folder):
    folder = Path(folder)
    if folder.is_symlink():
        raise ValueError("Symlink intake refused")
    paths = sorted(folder.iterdir())
    if not paths or len(paths)>100:
        raise ValueError("Provide 1-100 labeled invoices")
    # Unsupported files reject the intake before any publication.
    if any(p.name=="FAILED" for p in paths):raise ValueError("Failed split run")
    split_manifest=folder/"split-manifest.json"
    if split_manifest.is_symlink():raise ValueError("Symlink split manifest")
    if split_manifest.exists():
        import hashlib
        import json
        manifest=json.loads(split_manifest.read_text())
        expected=manifest["files"]
        if {p.name for p in paths}!=set(expected)|{"split-manifest.json"}:
            raise ValueError("Unexpected split files")
        for name,sha in expected.items():
            if Path(name).name!=name or (folder/name).is_symlink() or hashlib.sha256((folder/name).read_bytes()).hexdigest()!=sha:
                raise ValueError("Split output integrity mismatch")
        paths=[p for p in paths if p.name!="split-manifest.json"]
    import hashlib
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    parsed=[]
    for p in paths:
        if p.suffix.lower()==".pdf":
            from .pdf_intake import extract_invoice_pdf
            parsed.append(extract_invoice_pdf(p))
        else:parsed.append(parse_invoice_text(p))
    if any(hashlib.sha256(p.read_bytes()).hexdigest()!=before[p.name] for p in paths):
        raise ValueError("Source changed during document extraction")
    result = validate_documents(parsed)
    for record, path in zip(result, paths):
        import hashlib
        record["source_file"] = path.name
        record["file_sha256"] = before[path.name]
    return result
