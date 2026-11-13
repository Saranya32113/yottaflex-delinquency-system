
import random
from datetime import date
from sqlalchemy.orm import Session

from config import RANDOM_SEED
from database.models import Installment, Payment


SNAPSHOT_DATE = date(2026, 11, 13)


def generate_reversed_payments(session: Session):

    print("Generating reversed payment records...")

    existing = session.query(Payment).filter(
        Payment.payment_status == "reversed"
    ).count()

    if existing > 0:
        print("Reversed payments already exist.")
        print("Existing reversed payments:", existing)
        return

    rng = random.Random(RANDOM_SEED + 300)

    installments = (
        session.query(Installment)
        .filter(Installment.due_date <= SNAPSHOT_DATE)
        .order_by(Installment.installment_id)
        .all()
    )

    if not installments:
        print("No eligible installments found.")
        return

    reversed_count = max(1, round(len(installments) * 0.01))

    selected = rng.sample(
        installments,
        min(reversed_count, len(installments))
    )

    existing_count = session.query(Payment).count()
    payments = []

    for number, installment in enumerate(selected, start=1):

        payment = Payment(
            payment_id=f"PAY-2026-{existing_count + number:07d}",
            loan_id=installment.loan_id,
            payment_date=min(installment.due_date, SNAPSHOT_DATE),
            amount=installment.amount_due,
            payment_method=rng.choice([
                "UPI",
                "bank_transfer",
                "auto_debit"
            ]),
            payment_status="reversed"
        )

        payments.append(payment)

    try:
        session.add_all(payments)
        session.commit()

        print("Reversed payment generation completed!")
        print("Reversed payments created:", len(payments))

    except Exception:
        session.rollback()
        raise


if __name__ == "__main__":
    from database.database import get_session

    db = get_session()

    try:
        generate_reversed_payments(db)
    finally:
        db.close()
