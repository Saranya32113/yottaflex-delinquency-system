
import random
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from database.models import (
    CollectionCase,
    ContactPreference,
    Loan,
    Account,
    Customer,
    DelinquencySnapshot,
    PromiseToPay
)

RANDOM_SEED = 20261022
SNAPSHOT_DATE = date(2026, 11, 13)


def money(value):
    return Decimal(str(value)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )


def generate_promises(session):

    print("Generating Promise-to-Pay records...")

    existing = session.query(PromiseToPay).count()

    if existing > 0:
        print("Promise records already exist.")
        print("Existing records:", existing)
        return

    rng = random.Random(RANDOM_SEED + 600)

    records = (
        session.query(
            CollectionCase,
            Loan,
            DelinquencySnapshot
        )
        .join(Loan, CollectionCase.loan_id == Loan.loan_id)
        .join(
            DelinquencySnapshot,
            DelinquencySnapshot.snapshot_id
            == CollectionCase.snapshot_id
        )
        .filter(
            CollectionCase.case_status == "open",
            DelinquencySnapshot.disputed.is_(False),
            DelinquencySnapshot.hardship_flag.is_(False)
        )
        .all()
    )

    promises = []

    eligible_records = [
        record for record in records
        if rng.random() < 0.25
    ]

    for index, (case, loan, snapshot) in enumerate(
        eligible_records, start=1
    ):

        arrears = money(snapshot.total_arrears)

        if arrears <= 0:
            continue

        # Promise amounts are bounded by arrears
        percentage = Decimal(
            str(round(rng.uniform(0.30, 1.00), 2))
        )

        promised_amount = money(arrears * percentage)

        promised_date = SNAPSHOT_DATE + timedelta(
            days=rng.randint(1, 30)
        )

        # Assign a status based on the promise date
        if promised_date < SNAPSHOT_DATE:
            promise_status = "missed"
        elif promised_date == SNAPSHOT_DATE:
            promise_status = "fulfilled"
        else:
            promise_status = "pending"

        promise = PromiseToPay(
            promise_id=f"PTP-2026-{index:07d}",
            case_id=case.case_id,
            attempt_id=None,
            promised_amount=promised_amount,
            promised_date=promised_date,
            promise_status=promise_status
        )

        promises.append(promise)

    try:
        session.add_all(promises)
        session.commit()

        print("\nPromise generation completed!")
        print("Total promises:", len(promises))

        for status in [
            "pending",
            "fulfilled",
            "missed",
            "cancelled",
            "invalid"
        ]:
            count = sum(
                1 for promise in promises
                if promise.promise_status == status
            )

            print(f"{status.capitalize()}: {count}")

    except Exception:
        session.rollback()
        raise


if __name__ == "__main__":

    from database.database import get_session

    db = get_session()

    try:
        generate_promises(db)
    finally:
        db.close()
