from fastapi import FastAPI, HTTPException

from .pipeline import build_demo

app = FastAPI(title="Finance Operations Intelligence Engine", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok", "mode": "synthetic demonstration"}


@app.get("/v1/management-package")
def management_package():
    return build_demo()["management_package"]


@app.get("/v1/reviews")
def reviews():
    return build_demo()["approval_queue"]


@app.post("/v1/reviews/{review_id}/decision")
def decision(review_id: str, decision: str):
    if decision not in {"approved", "rejected", "investigate"}:
        raise HTTPException(400, "Decision must be approved, rejected, or investigate")
    if review_id not in {item["review_id"] for item in build_demo()["approval_queue"]}:
        raise HTTPException(404, "Review item not found")
    return {"review_id": review_id, "decision": decision, "persisted": False,
            "note": "Demo endpoint: no external or ledger write occurs."}
