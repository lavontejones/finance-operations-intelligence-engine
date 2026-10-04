from dataclasses import asdict, dataclass
from datetime import date


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    posted_on: date
    source: str
    description: str
    amount: float
    account: str
    reference: str = ""


@dataclass(frozen=True)
class ReviewItem:
    review_id: str
    transaction_id: str
    reason: str
    confidence: float
    status: str
    source_record: str

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    occurred_on: str
    actor: str
    action: str
    object_id: str
    lineage: str

    def as_dict(self):
        return asdict(self)
