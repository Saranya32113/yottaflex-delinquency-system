\# AI Usage Log

\## YottaFlex Delinquency \& Collections Management System



\### 1. Purpose



This document records the use of AI assistance during the development of the synthetic delinquency and collections management project.



AI was used as a development assistant. Generated suggestions and code were reviewed, executed and validated during implementation.



\### 2. AI-Assisted Development Activities



| Area | AI Assistance |

|---|---|

| Project architecture | Planning modules, folders and database relationships |

| Database design | Assistance with SQLAlchemy models and entity relationships |

| Synthetic data generation | Assistance with reproducible data generation logic |

| Delinquency processing | Assistance with DPD, arrears and risk categorization logic |

| Collection management | Assistance with case prioritization and workflow logic |

| Payment reconciliation | Assistance with payment allocation and validation |

| Contact management | Assistance with contact restrictions and scheduling logic |

| Promise-to-Pay | Assistance with promise status resolution |

| Anomaly detection | Assistance with detection rules and validation |

| Dashboard | Assistance with Streamlit pages, tables and visualizations |

| Documentation | Assistance with README and data dictionary preparation |



\### 3. Example Prompt Categories



The following are summaries of the types of prompts used during development, not verbatim conversation transcripts.



1\. Design a modular Python architecture for a delinquency and collections management system.

2\. Generate reproducible synthetic customer, account, loan and installment data.

3\. Implement SQLAlchemy database models and relationships.

4\. Develop payment reconciliation and promise-to-pay validation.

5\. Implement contact scheduling with customer communication restrictions.

6\. Create anomaly detection rules and compare results with ground-truth labels.

7\. Build a Streamlit dashboard for collections analytics.

8\. Troubleshoot Python, SQLAlchemy and Streamlit implementation issues.



\### 4. Human Review and Validation



AI-assisted outputs were reviewed through implementation and execution.



Validation included:



\- Database record count checks.

\- Payment allocation validation.

\- Contact schedule validation.

\- Promise status validation.

\- Ground-truth anomaly comparison.

\- Dashboard section verification.

\- CSV, JSON and SQL export verification.



\### 5. Anomaly Detection Validation



The system contains five intentionally injected synthetic anomalies.



Validation result:



| Metric | Result |

|---|---:|

| Ground-truth anomalies | 5 |

| Detected anomalies | 5 |

| Missed anomalies | 0 |

| Additional detections | 0 |



\### 6. Responsible AI Usage



\- AI was used for development assistance, not as a replacement for testing.

\- Generated code was executed and checked against project requirements.

\- Synthetic data was used for demonstration.

\- No real customer information or confidential credentials were supplied for code generation.

\- Final implementation decisions and validation remain the responsibility of the project developer.



\### 7. Limitations



AI-generated suggestions may require modification to match the actual project architecture and runtime environment. All important outputs were checked through implementation and validation commands.



