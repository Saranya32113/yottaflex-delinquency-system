
import random
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

from database.models import (
    Loan,
    Installment,
    Payment,
    DelinquencySnapshot
)

SNAPSHOT_DATE = date(2026, 11, 13)
RANDOM_SEED = 20261022


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def generate_delinquency_snapshots(session):

    print("Generating delinquency snapshots...")

    existing = session.query(DelinquencySnapshot).count()

    if existing > 0:
        print("Delinquency snapshots already exist.")
        print("Existing records:", existing)
        print("Skipping generation to prevent duplicates.")
        return

    rng = random.Random(RANDOM_SEED + 400)

    loans = session.query(Loan).order_by(Loan.loan_id).all()
    installments = session.query(Installment).all()

    received_payments = session.query(Payment).filter(
        Payment.payment_status == "received"
    ).all()

    if not loans:
        raise ValueError("No loans found.")

    # Group installments by loan
    installments_by_loan = defaultdict(list)

    for installment in installments:
        installments_by_loan[installment.loan_id].append(
            installment
        )

    # Sum received payments by loan
    payments_by_loan = defaultdict(Decimal)

    for payment in received_payments:
        payments_by_loan[payment.loan_id] += money(payment.amount)

    snapshots = []

    for index, loan in enumerate(loans, start=1):

        loan_installments = installments_by_loan[loan.loan_id]

        overdue_unpaid = []

        for installment in loan_installments:

            remaining = money(
                Decimal(str(installment.amount_due))
                - Decimal(str(installment.amount_paid))
            )

            if (
                installment.due_date < SNAPSHOT_DATE
                and remaining > 0
            ):
                overdue_unpaid.append(
                    (installment, remaining)
                )

        # Calculate total arrears
        total_arrears = money(
            sum(
                (remaining for _, remaining in overdue_unpaid),
                Decimal("0.00")
            )
        )

        # Calculate DPD from the oldest unpaid overdue installment
        if overdue_unpaid:
            oldest_due_date = min(
                installment.due_date
                for installment, _ in overdue_unpaid
            )

            days_past_due = (
                SNAPSHOT_DATE - oldest_due_date
            ).days
        else:
            days_past_due = 0

        # Calculate outstanding principal
        total_received = payments_by_loan[loan.loan_id]

        outstanding_balance = max(
            Decimal("0.00"),
            money(
                Decimal(str(loan.principal_amount))
                - total_received
            )
        )

        # Calculate risk category
        principal = Decimal(str(loan.principal_amount))

        arrears_ratio = (
            total_arrears / principal
            if principal > 0
            else Decimal("0")
        )

        if (
            days_past_due >= 90
            or arrears_ratio >= Decimal("0.20")
        ):
            risk_category = "high"

        elif (
            days_past_due >= 30
            or arrears_ratio >= Decimal("0.05")
        ):
            risk_category = "medium"

        else:
            risk_category = "low"

        # Synthetic dispute and hardship indicators
        disputed = rng.random() < 0.03
        hardship_flag = rng.random() < 0.05

        snapshot = DelinquencySnapshot(
            snapshot_id=f"SNAP-2026-{index:07d}",
            loan_id=loan.loan_id,
            snapshot_date=SNAPSHOT_DATE,
            days_past_due=days_past_due,
            total_arrears=total_arrears,
            outstanding_balance=outstanding_balance,
            risk_category=risk_category,
            disputed=disputed,
            hardship_flag=hardship_flag
        )

        snapshots.append(snapshot)

        if index % 1000 == 0:
            print(f"Processed {index} loans")

    try:
        session.add_all(snapshots)
        session.commit()

        print("\nDelinquency snapshot generation completed!")
        print("Total snapshots:", len(snapshots))

    except Exception:
        session.rollback()
        raise


if __name__ == "__main__":
    from database.database import get_session

    db = get_session()

    try:
        generate_delinquency_snapshots(db)
    finally:
        db.close()
