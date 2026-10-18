"""Optional digital-text PDF adapter and reviewer-defined packet splitting.

Not OCR; not automatic semantic classification; not a hostile-PDF sandbox.
"""
import hashlib
import json
import os
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError


def read_pdf(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower()!=".pdf":
        raise ValueError("Regular PDF required")
    raw=path.read_bytes()
    if len(raw)>2_000_000:raise ValueError("PDF exceeds 2 MB")
    try:
        reader=PdfReader(BytesIO(raw),strict=True)
        if reader.is_encrypted:raise ValueError("Encrypted PDF not supported")
        root=reader.trailer["/Root"]
        names=root.get("/Names",{})
        if any(k in root for k in ("/OpenAction","/AA","/AcroForm")) or any(k in names for k in ("/JavaScript","/EmbeddedFiles")):
            raise ValueError("Active or embedded PDF content not supported")
        if not 1<=len(reader.pages)<=20:raise ValueError("Require 1-20 pages")
        for page in reader.pages:
            if any(k in page for k in ("/AA","/Annots")):
                raise ValueError("PDF page actions/annotations not supported")
        return reader,raw
    except (PdfReadError,KeyError,TypeError) as exc:
        raise ValueError("Malformed PDF") from exc


def extract_invoice_pdf(path):
    reader,_raw=read_pdf(path)
    text="\n".join(page.extract_text() or "" for page in reader.pages)
    if not text.strip() or len(text)>65536:
        raise ValueError("PDF lacks supported digital text; OCR is not included")
    from .documents import parse_labeled_text
    return parse_labeled_text(text)


def split_packet(source,plan,output):
    """A reviewed exact source hash and complete non-overlapping page map are mandatory."""
    reader,raw=read_pdf(source)
    source_hash=hashlib.sha256(raw).hexdigest()
    if plan["source_sha256"]!=source_hash or not plan["reviewer"].strip() or datetime.fromisoformat(plan["reviewed_at"]).tzinfo is None:
        raise ValueError("Current source hash and reviewer/time required")
    documents=plan["documents"]
    if not documents or len(documents)>20:raise ValueError("Invalid split plan")
    used=[];ids=set()
    for d in documents:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}",d["document_id"]) or d["document_id"] in ids:
            raise ValueError("Unique safe document IDs required")
        ids.add(d["document_id"])
        pages=d["pages"]
        if not pages or any(type(n) is not int or not 1<=n<=len(reader.pages) for n in pages):
            raise ValueError("Invalid page range")
        used.extend(pages)
    if sorted(used)!=list(range(1,len(reader.pages)+1)):
        raise ValueError("Plan must cover every source page once")
    target=Path(output).absolute()
    for p in (target,*target.parents):
        if p.is_symlink():raise ValueError("Symlink output refused")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.mkdir(mode=0o700)
    manifest={"source_sha256":source_hash,"review_plan":plan,"files":{},"mode":"synthetic_or_private_review_only"}
    try:
        for index,d in enumerate(documents,1):
            writer=PdfWriter()
            for number in d["pages"]:writer.add_page(reader.pages[number-1])
            name=f"document-{index:02d}.pdf";path=target/name
            with path.open("xb") as h:
                os.chmod(path,0o600);writer.write(h)
            manifest["files"][name]=hashlib.sha256(path.read_bytes()).hexdigest()
        m=target/"split-manifest.json"
        m.write_text(json.dumps(manifest,indent=2)+"\n");os.chmod(m,0o600)
    except Exception:
        marker=target/"FAILED";marker.write_text("Incomplete PDF split; do not process outputs.\n");os.chmod(marker,0o600)
        raise
    return manifest
