# Finance Operations Intelligence Engine

Production-style reference architecture and consulting case study for a fictional $25M construction-and-manufacturing company with 100 employees. It uses **synthetic data only**.

It shows how finance events move from ingestion to controlled action:

```text
Source files -> validation -> classification -> controls -> approval -> reporting
                         |                     |             |
                    audit record          exception queue  forecasts
```

## What this repository demonstrates

| Area | Working example |
|---|---|
| Ingestion | Bank, card, invoice, payroll, recurring-expense CSV inputs |
| Controls | Duplicate, anomaly, reconciliation, and confidence rules |
| Finance operations | AR aging, close checklist, capex, debt, working capital |
| Planning | Budget versus actual, 13-week cash forecast, 12-month forecast |
| Governance | Human approval queue, audit log, source lineage |
| Delivery | CLI demo, FastAPI routes, optional Streamlit dashboard, CI tests |

## Fast local start

Requires Python 3.11 or later.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python scripts/run_demo.py
pytest
```

The demo writes `examples/demo_summary.json`. It does not connect to a bank, accounting system, Airtable, n8n, Supabase, or an LLM.

For a local API:

```bash
uvicorn foie.api:app --reload
```

For the optional dashboard:

```bash
streamlit run src/foie/dashboard.py
```

## Automation policy

| Confidence | System action | Human action |
|---|---|---|
| 0.90 to 1.00 | Post as a proposed, controlled result | Periodic review |
| 0.60 to 0.89 | Hold | Approve, correct, or reject |
| Below 0.60 | Investigate | Resolve with evidence |

No automated payment, journal posting, or external-system write occurs in this reference implementation.

## Architecture and data ownership

PostgreSQL or Supabase is the intended authoritative operational store in a deployed version. This demo uses in-memory objects and CSV fixtures to keep it safe and easy to run. Airtable may be used as an optional review workbench. It is not the authoritative ledger or audit store. The included n8n workflow is a non-live import template with an approval gate.

See [architecture](docs/architecture.md), [security and privacy](docs/security-privacy.md), [case study](docs/case-study.md), and [limitations](docs/limitations.md).

## Modeling assumptions

The fictional company is **Northstar Build & Fabrication LLC**, a single legal company. It has construction projects and a light fabrication operation. “Intercompany-style” entries model internal cost transfers between the Project Delivery and Fabrication cost centers. They are management allocations, not legal intercompany accounting. A multi-entity deployment needs separate legal-entity ledgers, due-to/due-from accounts, consolidation rules, and accounting review.

## Repository map

```text
src/foie/        Finance rules, forecasting, API, optional dashboard
data/raw/        Synthetic source fixtures
tests/           Unit and integration-style tests
n8n/             Non-live workflow import template
docs/            Architecture, controls, security, limitations, case study
scripts/         Run and validate the demonstration
```

## Public repository checklist

- [x] Synthetic data only
- [x] No credentials or private URLs
- [x] No client names, client outcomes, or deployment claims
- [x] Clear limits and human-control requirements
- [x] Tests and GitHub Actions workflow
- [x] Dependency and secret-ignore files

## License

MIT. This project is a technical demonstration, not accounting, tax, legal, or security advice.
