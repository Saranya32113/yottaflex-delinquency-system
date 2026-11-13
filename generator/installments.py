
from datetime import date, timedelta

from sqlalchemy.orm import Session

from config import TOTAL_LOANS
from database.models import Loan, Installment


def generate_installments(session: Session):
    print("Generating installment records...")

    existing_count = session.query(Installment).count()

    if existing_count > 0:
        print("Installment records already exist.")
        print(f"Existing records: {existing_count}")
        print("Skipping generation to prevent duplicates.")
        return

    loans = session.query(Loan).order_by(Loan.loan_id).all()

    if len(loans) != TOTAL_LOANS:
        raise ValueError(
            f"Expected {TOTAL_LOANS} loans, found {len(loans)}"
        )

    snapshot_date = date(2026, 11, 13)
    installments = []

    for index, loan in enumerate(loans, start=1):

        # Calculate the number of completed loan months
        elapsed_months = (
            (snapshot_date.year - loan.start_date.year) * 12
            + snapshot_date.month - loan.start_date.month
        )

        latest_number = max(1, elapsed_months)

        # Generate the three most recent scheduled installments
        for offset in range(2, -1, -1):

            installment_number = latest_number - offset

            if installment_number < 1:
                continue

            due_date = loan.start_date + timedelta(
                days=30 * installment_number
            )

            monthly_principal = (
                float(loan.principal_amount) / loan.term_months
            )

            monthly_interest = (
                float(loan.principal_amount)
                * (float(loan.annual_interest_rate) / 100)
                / 12
            )

            amount_due = round(
                monthly_principal + monthly_interest, 2
            )

            status = (
                "overdue"
                if due_date < snapshot_date
                else "scheduled"
            )

            installment = Installment(
                installment_id=(
                    f"INS-{loan.loan_id}-{installment_number:03d}"
                ),
                loan_id=loan.loan_id,
                installment_number=installment_number,
                due_date=due_date,
                amount_due=amount_due,
                amount_paid=0,
                status=status
            )

            installments.append(installment)

        if index % 1000 == 0:
            print(f"Processed {index} loans")

    session.add_all(installments)
    session.commit()

    print("\nInstallment generation completed!")
    print("Total installments:", len(installments))


if __name__ == "__main__":
    from database.database import get_session

    db = get_session()

    try:
        generate_installments(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
