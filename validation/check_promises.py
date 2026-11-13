
import json
from decimal import Decimal

from config import GROUND_TRUTH_DIR
from database.database import get_session
from database.models import (
    PromiseToPay,
    ContactAttempt,
    CollectionCase,
    Loan,
    Payment,
    PromisePaymentAllocation,
    DelinquencySnapshot,
)


def money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def main():
    session = get_session()

    errors = []
    expected_anomalies = []
    checked = 0

    try:
        promises = session.query(PromiseToPay).all()

        attempts = {
            item.attempt_id: item
            for item in session.query(ContactAttempt).all()
        }

        cases = {
            item.case_id: item
            for item in session.query(CollectionCase).all()
        }

        loans = {
            item.loan_id: item
            for item in session.query(Loan).all()
        }

        payments = {
            item.payment_id: item
            for item in session.query(Payment).all()
        }

        snapshots = {
            item.snapshot_id: item
            for item in session.query(DelinquencySnapshot).all()
        }

        links = session.query(PromisePaymentAllocation).all()
        links_by_promise = {}

        for link in links:
            links_by_promise.setdefault(
                link.promise_id, []
            ).append(link)

        # Load the official synthetic ground truth.
        ground_truth_path = (
            GROUND_TRUTH_DIR / "ground_truth.json"
        )

        with open(ground_truth_path, "r", encoding="utf-8") as file:
            ground_truth = json.load(file)

        expected_promise_anomalies = {
            item["entity_id"]
            for item in ground_truth
            if item["anomaly_type"] == "promise_amount_exceeds_arrears"
        }

        for promise in promises:
            checked += 1

            promised_amount = money(promise.promised_amount)
            linked_total = Decimal("0.00")

            case = cases.get(promise.case_id)

            if case is None:
                errors.append(
                    f"{promise.promise_id}: collection case not found"
                )
                continue

            loan = loans.get(case.loan_id)

            if loan is None:
                errors.append(
                    f"{promise.promise_id}: loan not found"
                )
                continue

            # Check contact attempt.
            if promise.attempt_id:
                attempt = attempts.get(promise.attempt_id)

                if attempt is None:
                    errors.append(
                        f"{promise.promise_id}: contact attempt not found"
                    )
                else:
                    if attempt.case_id != promise.case_id:
                        errors.append(
                            f"{promise.promise_id}: attempt belongs to another case"
                        )

                    if attempt.outcome != "promise":
                        errors.append(
                            f"{promise.promise_id}: incorrect contact outcome"
                        )

            # Check promise amount against snapshot arrears.
            if case.snapshot_id:
                snapshot = snapshots.get(case.snapshot_id)

                if snapshot is None:
                    errors.append(
                        f"{promise.promise_id}: snapshot not found"
                    )

                elif promised_amount > money(snapshot.total_arrears):
                    message = (
                        f"{promise.promise_id}: "
                        "promised amount exceeds arrears"
                    )

                    if promise.promise_id in expected_promise_anomalies:
                        expected_anomalies.append(message)
                    else:
                        errors.append(message)

            # Check linked payments.
            for link in links_by_promise.get(promise.promise_id, []):
                payment = payments.get(link.payment_id)

                if payment is None:
                    errors.append(
                        f"{promise.promise_id}: linked payment not found"
                    )
                    continue

                if payment.loan_id != loan.loan_id:
                    errors.append(
                        f"{promise.promise_id}: payment belongs to another loan"
                    )

                if payment.payment_status != "received":
                    errors.append(
                        f"{promise.promise_id}: linked payment is not received"
                    )

                amount = money(link.allocated_amount)

                if amount <= 0:
                    errors.append(
                        f"{promise.promise_id}: invalid payment link amount"
                    )

                linked_total += amount

            if linked_total > promised_amount:
                errors.append(
                    f"{promise.promise_id}: linked amount exceeds promise"
                )

            if promise.promise_status == "fulfilled":
                if linked_total < promised_amount:
                    errors.append(
                        f"{promise.promise_id}: fulfilled without full payment"
                    )

            elif promise.promise_status == "missed":
                if linked_total >= promised_amount:
                    errors.append(
                        f"{promise.promise_id}: missed despite full payment"
                    )

        print("\nPROMISE LIFECYCLE VALIDATION")
        print("=" * 50)

        print("Promises checked:", checked)
        print("Contact attempts found:", len(attempts))
        print("Promise-payment links checked:", len(links))

        print(
            "Expected injected promise anomalies:",
            len(expected_anomalies)
        )

        for anomaly in expected_anomalies:
            print("[EXPECTED ANOMALY]", anomaly)

        print("\nUnexpected validation errors:", len(errors))

        if errors:
            print("\nVALIDATION ERRORS:")

            for error in errors[:50]:
                print("-", error)

            print("\nVALIDATION FAILED!")

        else:
            print(
                "\nSUCCESS: No unexpected promise lifecycle errors found!"
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()
