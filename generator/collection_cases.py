
from datetime import datetime, date

from database.models import (
    Loan,
    DelinquencySnapshot,
    CollectionCase
)

SNAPSHOT_DATE = date(2026, 11, 13)


def calculate_priority_score(loan, snapshot):

    # DPD score: maximum 40
    dpd_score = min(
        snapshot.days_past_due / 180 * 40,
        40
    )

    # Arrears ratio score: maximum 25
    principal = float(loan.principal_amount)

    arrears_ratio = (
        float(snapshot.total_arrears) / principal
        if principal > 0 else 0
    )

    arrears_score = min(arrears_ratio / 0.30 * 25, 25)

    # Outstanding balance score: maximum 15
    outstanding_ratio = (
        float(snapshot.outstanding_balance) / principal
        if principal > 0 else 0
    )

    balance_score = min(outstanding_ratio * 15, 15)

    # Risk category score: maximum 20
    risk_scores = {
        "low": 5,
        "medium": 12,
        "high": 20
    }

    risk_score = risk_scores.get(
        snapshot.risk_category, 0
    )

    total_score = (
        dpd_score
        + arrears_score
        + balance_score
        + risk_score
    )

    return round(min(total_score, 100), 2)


def generate_collection_cases(session):

    print("Generating collection cases...")

    existing = session.query(CollectionCase).count()

    if existing > 0:
        print("Collection cases already exist.")
        print("Existing records:", existing)
        print("Skipping generation.")
        return

    loans = session.query(Loan).all()

    snapshots = session.query(
        DelinquencySnapshot
    ).all()

    snapshot_map = {
        snapshot.loan_id: snapshot
        for snapshot in snapshots
    }

    cases = []

    for index, loan in enumerate(loans, start=1):

        snapshot = snapshot_map.get(loan.loan_id)

        if snapshot is None:
            continue

        if float(snapshot.total_arrears) <= 0:
            continue

        score = calculate_priority_score(
            loan,
            snapshot
        )

        if score >= 70:
            priority_band = "high"
        elif score >= 40:
            priority_band = "medium"
        else:
            priority_band = "low"

        # Disputed and hardship cases require special handling
        if snapshot.disputed:
            case_status = "review"
            issue_type = "disputed_debt"

        elif snapshot.hardship_flag:
            case_status = "on_hold"
            issue_type = "hardship"

        else:
            case_status = "open"
            issue_type = "overdue_installment"

        case = CollectionCase(
            case_id=f"CASE-2026-{index:07d}",
            loan_id=loan.loan_id,
            snapshot_id=snapshot.snapshot_id,
            priority_score=score,
            priority_band=priority_band,
            case_status=case_status,
            opened_at=datetime(2026, 11, 13, 9, 0, 0),
            issue_type=issue_type
        )

        cases.append(case)

        if index % 1000 == 0:
            print(f"Processed {index} loans")

    try:
        session.add_all(cases)
        session.commit()

        print("\nCollection case generation completed!")
        print("Total cases:", len(cases))

    except Exception:
        session.rollback()
        raise


if __name__ == "__main__":

    from database.database import get_session

    db = get_session()

    try:
        generate_collection_cases(db)
    finally:
        db.close()
