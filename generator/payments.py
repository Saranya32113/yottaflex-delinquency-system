
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from config import RANDOM_SEED
from database.models import (
    Installment,
    Payment,
    PaymentAllocation
)


SNAPSHOT_DATE = date(2026, 11, 13)


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def generate_payments(session: Session):
    print("Generating payment records...")

    existing_payments = session.query(Payment).count()
    existing_allocations = session.query(PaymentAllocation).count()

    if existing_payments or existing_allocations:
        print("Payment data already exists. Skipping generation.")
        print("Payments:", existing_payments)
        print("Allocations:", existing_allocations)
        return

    rng = random.Random(RANDOM_SEED + 100)

    installments = (
        session.query(Installment)
        .order_by(Installment.installment_id)
        .all()
    )

    payments = []
    allocations = []
    payment_number = 0

    for index, installment in enumerate(installments, start=1):

        amount_due = money(installment.amount_due)
        amount_paid = Decimal("0.00")

        if installment.due_date <= SNAPSHOT_DATE:

            outcome = rng.random()

            # 58% fully paid
            # 20% partially paid
            # 22% unpaid
            if outcome < 0.58:
                amount_paid = amount_due

            elif outcome < 0.78:
                partial_percentage = Decimal(
                    str(round(rng.uniform(0.20, 0.80), 2))
                )
                amount_paid = money(
                    amount_due * partial_percentage
                )

                if amount_paid >= amount_due:
                    amount_paid = money(amount_due - Decimal("0.01"))

            if amount_paid > 0:

                days_after_due = (
                    SNAPSHOT_DATE - installment.due_date
                ).days

                payment_date = installment.due_date + timedelta(
                    days=rng.randint(0, days_after_due)
                )

                payment_number += 1
                payment_id = f"PAY-2026-{payment_number:07d}"

                payment = Payment(
                    payment_id=payment_id,
                    loan_id=installment.loan_id,
                    payment_date=payment_date,
                    amount=amount_paid,
                    payment_method=rng.choice([
                        "UPI",
                        "bank_transfer",
                        "auto_debit",
                        "cash"
                    ]),
                    payment_status="received"
                )

                allocation = PaymentAllocation(
                    allocation_id=f"ALLOC-2026-{payment_number:07d}",
                    payment_id=payment_id,
                    installment_id=installment.installment_id,
                    allocated_amount=amount_paid
                )

                payments.append(payment)
                allocations.append(allocation)

        # Store the installment's paid amount
        installment.amount_paid = amount_paid

        if amount_paid >= amount_due:
            installment.status = "paid"

        elif amount_paid > 0:
            installment.status = "partially_paid"

        elif installment.due_date < SNAPSHOT_DATE:
            installment.status = "overdue"

        else:
            installment.status = "scheduled"

        if index % 5000 == 0:
            print(f"Processed {index} installments")

    # Add a small number of failed/reversed payment attempts.
    # These do not reduce installment balances.
    for installment in installments:

        if rng.random() < 0.02:
            payment_number += 1

            payment_date = min(
                installment.due_date,
                SNAPSHOT_DATE
            )

            failed_payment = Payment(
                payment_id=f"PAY-2026-{payment_number:07d}",
                loan_id=installment.loan_id,
                payment_date=payment_date,
                amount=money(installment.amount_due),
                payment_method=rng.choice([
                    "UPI",
                    "bank_transfer",
                    "auto_debit"
                ]),
                payment_status="failed"
            )

            payments.append(failed_payment)

    try:
        session.add_all(payments)
        session.add_all(allocations)
        session.commit()

        print("\nPayment generation completed!")
        print("Total payment records:", len(payments))
        print("Received payments:", sum(
            1 for p in payments
            if p.payment_status == "received"
        ))
        print("Failed payments:", sum(
            1 for p in payments
            if p.payment_status == "failed"
        ))
        print("Payment allocations:", len(allocations))

    except Exception:
        session.rollback()
        raise


if __name__ == "__main__":
    from database.database import get_session

    db = get_session()

    try:
        generate_payments(db)
    finally:
        db.close()
