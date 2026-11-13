
import random
from datetime import date, datetime, timedelta, time
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

from database.database import get_session
from database.models import (
    PromiseToPay,
    CollectionCase,
    Loan,
    Account,
    ContactPreference,
    ContactAttempt,
    Payment,
    PromisePaymentAllocation
)

from config import RANDOM_SEED

SNAPSHOT_DATE = date(2026, 11, 13)


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def resolve_promises(session):

    print("Processing Promise-to-Pay lifecycle...")

    promises = session.query(PromiseToPay).order_by(
        PromiseToPay.promise_id
    ).all()

    if not promises:
        print("No promises found.")
        return

    existing_attempts = session.query(ContactAttempt).count()
    existing_links = session.query(
        PromisePaymentAllocation
    ).count()

    if existing_attempts or existing_links:
        print("Promise lifecycle records already exist.")
        print("Contact attempts:", existing_attempts)
        print("Promise payment links:", existing_links)
        print("Skipping to prevent duplicates.")
        return

    rng = random.Random(RANDOM_SEED + 700)

    case_ids = [p.case_id for p in promises]

    cases = session.query(CollectionCase).filter(
        CollectionCase.case_id.in_(case_ids)
    ).all()

    case_map = {case.case_id: case for case in cases}

    loan_ids = list({
        case.loan_id for case in cases
    })

    loans = session.query(Loan).filter(
        Loan.loan_id.in_(loan_ids)
    ).all()

    loan_map = {loan.loan_id: loan for loan in loans}

    account_ids = list({
        loan.account_id for loan in loans
    })

    accounts = session.query(Account).filter(
        Account.account_id.in_(account_ids)
    ).all()

    account_map = {
        account.account_id: account for account in accounts
    }

    customer_ids = list({
        account.customer_id for account in accounts
    })

    preferences = session.query(ContactPreference).filter(
        ContactPreference.customer_id.in_(customer_ids)
    ).all()

    preference_map = {
        preference.customer_id: preference
        for preference in preferences
    }

    received_payments = session.query(Payment).filter(
        Payment.payment_status == "received",
        Payment.loan_id.in_(loan_ids)
    ).order_by(
        Payment.payment_date,
        Payment.payment_id
    ).all()

    payments_by_loan = defaultdict(list)

    for payment in received_payments:
        payments_by_loan[payment.loan_id].append(payment)

    # Count contact attempts separately for each case.
    existing_counts = defaultdict(int)

    attempts = []
    payment_links = []

    status_counts = {
        "pending": 0,
        "fulfilled": 0,
        "missed": 0
    }

    skipped_restricted = 0

    for index, promise in enumerate(promises, start=1):

        case = case_map.get(promise.case_id)

        if case is None:
            raise ValueError(
                f"Collection case missing: {promise.case_id}"
            )

        loan = loan_map.get(case.loan_id)

        if loan is None:
            raise ValueError(
                f"Loan missing for promise: {promise.promise_id}"
            )

        account = account_map.get(loan.account_id)

        if account is None:
            raise ValueError(
                f"Account missing for loan: {loan.loan_id}"
            )

        preference = preference_map.get(account.customer_id)

        if preference is None or preference.do_not_contact:
            promise.promise_status = "pending"
            skipped_restricted += 1
            status_counts["pending"] += 1
            continue

        days_before_snapshot = rng.randint(1, 45)

        attempted_date = (
            SNAPSHOT_DATE
            - timedelta(days=days_before_snapshot)
        )

        attempted_at = datetime.combine(
            attempted_date,
            time(10, 0)
        )

        # Generate a case-specific immutable contact ID.
        existing_counts[case.case_id] += 1

        attempt_number = existing_counts[case.case_id]

        attempt_id = (
            f"CTP-{case.case_id}-{attempt_number:03d}"
        )

        attempt = ContactAttempt(
            attempt_id=attempt_id,
            case_id=case.case_id,
            preference_id=preference.preference_id,
            channel=preference.channel,
            attempted_at=attempted_at,
            outcome="promise",
            blocked=False,
            block_reason=None
        )

        attempts.append(attempt)

        promised_date = attempted_date + timedelta(
            days=rng.randint(7, 21)
        )

        promise.attempt_id = attempt_id
        promise.promised_date = promised_date

        if promised_date > SNAPSHOT_DATE:
            promise.promise_status = "pending"
            status_counts["pending"] += 1
            continue

        matching_payments = [
            payment
            for payment in payments_by_loan[loan.loan_id]
            if (
                attempted_date < payment.payment_date
                <= promised_date
            )
        ]

        remaining = money(promise.promised_amount)

        for payment in matching_payments:

            if remaining <= Decimal("0.00"):
                break

            available = money(payment.amount)
            allocated = min(available, remaining)

            if allocated > 0:

                link = PromisePaymentAllocation(
                    promise_id=promise.promise_id,
                    payment_id=payment.payment_id,
                    allocated_amount=allocated
                )

                payment_links.append(link)
                remaining = money(remaining - allocated)

        if remaining <= Decimal("0.00"):
            promise.promise_status = "fulfilled"
            status_counts["fulfilled"] += 1

        else:
            promise.promise_status = "missed"
            status_counts["missed"] += 1

        if index % 250 == 0:
            print(f"Processed {index} promises")

    try:
        session.add_all(attempts)
        session.add_all(payment_links)
        session.commit()

        print("\nPROMISE LIFECYCLE PROCESSING COMPLETED")
        print("=" * 45)

        print("Total promises:", len(promises))
        print("Contact attempts created:", len(attempts))
        print("Payment links created:", len(payment_links))

        print("\nPROMISE STATUS SUMMARY")

        for status, count in status_counts.items():
            print(f"{status.capitalize()}: {count}")

        print(
            "Restricted customers skipped:",
            skipped_restricted
        )

    except Exception:
        session.rollback()
        raise


if __name__ == "__main__":

    db = get_session()

    try:
        resolve_promises(db)
    finally:
        db.close()
