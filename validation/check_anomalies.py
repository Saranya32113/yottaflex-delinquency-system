
import json

from config import GROUND_TRUTH_DIR
from database.database import get_session
from database.models import (
    CollectionCase,
    ContactAttempt,
    ContactPreference,
    DelinquencySnapshot,
    Installment,
    Loan,
    Payment,
    PaymentAllocation,
    PromiseToPay,
)


def detect_anomalies(session):
    detected = []

    # ANOMALY 1: Paid-off loan in an open collection case
    results = (
        session.query(CollectionCase, Loan)
        .join(Loan, CollectionCase.loan_id == Loan.loan_id)
        .filter(
            CollectionCase.case_status == "open",
            Loan.loan_status == "paid_off"
        )
        .all()
    )

    for case, loan in results:
        detected.append({
            "anomaly_type": "paid_off_loan_in_collection",
            "entity_id": case.case_id,
            "message": "Paid-off loan remains in an open collection case."
        })

    # ANOMALY 2: Contact outside permitted hours
    results = (
        session.query(ContactAttempt, ContactPreference)
        .join(
            ContactPreference,
            ContactAttempt.preference_id
            == ContactPreference.preference_id
        )
        .filter(ContactAttempt.attempted_at.isnot(None))
        .all()
    )

    for attempt, preference in results:
        local_time = attempt.attempted_at.time()
        start_time = preference.permitted_start
        end_time = preference.permitted_end

        if not (start_time <= local_time <= end_time):
            detected.append({
                "anomaly_type": "contact_outside_allowed_window",
                "entity_id": attempt.attempt_id,
                "message": "Contact attempt falls outside the permitted time window."
            })

    # ANOMALY 3: Payment allocated to an installment from another loan
    results = (
        session.query(PaymentAllocation, Payment, Installment)
        .join(
            Payment,
            PaymentAllocation.payment_id == Payment.payment_id
        )
        .join(
            Installment,
            PaymentAllocation.installment_id == Installment.installment_id
        )
        .filter(Payment.loan_id != Installment.loan_id)
        .all()
    )

    for allocation, payment, installment in results:
        detected.append({
            "anomaly_type": "payment_allocated_to_wrong_installment",
            "entity_id": allocation.allocation_id,
            "message": "Payment and installment belong to different loans."
        })

    # ANOMALY 4: Promise amount exceeds snapshot arrears
    results = (
        session.query(PromiseToPay, DelinquencySnapshot)
        .join(
            CollectionCase,
            PromiseToPay.case_id == CollectionCase.case_id
        )
        .join(
            DelinquencySnapshot,
            CollectionCase.snapshot_id
            == DelinquencySnapshot.snapshot_id
        )
        .filter(
            PromiseToPay.promised_amount
            > DelinquencySnapshot.total_arrears
        )
        .all()
    )

    for promise, snapshot in results:
        detected.append({
            "anomaly_type": "promise_amount_exceeds_arrears",
            "entity_id": promise.promise_id,
            "message": "Promise amount exceeds recorded arrears."
        })

    # ANOMALY 5: Disputed debt treated as an open collection case
    results = (
        session.query(CollectionCase, DelinquencySnapshot)
        .join(
            DelinquencySnapshot,
            CollectionCase.snapshot_id
            == DelinquencySnapshot.snapshot_id
        )
        .filter(
            CollectionCase.case_status == "open",
            DelinquencySnapshot.disputed.is_(True)
        )
        .all()
    )

    for case, snapshot in results:
        detected.append({
            "anomaly_type": "disputed_debt_treated_as_confirmed",
            "entity_id": case.case_id,
            "message": "Disputed debt is being treated as an open collection case."
        })

    return detected


def main():
    session = get_session()

    try:
        detected = detect_anomalies(session)

        ground_truth_path = GROUND_TRUTH_DIR / "ground_truth.json"

        with open(ground_truth_path, "r", encoding="utf-8") as file:
            ground_truth = json.load(file)

        expected = {
            (item["anomaly_type"], item["entity_id"])
            for item in ground_truth
        }

        found = {
            (item["anomaly_type"], item["entity_id"])
            for item in detected
        }

        print("\nYOTTAFLEX ANOMALY DETECTION REPORT")
        print("=" * 55)

        for item in detected:
            print(
                "[DETECTED]",
                item["anomaly_type"],
                "|",
                item["entity_id"]
            )

        matched = expected.intersection(found)
        missing = expected - found
        unexpected = found - expected

        print("\nSUMMARY")
        print("-" * 55)
        print("Ground-truth anomalies:", len(expected))
        print("Detected anomaly records:", len(detected))
        print("Expected anomalies detected:", len(matched))
        print("Expected anomalies missed:", len(missing))
        print("Additional detections:", len(unexpected))

        if missing:
            print("\nMISSING EXPECTED ANOMALIES:")
            for anomaly in sorted(missing):
                print("-", anomaly)

        if unexpected:
            print("\nADDITIONAL DETECTIONS TO REVIEW:")
            for anomaly in sorted(unexpected):
                print("-", anomaly)

        if not missing:
            print("\nSUCCESS: All five ground-truth anomalies were detected.")
        else:
            print("\nWARNING: Some ground-truth anomalies were not detected.")

    finally:
        session.close()


if __name__ == "__main__":
    main()
