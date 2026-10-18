import hashlib

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from foie.documents import process_folder
from foie.pdf_intake import extract_invoice_pdf, split_packet


def pdf(path,pages=2,blank=False):
    writer=PdfWriter()
    for i in range(pages):
        page=writer.add_blank_page(width=612,height=792)
        if not blank:
            font=DictionaryObject({NameObject("/Type"):NameObject("/Font"),NameObject("/Subtype"):NameObject("/Type1"),NameObject("/BaseFont"):NameObject("/Helvetica")})
            page[NameObject("/Resources")]=DictionaryObject({NameObject("/Font"):DictionaryObject({NameObject("/F1"):writer._add_object(font)})})
            lines=["document_type: invoice",f"document_id: I{i+1}","vendor: Synthetic Supplier","invoice_date: 2026-10-01","currency: USD","subtotal: 100.00","tax: 8.00","total: 108.00"]
            stream=DecodedStreamObject();stream.set_data(("BT /F1 12 Tf 50 750 Td 16 TL "+" ".join(f"({s}) Tj T*" for s in lines)+" ET").encode())
            page[NameObject("/Contents")]=writer._add_object(stream)
    with path.open("wb") as h:writer.write(h)
    return hashlib.sha256(path.read_bytes()).hexdigest()

def plan(sha,documents=None):
    return {"source_sha256":sha,"reviewer":"Synthetic Reviewer","reviewed_at":"2026-10-14T15:00:00+00:00",
            "documents":documents or [{"document_id":"I1","pages":[1]},{"document_id":"I2","pages":[2]}]}

def test_split_extract_conserve_pages(tmp_path):
    source=tmp_path/"packet.pdf";sha=pdf(source)
    m=split_packet(source,plan(sha),tmp_path/"split")
    assert len(m["files"])==2
    records=process_folder(tmp_path/"split")
    assert len(records)==2 and not any(r["blocking_reasons"] for r in records)
    assert all(r["total"]=="108.00" for r in records)
    with pytest.raises(FileExistsError):split_packet(source,plan(sha),tmp_path/"split")

@pytest.mark.parametrize("kind",["stale","overlap","gap","traversal","missing_reviewer","naive"])
def test_bad_split_plan_refused(tmp_path,kind):
    source=tmp_path/"packet.pdf";p=plan(pdf(source))
    if kind=="stale":p["source_sha256"]="stale"
    if kind=="overlap":p["documents"][1]["pages"]=[1,2]
    if kind=="gap":p["documents"]=p["documents"][:1]
    if kind=="traversal":p["documents"][0]["document_id"]="../invoice"
    if kind=="missing_reviewer":p["reviewer"]=""
    if kind=="naive":p["reviewed_at"]="2026-10-14T15:00:00"
    with pytest.raises(ValueError):split_packet(source,p,tmp_path/"split")
    assert not (tmp_path/"split").exists()

def test_blank_pdf_is_ocr_hold_not_extracted(tmp_path):
    p=tmp_path/"scan.pdf";pdf(p,pages=1,blank=True)
    with pytest.raises(ValueError,match="OCR"):extract_invoice_pdf(p)

def test_active_pdf_refused(tmp_path):
    writer=PdfWriter();writer.add_blank_page(612,792);writer.add_js("app.alert('synthetic')")
    p=tmp_path/"active.pdf"
    with p.open("wb") as h:writer.write(h)
    with pytest.raises(ValueError):extract_invoice_pdf(p)

def test_split_tamper_refused(tmp_path):
    p=tmp_path/"packet.pdf";sha=pdf(p);split_packet(p,plan(sha),tmp_path/"split")
    (tmp_path/"split/document-01.pdf").write_text("modified")
    with pytest.raises(ValueError):process_folder(tmp_path/"split")
