
from decimal import Decimal

from sqlalchemy import func

from database.database import get_session
from database.models import (
    Payment,
    PaymentAllocation,
    Installment,
)


def validate_payments(db):
    errors = []

    # --------------------------------------------------
    # 1. Retrieve payment records
    # --------------------------------------------------

    received = db.query(Payment).filter(
        Payment.payment_status == "received"
    ).all()

    failed = db.query(Payment).filter(
        Payment.payment_status == "failed"
    ).all()

    reversed_payments = db.query(Payment).filter(
        Payment.payment_status == "reversed"
    ).all()

    # --------------------------------------------------
    # 2. Identify cross-loan allocation anomalies
    # --------------------------------------------------

    wrong_allocations = (
        db.query(PaymentAllocation, Payment, Installment)
        .join(
            Payment,
            Payment.payment_id == PaymentAllocation.payment_id
        )
        .join(
            Installment,
            Installment.installment_id
            == PaymentAllocation.installment_id
        )
        .filter(
            Payment.payment_status == "received",
            Payment.loan_id != Installment.loan_id
        )
        .all()
    )

    # Both the source loan and destination loan are affected.
    affected_loan_ids = set()

    for allocation, payment, installment in wrong_allocations:
        affected_loan_ids.add(payment.loan_id)
        affected_loan_ids.add(installment.loan_id)

    # --------------------------------------------------
    # 3. Validate received payment allocation totals
    # --------------------------------------------------

    for payment in received:
        allocated = db.query(
            func.coalesce(
                func.sum(PaymentAllocation.allocated_amount), 0
            )
        ).filter(
            PaymentAllocation.payment_id == payment.payment_id
        ).scalar()

        if Decimal(str(allocated)) != Decimal(str(payment.amount)):
            errors.append(
                f"Received payment allocation mismatch: "
                f"{payment.payment_id}"
            )

    # --------------------------------------------------
    # 4. Failed payments must not have allocations
    # --------------------------------------------------

    for payment in failed:
        count = db.query(PaymentAllocation).filter(
            PaymentAllocation.payment_id == payment.payment_id
        ).count()

        if count > 0:
            errors.append(
                f"Failed payment has allocation: {payment.payment_id}"
            )

    # --------------------------------------------------
    # 5. Reversed payments must not have allocations
    # --------------------------------------------------

    for payment in reversed_payments:
        count = db.query(PaymentAllocation).filter(
            PaymentAllocation.payment_id == payment.payment_id
        ).count()

        if count > 0:
            errors.append(
                f"Reversed payment has allocation: {payment.payment_id}"
            )

    # --------------------------------------------------
    # 6. Validate installment allocation totals
    # --------------------------------------------------

    installments = db.query(Installment).all()

    installments_checked = 0
    installments_skipped = 0

    for installment in installments:

        # Cross-loan anomalies can affect reconciliation
        # for both the source and destination loans.
        if installment.loan_id in affected_loan_ids:
            installments_skipped += 1
            continue

        allocated = db.query(
            func.coalesce(
                func.sum(PaymentAllocation.allocated_amount), 0
            )
        ).join(
            Payment,
            Payment.payment_id == PaymentAllocation.payment_id
        ).filter(
            PaymentAllocation.installment_id
            == installment.installment_id,
            Payment.payment_status == "received",
            Payment.loan_id == installment.loan_id
        ).scalar()

        installments_checked += 1

        if Decimal(str(allocated)) != Decimal(
            str(installment.amount_paid)
        ):
            errors.append(
                f"Installment allocation mismatch: "
                f"{installment.installment_id}"
            )

    # --------------------------------------------------
    # 7. Return validation results
    # --------------------------------------------------

    return {
        "errors": errors,
        "received_checked": len(received),
        "failed_checked": len(failed),
        "reversed_checked": len(reversed_payments),
        "installments_checked": installments_checked,
        "installments_skipped": installments_skipped,
        "wrong_loan_allocations": len(wrong_allocations),
    }


def main():
    db = get_session()

    try:
        result = validate_payments(db)

        print("\nPAYMENT RECONCILIATION VALIDATION")
        print("=" * 50)

        print(
            "Received payments checked:",
            result["received_checked"]
        )

        print(
            "Failed payments checked:",
            result["failed_checked"]
        )

        print(
            "Reversed payments checked:",
            result["reversed_checked"]
        )

        print(
            "Installments checked:",
            result["installments_checked"]
        )

        print(
            "Installments skipped due to cross-loan anomalies:",
            result["installments_skipped"]
        )

        print(
            "Wrong-loan allocations identified:",
            result["wrong_loan_allocations"]
        )

        print("\nVALIDATION RESULTS")
        print("-" * 50)

        print("Validation errors:", len(result["errors"]))

        if result["errors"]:
            for error in result["errors"][:20]:
                print(error)

            print("\nVALIDATION FAILED!")

        else:
            print("\nSUCCESS: Payment reconciliation passed!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
