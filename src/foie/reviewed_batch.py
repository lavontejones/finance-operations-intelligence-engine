"""Offline batch records and approvals. Filesystem operator is the trust boundary.

No credentials, network, ledger writes, or authenticated multi-user review service.
"""
import csv
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from .money import csv_cell


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def approved_export(records, decisions):
    by_id = {r["record_id"]: r for r in records}
    if len(by_id) != len(records):
        raise ValueError("Duplicate record IDs")
    result, seen = [], set()
    for d in decisions:
        rid = d["record_id"]
        if rid in seen or rid not in by_id:
            raise ValueError("Unknown or duplicate approval")
        seen.add(rid)
        record = by_id[rid]
        if d["record_digest"] != digest(record):
            raise ValueError("Stale approval")
        if d["decision"] not in {"approve", "reject", "defer"}:
            raise ValueError("Invalid decision")
        if not str(d["reviewer"]).strip() or not str(d["reason"]).strip():
            raise ValueError("Reviewer and reason required")
        if datetime.fromisoformat(d["reviewed_at"]).tzinfo is None:
            raise ValueError("Timezone-aware review timestamp required")
        if d["decision"] == "approve":
            if record["blocking_reasons"]:
                raise ValueError("Correct blocked source and rerun before approval")
            result.append({**record, "approval": dict(d), "posting_permitted": False})
    return result


def write_run(target, payload, *, reviewed_csv=None):
    """Publish complete immutable run; final-folder reservation uses exclusive mkdir.

    Hash manifest detects accidental edits; it is not a signed or tamper-proof log.
    """
    target = Path(target).absolute()
    for p in (target, *target.parents):
        if p.is_symlink():
            raise ValueError("Symlink output refused")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".batch-", dir=target.parent))
    os.chmod(stage, 0o700)
    reserved = False
    try:
        for name, value in payload.items():
            if Path(name).name != name or name == "manifest.json" or not name.endswith(".json"):
                raise ValueError("Safe JSON output filenames required")
            p = stage / name
            p.write_text(json.dumps(value, indent=2, sort_keys=True, default=str)+"\n")
            os.chmod(p, 0o600)
        if reviewed_csv is not None:
            write_reviewed_csv(stage / "reviewed-proposals.csv", reviewed_csv)
        files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.iterdir()}
        (stage / "manifest.json").write_text(json.dumps({"files": files, "mode": "offline_review_only"}, indent=2)+"\n")
        os.chmod(stage / "manifest.json", 0o600)
        target.mkdir(mode=0o700)  # atomic exclusive reservation; never replaces prior output
        reserved = True
        for p in sorted(stage.iterdir(), key=lambda p: p.name == "manifest.json"):
            os.rename(p, target / p.name)
    except Exception:
        # A partially published run has no complete manifest; never use it for export.
        if reserved and target.exists():
            (target / "FAILED").write_text("Publication failed; discard this new run after investigation.\n")
        raise
    finally:
        shutil.rmtree(stage)


def write_reviewed_csv(path, approved):
    """CSV is a reviewed proposal export, not an accounting-system import format."""
    path = Path(path)
    with path.open("x", newline="", encoding="utf-8") as h:
        os.chmod(path, 0o600)
        fields = ["record_id", "document_id", "vendor", "total", "currency", "reviewer", "posting_permitted"]
        writer = csv.DictWriter(h, fieldnames=fields)
        writer.writeheader()
        for r in approved:
            writer.writerow({k: csv_cell(r.get(k, r["approval"]["reviewer"] if k=="reviewer" else "")) for k in fields})


def verify_run(path):
    """Refuse interrupted, unexpected, symlinked or altered run evidence."""
    path=Path(path)
    if path.is_symlink() or (path/"FAILED").exists() or (path/"RUNNING").exists():
        raise ValueError("Incomplete or symlink run")
    for parent in path.parents:
        if parent.is_symlink():raise ValueError("Symlink run ancestor")
    if (path/"manifest.json").is_symlink():raise ValueError("Symlink manifest")
    manifest=json.loads((path/"manifest.json").read_text())
    files=manifest["files"]
    if not files or {p.name for p in path.iterdir()}!=set(files)|{"manifest.json"}:
        raise ValueError("Unexpected run files")
    for name,expected in files.items():
        if Path(name).name!=name or name=="manifest.json":
            raise ValueError("Unsafe manifest path")
        p=path/name
        if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
            raise ValueError("Run integrity mismatch")
    return manifest
