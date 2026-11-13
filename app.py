
import json
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from config import DATABASE_PATH, EXPORT_DIR, GROUND_TRUTH_DIR
from database.database import get_session
from validation.check_anomalies import detect_anomalies


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="YottaFlex | Collections Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("YottaFlex AI Technologies")
st.subheader("Delinquency & Collections Management Dashboard")

st.caption(
    "Synthetic demonstration dataset | Snapshot date: 13 November 2026"
)

DB_PATH = Path(DATABASE_PATH)
EXPORT_PATH = Path(EXPORT_DIR)
GROUND_TRUTH_PATH = Path(GROUND_TRUTH_DIR) / "ground_truth.json"


# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

@st.cache_data(ttl=30)
def load_table(query):
    connection = sqlite3.connect(str(DB_PATH))
    try:
        return pd.read_sql_query(query, connection)
    finally:
        connection.close()


@st.cache_data(ttl=30)
def load_counts():
    connection = sqlite3.connect(str(DB_PATH))

    try:
        tables = [
            "customers",
            "accounts",
            "loans",
            "installments",
            "payments",
            "payment_allocations",
            "delinquency_snapshots",
            "collection_cases",
            "contact_preferences",
            "contact_attempts",
            "promises_to_pay",
            "promise_payment_allocations",
            "audit_events",
        ]

        result = {}

        for table in tables:
            result[table] = pd.read_sql_query(
                f'SELECT COUNT(*) AS total FROM "{table}"',
                connection
            ).iloc[0]["total"]

        return result

    finally:
        connection.close()


# --------------------------------------------------
# LOAD DATABASE DATA
# --------------------------------------------------

if not DB_PATH.exists():
    st.error("Database file not found. Please initialize the database.")
    st.stop()

counts = load_counts()

cases = load_table("""
    SELECT case_id, loan_id, priority_score, priority_band,
           case_status, issue_type
    FROM collection_cases
""")

snapshots = load_table("""
    SELECT loan_id, days_past_due, total_arrears,
           outstanding_balance, risk_category,
           disputed, hardship_flag
    FROM delinquency_snapshots
""")

promises = load_table("""
    SELECT promise_id, case_id, promised_amount,
           promised_date, promise_status
    FROM promises_to_pay
""")

payments = load_table("""
    SELECT payment_id, amount, payment_status, payment_date
    FROM payments
""")

contact_preferences = load_table("""
    SELECT preference_id, channel, do_not_contact
    FROM contact_preferences
""")


# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------

st.sidebar.title("Navigation")

section = st.sidebar.radio(
    "Select dashboard section",
    [
        "Overview",
        "Collection Cases",
        "Risk Analysis",
        "Payments & Promises",
        "Contact Management",
        "Anomaly Detection",
        "Data Exports",
    ],
    key="dashboard_section",
)

# Temporary debug message
st.info(f"DEBUG — Selected dashboard section: {section}")

st.sidebar.divider()
st.sidebar.write("Dataset information")
st.sidebar.write(f"Customers: {counts['customers']:,}")
st.sidebar.write(f"Loans: {counts['loans']:,}")
st.sidebar.write(f"Installments: {counts['installments']:,}")


# --------------------------------------------------
# OVERVIEW
# --------------------------------------------------

if section == "Overview":

    st.header("Portfolio Overview")

    total_loans = counts["loans"]
    total_cases = counts["collection_cases"]

    open_cases = int(
        (cases["case_status"] == "open").sum()
    )

    total_arrears = snapshots["total_arrears"].sum()

    total_received = payments.loc[
        payments["payment_status"] == "received",
        "amount"
    ].sum()

    total_promises = counts["promises_to_pay"]

    fulfilled = int(
        (promises["promise_status"] == "fulfilled").sum()
    )

    missed = int(
        (promises["promise_status"] == "missed").sum()
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Loans", f"{total_loans:,}")
    col2.metric("Collection Cases", f"{total_cases:,}")
    col3.metric("Open Cases", f"{open_cases:,}")
    col4.metric("Total Arrears", f"₹{total_arrears:,.2f}")

    col5, col6, col7, col8 = st.columns(4)

    col5.metric("Received Payments", f"₹{total_received:,.2f}")
    col6.metric("Total Promises", f"{total_promises:,}")
    col7.metric("Fulfilled Promises", f"{fulfilled:,}")
    col8.metric("Missed Promises", f"{missed:,}")

    st.divider()

    left, right = st.columns(2)

    with left:
        st.subheader("Delinquency Risk Distribution")

        risk_data = (
            snapshots["risk_category"]
            .value_counts()
            .rename_axis("Risk")
            .reset_index(name="Count")
        )

        fig = px.pie(
            risk_data,
            names="Risk",
            values="Count",
            hole=0.4,
            title="Loans by Risk Category"
        )

        st.plotly_chart(fig, width="stretch")

    with right:
        st.subheader("Collection Priority Distribution")

        priority_data = (
            cases["priority_band"]
            .value_counts()
            .rename_axis("Priority")
            .reset_index(name="Count")
        )

        fig = px.bar(
            priority_data,
            x="Priority",
            y="Count",
            color="Priority",
            title="Collection Cases by Priority"
        )

        st.plotly_chart(fig, width="stretch")

    st.subheader("Collection Case Status")

    status_data = (
        cases["case_status"]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Count")
    )

    st.dataframe(status_data, width="stretch")


# --------------------------------------------------
# COLLECTION CASES
# --------------------------------------------------

elif section == "Collection Cases":

    st.header("Collection Case Management")

    col1, col2 = st.columns(2)

    with col1:
        selected_priority = st.selectbox(
            "Filter by priority",
            ["All", "high", "medium", "low"]
        )

    with col2:
        selected_status = st.selectbox(
            "Filter by status",
            ["All", "open", "on_hold", "review", "closed"]
        )

    filtered = cases.copy()

    if selected_priority != "All":
        filtered = filtered[
            filtered["priority_band"] == selected_priority
        ]

    if selected_status != "All":
        filtered = filtered[
            filtered["case_status"] == selected_status
        ]

    st.metric("Matching Cases", f"{len(filtered):,}")

    st.dataframe(
        filtered.sort_values(
            "priority_score",
            ascending=False
        ),
        width="stretch",
        hide_index=True
    )


# --------------------------------------------------
# RISK ANALYSIS
# --------------------------------------------------

elif section == "Risk Analysis":

    st.header("Delinquency Risk Analysis")

    risk_summary = (
        snapshots.groupby("risk_category")
        .agg(
            loan_count=("loan_id", "count"),
            average_dpd=("days_past_due", "mean"),
            total_arrears=("total_arrears", "sum"),
        )
        .reset_index()
    )

    st.dataframe(
        risk_summary,
        width="stretch",
        hide_index=True
    )

    fig = px.bar(
        risk_summary,
        x="risk_category",
        y="loan_count",
        color="risk_category",
        title="Loans by Risk Category"
    )

    st.plotly_chart(fig, width="stretch")

    st.subheader("Delinquency Indicators")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Disputed Loans",
        f"{int(snapshots['disputed'].sum()):,}"
    )

    col2.metric(
        "Hardship Loans",
        f"{int(snapshots['hardship_flag'].sum()):,}"
    )

    col3.metric(
        "Average Days Past Due",
        f"{snapshots['days_past_due'].mean():.1f}"
    )


# --------------------------------------------------
# PAYMENTS AND PROMISES
# --------------------------------------------------

elif section == "Payments & Promises":

    st.header("Payment Reconciliation & Promise Tracking")

    payment_summary = (
        payments.groupby("payment_status")
        .agg(
            payment_count=("payment_id", "count"),
            total_amount=("amount", "sum")
        )
        .reset_index()
    )

    st.subheader("Payment Summary")

    st.dataframe(
        payment_summary,
        width="stretch",
        hide_index=True
    )

    promise_summary = (
        promises.groupby("promise_status")
        .agg(
            promise_count=("promise_id", "count"),
            promised_amount=("promised_amount", "sum")
        )
        .reset_index()
    )

    st.subheader("Promise-to-Pay Summary")

    st.dataframe(
        promise_summary,
        width="stretch",
        hide_index=True
    )

    fig = px.bar(
        promise_summary,
        x="promise_status",
        y="promise_count",
        color="promise_status",
        title="Promise Status Distribution"
    )

    st.plotly_chart(fig, width="stretch")


# --------------------------------------------------
# CONTACT MANAGEMENT
# --------------------------------------------------

elif section == "Contact Management":

    st.header("Contact Preferences & Scheduling")

    channel_summary = (
        contact_preferences.groupby("channel")
        .size()
        .reset_index(name="customers")
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Preferred Contact Channels")

        fig = px.pie(
            channel_summary,
            names="channel",
            values="customers",
            title="Customer Contact Preferences"
        )

        st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Contact Restrictions")

        restriction_summary = (
            contact_preferences["do_not_contact"]
            .value_counts()
            .rename_axis("Do Not Contact")
            .reset_index(name="Customers")
        )

        st.dataframe(
            restriction_summary,
            width="stretch",
            hide_index=True
        )

    schedule_path = EXPORT_PATH / "contact_schedule.csv"

    st.subheader("Scheduled Contact Tasks")

    if schedule_path.exists():
        schedule = pd.read_csv(schedule_path)

        st.metric("Scheduled Tasks", f"{len(schedule):,}")

        st.dataframe(
            schedule.head(100),
            width="stretch",
            hide_index=True
        )

        with open(schedule_path, "rb") as file:
            st.download_button(
                "Download Contact Schedule CSV",
                data=file,
                file_name="contact_schedule.csv",
                mime="text/csv"
            )
    else:
        st.warning("Contact schedule export was not found.")


# --------------------------------------------------
# ANOMALY DETECTION
# --------------------------------------------------

elif section == "Anomaly Detection":

    st.header("Data Quality & Anomaly Detection")

    st.warning(
        "This demonstration contains five intentionally injected "
        "synthetic anomalies. They are test exceptions, not real customer events."
    )

    try:
        session = get_session()

        try:
            detected = detect_anomalies(session)
        finally:
            session.close()

        if GROUND_TRUTH_PATH.exists():
            with open(
                GROUND_TRUTH_PATH,
                "r",
                encoding="utf-8"
            ) as file:
                ground_truth = json.load(file)
        else:
            ground_truth = []

        expected = {
            (item["anomaly_type"], item["entity_id"])
            for item in ground_truth
        }

        found = {
            (item["anomaly_type"], item["entity_id"])
            for item in detected
        }

        matched = expected.intersection(found)
        missed = expected - found
        additional = found - expected

        col1, col2, col3 = st.columns(3)

        col1.metric("Ground Truth", len(expected))
        col2.metric("Detected", len(matched))
        col3.metric("Missed", len(missed))

        if not missed and expected:
            st.success("All ground-truth anomalies were detected.")
        else:
            st.error("Some expected anomalies were not detected.")

        if detected:
            st.subheader("Detected Exceptions")

            st.dataframe(
                pd.DataFrame(detected),
                width="stretch",
                hide_index=True
            )

        if additional:
            st.subheader("Additional Detections")

            st.dataframe(
                pd.DataFrame([
                    {
                        "anomaly_type": item[0],
                        "entity_id": item[1]
                    }
                    for item in additional
                ]),
                width="stretch",
                hide_index=True
            )

    except Exception as error:
        st.error(f"Unable to load anomaly report: {error}")


# --------------------------------------------------
# DATA EXPORTS
# --------------------------------------------------

elif section == "Data Exports":

    st.header("Database Exports")

    manifest_path = EXPORT_PATH / "export_manifest.json"

    if manifest_path.exists():
        with open(
            manifest_path,
            "r",
            encoding="utf-8"
        ) as file:
            manifest = json.load(file)

        st.write("Available database table exports")

        manifest_rows = []

        for table_name, details in manifest["tables"].items():
            manifest_rows.append({
                "Table": table_name,
                "Records": details["row_count"],
                "CSV": details["csv_file"],
                "JSON": details["json_file"]
            })

        st.dataframe(
            pd.DataFrame(manifest_rows),
            width="stretch",
            hide_index=True
        )

        st.info(
            "CSV and JSON files and the SQLite SQL dump are available "
            "inside the data/exports folder."
        )

    else:
        st.warning("Export manifest not found. Run the export script first.")


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "YottaFlex AI Technologies | Synthetic Data Demonstration | "
    "For evaluation purposes only"
)
