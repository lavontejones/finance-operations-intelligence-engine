# Finance Operations Intelligence Engine

> A production-style reference architecture for controlled finance operations: from synthetic source records to reviewable exceptions, cash forecasts, and CFO reporting.

**Finance Operations Intelligence Engine** is a public portfolio project and consulting case study. It models a fictional $25M construction-and-manufacturing company with 100 employees. Every company, transaction, person, and amount in this repository is synthetic.

It is not an accounting system, a banking connection, or a deployed client product. It is a working demonstration of the architecture, logic, controls, and communication needed to design one responsibly.

## Contents

- [Business case](#business-case)
- [What works now](#what-works-now)
- [System flow](#system-flow)
- [Control model](#control-model)
- [Finance scope](#finance-scope)
- [Quick start](#quick-start)
- [Sample result](#sample-result)
- [API and dashboard](#api-and-dashboard)
- [Data model and lineage](#data-model-and-lineage)
- [Production reference design](#production-reference-design)
- [Repository structure](#repository-structure)
- [Security, privacy, and limits](#security-privacy-and-limits)

## Business case

Small and mid-sized finance teams often receive activity from several places: bank accounts, company cards, invoices, payroll exports, recurring vendor bills, and project systems. A basic spreadsheet process can record these events. It becomes less reliable when the team must also answer four questions:

1. Is this record complete, unique, and matched to the ledger?
2. Can the system explain why it categorized or flagged the record?
3. Which items require a person to approve, correct, or investigate?
4. What does current activity mean for cash, receivables, close work, and management reporting?

This project answers those questions with clear, deterministic examples. It keeps a link to the source record, applies a rule, records the result, and sends uncertainty to a human review queue.

## What works now

| Area | Demonstration capability | Output |
|---|---|---|
| Data intake | Reads synthetic bank, ledger, invoice, payroll, and recurring-expense CSV files | Normalized records and source inventory |
| Transaction control | Finds duplicate activity and unusually large account activity | Review items with reason and confidence |
| Classification | Applies simple, explainable keyword rules | Category and confidence result |
| Reconciliation | Matches bank records to ledger records by date, amount, and reference | Matched count and unmatched items |
| Receivables | Groups open invoices into aging buckets | Current through over-90-day balances |
| Planning | Produces budget variance, 13-week cash, and 12-month operating forecast examples | Structured forecast records |
| Management reporting | Calculates a small KPI set and produces a CFO-package summary | JSON management package |
| Governance | Creates audit events and an approval queue | Source lineage and action state |
| Delivery | Provides a command-line run, API routes, optional dashboard, tests, and CI | Local and GitHub validation paths |

## System flow

```text
Synthetic source files
bank | ledger | invoices | payroll | recurring expenses
                         |
                         v
             Input validation and normalization
                         |
                         +--------------------------+
                         |                          |
                         v                          v
               Finance event + source ID       Audit event + lineage
                         |
                         v
      Classification | duplicate | anomaly | reconciliation rules
                         |
            +------------+-------------+
            |                          |
            v                          v
     High-confidence proposal    Review or investigation item
            |                          |
            +------------+-------------+
                         |
                         v
   AR aging | close tasks | cash forecast | KPIs | CFO package
```

### Design rule

The system does not hide uncertainty. It shows the rule, confidence, source record, and required action. It does not automatically send payments, post journals, or write to an external finance system.

## Control model

| Confidence band | System treatment | Required human treatment |
|---|---|---|
| 0.90 to 1.00 | Create a controlled proposal | Perform periodic review or approval required by policy |
| 0.60 to 0.89 | Hold the item | Approve, correct, or reject it |
| Below 0.60 | Mark for investigation | Resolve with supporting evidence |

The included example creates two review items:

- A duplicate fuel-card settlement.
- A capital-equipment item that is unusually large compared with other capital-expenditure activity.

These are rule examples. They are not a complete fraud-detection system or a substitute for accounting review.

## Finance scope

### Current runnable examples

```text
Bank and card activity        -> reconciliation, duplicate and anomaly controls
Customer invoices             -> accounts-receivable aging
Payroll export                -> intake source inventory
Recurring expense export      -> intake source inventory
Budget and actual values      -> variance analysis
Weekly cash assumptions       -> 13-week cash forecast
Monthly revenue/cost values   -> rolling 12-month operating forecast
```

### Reference architecture scope

The repository documents a production path for the following areas. The local code demonstrates a controlled subset so that it remains safe, understandable, and runnable without services or credentials.

| Finance function | Intended production design |
|---|---|
| Monthly close | Close tasks, owner, due date, evidence link, sign-off, and unresolved-exception carryover |
| Capex | Asset register, approval record, useful life, depreciation schedule, and project allocation |
| Debt | Principal, interest, maturity, covenant, payment schedule, and forecast effect |
| Working capital | AR, inventory, AP, project commitments, and cash-conversion measurements |
| Internal allocations | Project Delivery and Fabrication cost-center transfers with clear management-reporting labels |
| Legal intercompany accounting | Separate entity ledgers, due-to/due-from balances, elimination rules, and consolidation controls |

The public case has one legal company: **Northstar Build & Fabrication LLC**. The “intercompany-style” record is an internal cost-center allocation. It is not a legal intercompany entry.

## Quick start

### 1. Prerequisites

- Python 3.11 or later.
- A terminal application.

### 2. Create an isolated project environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e '.[dev]'
```

### 3. Run the synthetic demonstration

```bash
python3 scripts/run_demo.py
```

This creates `examples/demo_summary.json`. The file is generated from local synthetic fixtures. No network connection is used.

### 4. Run the tests

```bash
pytest
```

### 5. Run the API

```bash
uvicorn foie.api:app --reload
```

Open `http://127.0.0.1:8000/docs` for the local API documentation.

### 6. Run the optional dashboard

```bash
python3 -m pip install -e '.[dashboard]'
streamlit run src/foie/dashboard.py
```

## Sample result

The checked-in sample output is available at [`examples/demo_summary.json`](examples/demo_summary.json). A shortened example follows:

```json
{
  "company": "Northstar Build & Fabrication LLC (fictional)",
  "reconciliation": {
    "bank_records": 9,
    "ledger_records": 4,
    "matched": 4
  },
  "management_package": {
    "kpis": {
      "gross_margin_pct": 16.2,
      "days_sales_outstanding": 87.8,
      "cash_ratio": 1.53
    },
    "week_13_cash": 1500000,
    "open_control_items": 2
  }
}
```

All values are examples. They do not describe an actual business or financial result.

## API and dashboard

| Route | Method | Purpose | Write behavior |
|---|---|---|---|
| `/health` | `GET` | Reports local demonstration status | No write |
| `/v1/management-package` | `GET` | Returns the synthetic CFO-package summary | No write |
| `/v1/reviews` | `GET` | Returns open control items | No write |
| `/v1/reviews/{review_id}/decision` | `POST` | Demonstrates a human decision | Returns a simulated result only |

Example local request:

```bash
curl http://127.0.0.1:8000/v1/management-package
```

The optional dashboard displays KPI values, the control queue, and the 13-week cash series. It reads the same synthetic in-memory result as the API. It does not store changes.

## Data model and lineage

Every finance event in a deployed design needs enough information to answer: “Where did this number come from, what happened to it, and who made a decision about it?”

```text
source system + source record ID
              |
              v
         finance event
              |
      +-------+--------+
      |                |
      v                v
control result     audit event
      |                |
      +-------+--------+
              |
              v
       review decision and report
```

The included reference schema defines three core records:

| Record | Purpose |
|---|---|
| `finance_event` | A normalized source event with source hash and source-record ID |
| `review_item` | An item that needs a human decision, with reason and confidence |
| `audit_event` | A record of an action, actor, object, time, and lineage |

See [`docs/postgres-schema.sql`](docs/postgres-schema.sql) for the reference PostgreSQL schema.

## Production reference design

```text
External systems               Control and reporting layer
----------------              ---------------------------------
Bank / card exports     ->    FastAPI intake boundary
Accounting platform     ->    PostgreSQL or Supabase database
Payroll platform        ->    Object storage for source evidence
Project system          ->    Rule and reconciliation service
                              Human review application
                              Reporting API and dashboard
                              n8n for scheduled orchestration
```

| Component | Role | Source of truth? |
|---|---|---|
| PostgreSQL or Supabase | Finance events, review states, audit records | Yes, for application operations |
| Accounting platform | Official general ledger and accounting records | Yes, for accounting records |
| Object storage | Encrypted original source documents and hashes | Yes, for source evidence |
| FastAPI | Validated request and reporting boundary | No |
| n8n | Scheduled intake and notification workflow | No |
| Airtable | Optional team review board or operations workspace | No |
| Streamlit or web dashboard | Read-only presentation layer | No |

### Optional LLM use

An LLM may help a human summarize a large exception list or draft a review note. It must not become the source of truth, create an accounting entry without approval, or replace deterministic validation. The runnable project does not call an LLM.

## Repository structure

```text
src/foie/
  controls.py          Duplicate, anomaly, reconciliation, and category rules
  forecasting.py       AR aging and forecast calculations
  pipeline.py          Synthetic intake and end-to-end demonstration assembly
  reporting.py         KPI, variance, and management-package output
  api.py               Local FastAPI endpoints
  dashboard.py         Optional Streamlit dashboard

data/raw/              Synthetic source fixtures only
tests/                 Unit and integration-style tests
docs/                  Architecture, case study, schema, security, and limits
n8n/                   Inactive workflow template with a human approval gate
examples/              Generated demonstration output
scripts/               Command-line demonstration runner
.github/workflows/     GitHub Actions validation workflow
```

## Validation and continuous integration

The GitHub Actions workflow runs these checks on a push or pull request to `main`:

```text
Install dependencies
       |
       v
Run Ruff static checks
       |
       v
Run Pytest tests
       |
       v
Run the synthetic demonstration
```

The local demo was validated to produce a management package, reconciliation results, source inventory, audit trail, and two review items.

## Security, privacy, and limits

| Topic | This repository | Required before real use |
|---|---|---|
| Data | Synthetic fixtures only | Approved data handling, retention, and minimization rules |
| Credentials | None included | Managed secrets and secret rotation |
| API access | Local demonstration without authentication | Authentication, authorization, role controls, and logging |
| Data protection | Teaching implementation | Encryption in transit and at rest, backup restoration tests |
| Financial action | No payments, postings, or external writes | Segregation of duties, approval controls, tested integrations |
| Audit | In-memory example audit events | Immutable retention, monitoring, and periodic control review |

Read these documents before extending the project:

- [Architecture](docs/architecture.md)
- [Case study](docs/case-study.md)
- [Security and privacy notes](docs/security-privacy.md)
- [Limitations](docs/limitations.md)
- [Security reporting policy](SECURITY.md)

## Public repository checklist

- [x] Synthetic data only
- [x] No credentials, private URLs, or access tokens
- [x] No client names, client outcomes, or live-deployment claims
- [x] Human-control and approval requirements stated clearly
- [x] Tests and a GitHub Actions workflow included
- [x] `.gitignore` and `.env.example` included
- [x] MIT license included

## License and disclaimer

MIT License. This repository is a technical demonstration. It is not accounting, tax, legal, financial, or security advice.
