\# YottaFlex Delinquency \& Collections System

\## Database Schema and Data Dictionary



\### 1. Overview



The system uses SQLite and SQLAlchemy to store synthetic customer, loan, installment, payment and collections data.



The database contains 13 tables.



\### 2. Database Tables



| Table | Purpose |

|---|---|

| customers | Stores synthetic customer information |

| accounts | Stores customer account details and status |

| loans | Stores loan principal, interest rate, term and status |

| installments | Stores installment due dates, amounts and payment status |

| delinquency\_snapshots | Stores DPD, arrears, outstanding balance and risk information |

| contact\_preferences | Stores preferred contact channels, permitted hours and DNC restrictions |

| collection\_cases | Stores collection case status, issue type and priority |

| contact\_attempts | Stores contact attempt details and outcomes |

| promises\_to\_pay | Stores customer payment promises and their status |

| payments | Stores received, reversed and failed payment records |

| payment\_allocations | Links payments to installments |

| promise\_payment\_allocations | Links payments to promises to pay |

| audit\_events | Stores audit-related event records |



\### 3. Entity Descriptions



\#### Customers

Contains synthetic customer identifiers, names, email addresses, phone numbers and creation timestamps.



Primary key: `customer\_id`



\#### Accounts

Represents customer accounts and their status.



Primary key: `account\_id`



Foreign key: `customer\_id`



\#### Loans

Contains loan details, including principal, interest rate, term, start date and loan status.



Primary key: `loan\_id`



Foreign key: `account\_id`



\#### Installments

Stores installment number, due date, amount due, amount paid and repayment status.



Primary key: `installment\_id`



Foreign key: `loan\_id`



Unique constraint: `loan\_id` and `installment\_number`



\#### Delinquency Snapshots

Stores delinquency information for a loan on a snapshot date.



Important attributes include:



\- Days past due (DPD)

\- Total arrears

\- Outstanding balance

\- Risk category

\- Dispute indicator

\- Hardship indicator



Primary key: `snapshot\_id`



Foreign key: `loan\_id`



\#### Contact Preferences

Stores customer communication preferences, permitted contact hours, timezone and Do Not Contact status.



Primary key: `preference\_id`



Foreign key: `customer\_id`



\#### Collection Cases

Represents collection work associated with a loan and its delinquency snapshot.



Includes priority score, priority band, case status and issue type.



Primary key: `case\_id`



Foreign keys: `loan\_id`, `snapshot\_id`



\#### Contact Attempts

Records attempted customer contacts, channel, timestamp, outcome and any restriction-related blocking information.



Primary key: `attempt\_id`



Foreign keys: `case\_id`, `preference\_id`



\#### Promises to Pay

Stores promised payment amounts, promised dates and promise status.



Primary key: `promise\_id`



Foreign keys: `case\_id`, `attempt\_id`



\#### Payments

Stores payment date, amount, method and payment status.



Primary key: `payment\_id`



Foreign key: `loan\_id`



\#### Payment Allocations

Connects a payment to an installment and records the allocated amount.



Primary key: `allocation\_id`



Foreign keys: `payment\_id`, `installment\_id`



\#### Promise Payment Allocations

Links payments to promises to pay and records the allocated amount.



Primary key: `id`



Foreign keys: `promise\_id`, `payment\_id`



\#### Audit Events

Stores event-related information, including entity type, entity identifier, event type, timestamp, old and new values, actor type and notes.



Primary key: `event\_id`



\### 4. Main Relationships



\- One customer can have multiple accounts.

\- One account can have multiple loans.

\- One loan can have multiple installments.

\- One loan can have multiple delinquency snapshots.

\- One customer can have contact preferences.

\- One loan can have collection cases.

\- One collection case can have contact attempts and promises to pay.

\- One loan can have multiple payments.

\- Payments can be allocated to installments.

\- Payments can also be linked to promises to pay.



\### 5. Dataset Configuration



| Attribute | Value |

|---|---:|

| Random seed | 20261022 |

| Customers | 10,000 |

| Accounts | 10,000 |

| Loans | 10,000 |

| Installments | 30,000 |

| Delinquency snapshots | 10,000 |

| Collection cases | 7,564 |

| Payments | 21,556 |

| Promises to Pay | 1,787 |



\### 6. Data Assumptions



\- All generated records are synthetic.

\- Three installment records are generated per loan as a recent installment sample.

\- Outstanding balance is a simplified principal-based estimate.

\- Contact scheduling generates proposed tasks and does not send actual communications.

\- Ground-truth anomaly labels are maintained separately from operational records.



\### 7. Data Quality



The validation process checks payment allocations, contact restrictions, promise status resolution and five intentionally injected anomalies.



The anomaly detection validation achieved five expected detections, zero missed detections and zero additional detections.



