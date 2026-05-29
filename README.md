# Tacheon Technical Assessment — Dhanush Kumar

This repository is my submission for the Tacheon Data & AI Product Engineer assessment. It contains two tasks completed to production standard.

---

## Task 1 — Product Scoping

A complete v1 product scope for an internal marketing performance tool. The tool answers one repeated question for marketing analysts: "How is our marketing performing across channels right now, and where should we be focusing?"

Deliverables:
- **Product brief** — 9 sections covering problem, user, features, data flow, trust model, exclusions, and success metric
- **Flow diagram** — Mermaid.js diagram of the full data and user interaction flow
- **Wireframe descriptions** — Two screens described in enough detail for a designer to build from

→ [`task-1-product-scoping/`](./task-1-product-scoping/)

---

## Task 2 — Data Pipeline

A production-quality ETL pipeline that fetches 7-day weather forecast data for Mumbai from the Open-Meteo API, transforms it into an enriched dataset with six derived fields, and loads it into BigQuery.

Deliverables:
- **4 Python modules** — `fetch.py`, `transform.py`, `load.py`, `pipeline.py`
- **SQL queries** — analytical summary and data quality check
- **Unit tests** — 9 tests covering normal input, null handling, derived field correctness, and boundary conditions
- **Production strategy** — scheduling, failure detection, and scaling approach

→ [`task-2-pipeline/`](./task-2-pipeline/)

---

## Commit History

The commit history is part of the submission. Each commit message follows the format `<type>: <what changed and why>` and represents a deliberate stage of work, not a polished-after-the-fact squash.

---

## Author

Dhanush Kumar  
Assessment submitted: May 2026
