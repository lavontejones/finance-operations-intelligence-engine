# Architecture

```text
CSV/API sources
      |
Validation and schema checks
      |
Normalized finance events ----> immutable audit event + source ID
      |
Rules: category, duplicate, anomaly, reconciliation
      |                         |
High confidence              Medium / low confidence
proposed result               review queue / investigation
      |                         |
Forecasts, close tasks, KPIs, CFO package
```

## Intended production components

| Component | Purpose | Authority |
|---|---|---|
| FastAPI | Receives controlled requests and serves reports | Application boundary |
| PostgreSQL/Supabase | Events, review decisions, audit records | Authoritative operational data |
| Object storage | Encrypted source documents and hashes | Source evidence |
| n8n | Scheduled intake and notification orchestration | Not a ledger |
| Airtable | Optional human review board | Not authoritative |
| Dashboard | Read-only operations and management view | Presentation only |

The local example replaces these services with CSV fixtures and in-memory processing. It is deliberately non-live.

## Finance controls

- Preserve a source identifier on every processed event.
- Keep the original file and its hash in a deployed design.
- Require a different user to approve exceptions when segregation of duties is needed.
- Do not permit an automation to pay a vendor, post a journal entry, or change a bank record without an approved integration design.
- Reconcile records before close; retain unresolved exceptions.

## Close, debt, capex, and working capital

The close workflow includes bank reconciliation, AR review, capex/debt review, accrual review, and management review. A deployed model would calculate depreciation from the fixed-asset register, separate loan principal from interest, and derive working-capital requirements from AR, inventory, AP, and project commitments. The public fixtures show only a small controlled sample.
