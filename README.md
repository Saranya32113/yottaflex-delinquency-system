# YottaFlex AI Technologies

## Delinquency & Collections Management System

An end-to-end synthetic delinquency and collections management system built using Python, SQLite, SQLAlchemy, Pandas and Streamlit.

### Project Overview

This project demonstrates how a financial collections workflow can manage loan delinquency, prioritize collection cases, schedule customer contacts, track promises to pay, reconcile payments and identify data-quality anomalies.

**All records are synthetic and intended exclusively for demonstration and evaluation. No real customer information is used.**

### Key Features

- Synthetic generation of 10,000 customers, accounts and loans.
- 30,000 installment records.
- Delinquency snapshots with DPD, arrears and risk categories.
- Collection case creation and priority scoring.
- Customer contact preferences and Do Not Contact restrictions.
- Contact scheduling based on permitted contact windows.
- Promise-to-Pay tracking and resolution.
- Payment reconciliation and installment allocations.
- Audit event records.
- Detection of five intentionally injected anomalies.
- CSV, JSON and SQLite SQL exports.
- Interactive Streamlit dashboard.

### Technology Stack

| Component | Technology |
|---|---|
| Programming | Python |
| Database | SQLite |
| ORM | SQLAlchemy |
| Data processing | Pandas, NumPy |
| Synthetic data | Faker |
| Dashboard | Streamlit |
| Visualization | Plotly |
| Testing | Python validation modules, pytest |

### Project Structure

```text
yottaflex-delinquency-system/
├── app.py
├── config.py
├── requirements.txt
├── init_db.py
├── check_data.py
├── migrate_payment_ids.py
├── migrate_case_contact_ids.py
├── database/
│   ├── __init__.py
│   ├── models.py
│   ├── database.py
│   └── relationships.py
├── generator/
│   ├── __init__.py
│   ├── master_data.py
│   ├── installments.py
│   ├── payments.py
│   ├── reversed_payments.py
│   ├── delinquency.py
│   ├── collection_cases.py
│   ├── contact_preferences.py
│   ├── promises.py
│   ├── audit_events.py
│   └── inject_anomalies.py
├── services/
│   ├── contact_scheduler.py
│   ├── resolve_promises.py
│   └── export_data.py
├── validation/
│   ├── check_payments.py
│   ├── check_contact_schedule.py
│   ├── check_promises.py
│   └── check_anomalies.py
├── dashboard/
├── tests/
│   ├── test_anomalies.py
│   ├── test_contacts.py
│   ├── test_payments.py
│   └── test_promises.py
├── docs/
│   └── data_dictionary.md
├── ai-usage/
│   └── ai_usage_log.md
└── data/
    ├── exports/
    └── ground_truth/
```

### Dataset Configuration

| Setting | Value |
|---|---:|
| Random seed | 20261022 |
| Customers | 10,000 |
| Accounts | 10,000 |
| Loans | 10,000 |
| Installments | 30,000 |
| Delinquency snapshots | 10,000 |
| Collection cases | 7,564 |
| Payment records | 21,556 |
| Promise-to-Pay records | 1,787 |

The installment dataset contains three installment records per loan, representing a recent installment window rather than the complete contractual loan schedule.

### Identifier Conventions

The system uses deterministic, zero-padded identifiers:

| Entity | Identifier format |
|---|---|
| Loan | `LOAN-2026-000001` |
| Installment | `INS-<loan-id>-001` |
| Collection case | `COL-2026-000001` |
| Contact attempt | `CTP-<case-id>-001` |
| Payment | `PMT-2026-000001` |

Identifiers are preserved across database relationships, audit references and exported ground-truth records.

### Installation

Python 3.10 or later is recommended.

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Windows CMD:

```cmd
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Run the Dashboard

From the project root:

```bash
python -m streamlit run app.py
```

Open the local URL shown in the terminal.

### Dashboard Modules

1. **Overview** – Portfolio KPIs, delinquency distribution and collection priorities.
2. **Collection Cases** – Collection case records and filters.
3. **Risk Analysis** – Risk categories, DPD and arrears analysis.
4. **Payments & Promises** – Payment reconciliation and Promise-to-Pay tracking.
5. **Contact Management** – Contact preferences, restrictions and scheduled tasks.
6. **Anomaly Detection** – Five injected synthetic data-quality exceptions.
7. **Data Exports** – Database table exports in CSV and JSON formats.

### Anomaly Detection

Five synthetic anomalies are injected to validate exception detection:

| ID | Anomaly |
|---|---|
| ANOM-001 | Paid-off loan remains in an open collection case |
| ANOM-002 | Contact attempt outside permitted hours |
| ANOM-003 | Payment allocated to an installment belonging to another loan |
| ANOM-004 | Promise amount exceeds recorded arrears |
| ANOM-005 | Disputed debt treated as a confirmed collection case |

Ground-truth labels are maintained separately under `data/ground_truth/`.

**Validation results:**

| Metric | Result |
|---|---:|
| Expected anomalies | 5 |
| Detected anomalies | 5 |
| Missed anomalies | 0 |
| Additional detections | 0 |

### Validation Commands

Run anomaly validation:

```bash
python -m validation.check_anomalies
```

Run payment validation:

```bash
python -m validation.check_payments
```

Run promise validation:

```bash
python -m validation.check_promises
```

Run contact schedule validation:

```bash
python -m validation.check_contact_schedule
```

Run automated tests:

```bash
python -m pytest tests -v
```

### Data Exports

The `data/exports/` directory contains:

- CSV exports for database tables.
- JSON exports for database tables.
- SQLite SQL dump.
- Export manifest.
- Scheduled contact task export.

Ground-truth anomaly labels are stored separately in `data/ground_truth/`.

### Important Assumptions and Limitations

- All data is synthetic.
- The outstanding balance calculation is a simplified principal-based estimate and does not represent a complete amortized interest calculation.
- Contact scheduling generates proposed tasks; it does not send actual messages.
- Contact scheduling does not currently model holidays, channel capacity or repeat-contact limits.
- Audit records include generated status observations and should not all be interpreted as verified historical state transitions.
- The installment records represent a three-installment sample per loan, not a complete loan repayment schedule.

### Security and Privacy

No real customer PII, credentials, API keys or confidential challenge documents should be committed to this repository.

The local SQLite database and Python virtual environment are excluded from Git tracking.

### Purpose

This project demonstrates synthetic financial data engineering, delinquency analytics, collection workflow management, payment reconciliation, anomaly detection and dashboard development.