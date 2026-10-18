from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal

from .money import money


@dataclass(frozen=True)
class Transaction:
    transaction_id: str
    posted_on: date
    source: str
    description: str
    amount: Decimal
    account: str
    reference: str = ""

    def __post_init__(self):
        if not self.transaction_id.strip() or not self.account.strip():
            raise ValueError("Transaction ID and account required")
        object.__setattr__(self, "amount", money(self.amount))


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

