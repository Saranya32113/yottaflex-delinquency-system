
import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from database.database import get_session
from database.models import (
    Account,
    AuditEvent,
    CollectionCase,
    ContactAttempt,
    DelinquencySnapshot,
    Installment,
    Loan,
    Payment,
    PaymentAllocation,
    PromisePaymentAllocation,
    PromiseToPay,
)
from config import GROUND_TRUTH_DIR


def inject_anomalies():
    session = get_session()
    ground_truth = []
    now = datetime.utcnow()

    try:
        # Prevent accidental duplicate injection.
        existing = session.query(AuditEvent).filter(
            AuditEvent.event_type == "anomaly_injected"
        ).count()

        if existing:
            print("Anomalies have already been injected.")
            print("Skipping to prevent duplicate modifications.")
            return

        # -------------------------------------------------
        # ANOMALY 1: Paid-off loan remains in collection
        # -------------------------------------------------
        case = session.query(CollectionCase).filter(
            CollectionCase.case_status == "open"
        ).first()

        if not case:
            raise ValueError("No open collection case found.")

        loan = session.query(Loan).filter(
            Loan.loan_id == case.loan_id
        ).first()

        account = session.query(Account).filter(
            Account.account_id == loan.account_id
        ).first()

        old_loan_status = loan.loan_status
        old_account_status = account.account_status

        loan.loan_status = "paid_off"
        account.account_status = "closed"

        if case.snapshot_id:
            snapshot = session.query(DelinquencySnapshot).filter(
                DelinquencySnapshot.snapshot_id == case.snapshot_id
            ).first()

            if snapshot:
                snapshot.total_arrears = Decimal("0.00")
                snapshot.outstanding_balance = Decimal("0.00")

        ground_truth.append({
            "anomaly_id": "ANOM-001",
            "anomaly_type": "paid_off_loan_in_collection",
            "entity_type": "CollectionCase",
            "entity_id": case.case_id,
            "related_entity_ids": [
                loan.loan_id,
                account.account_id
            ],
            "expected_validation": "A paid-off loan must not remain in an open collection case.",
            "description": "Loan marked paid_off and account closed while collection case remains open."
        })

        # -------------------------------------------------
        # ANOMALY 2: Contact outside permitted time window
        # -------------------------------------------------
        attempt = session.query(ContactAttempt).filter(
            ContactAttempt.preference_id.isnot(None)
        ).first()

        if not attempt:
            raise ValueError("No contact attempt with preference found.")

        preference_id = attempt.preference_id
        original_attempt_time = attempt.attempted_at

        attempt.attempted_at = original_attempt_time.replace(
            hour=22,
            minute=30,
            second=0
        )

        ground_truth.append({
            "anomaly_id": "ANOM-002",
            "anomaly_type": "contact_outside_allowed_window",
            "entity_type": "ContactAttempt",
            "entity_id": attempt.attempt_id,
            "related_entity_ids": [preference_id],
            "expected_validation": "Contact attempts must fall within the customer's permitted contact window.",
            "description": "Contact attempt moved to 22:30, outside the permitted 09:00-18:00 window."
        })

        # -------------------------------------------------
        # ANOMALY 3: Payment allocated to wrong installment
        # -------------------------------------------------
        allocation = session.query(PaymentAllocation).first()

        if not allocation:
            raise ValueError("No payment allocation found.")

        payment = session.query(Payment).filter(
            Payment.payment_id == allocation.payment_id
        ).first()

        wrong_installment = session.query(Installment).filter(
            Installment.loan_id != payment.loan_id
        ).first()

        if not wrong_installment:
            raise ValueError("No installment from another loan found.")

        original_installment_id = allocation.installment_id
        allocation.installment_id = wrong_installment.installment_id

        ground_truth.append({
            "anomaly_id": "ANOM-003",
            "anomaly_type": "payment_allocated_to_wrong_installment",
            "entity_type": "PaymentAllocation",
            "entity_id": allocation.allocation_id,
            "related_entity_ids": [
                payment.payment_id,
                original_installment_id,
                wrong_installment.installment_id
            ],
            "expected_validation": "The payment and its allocated installment must belong to the same loan.",
            "description": "Payment allocation reassigned to an installment belonging to a different loan."
        })

        # -------------------------------------------------
        # ANOMALY 4: Promise amount exceeds arrears
        # -------------------------------------------------
        promises = session.query(PromiseToPay).filter(
            PromiseToPay.promise_status == "pending"
        ).all()

        selected_promise = None
        selected_snapshot = None

        for promise in promises:
            linked_count = session.query(
                PromisePaymentAllocation
            ).filter(
                PromisePaymentAllocation.promise_id == promise.promise_id
            ).count()

            if linked_count > 0:
                continue

            promise_case = session.query(CollectionCase).filter(
                CollectionCase.case_id == promise.case_id
            ).first()

            if not promise_case or not promise_case.snapshot_id:
                continue

            promise_snapshot = session.query(DelinquencySnapshot).filter(
                DelinquencySnapshot.snapshot_id == promise_case.snapshot_id
            ).first()

            if promise_snapshot and promise_snapshot.total_arrears > 0:
                selected_promise = promise
                selected_snapshot = promise_snapshot
                break

        if not selected_promise:
            raise ValueError(
                "Could not find a pending promise suitable for anomaly 4."
            )

        original_promised_amount = selected_promise.promised_amount
        arrears = Decimal(str(selected_snapshot.total_arrears))

        selected_promise.promised_amount = (
            arrears + Decimal("1000.00")
        )

        ground_truth.append({
            "anomaly_id": "ANOM-004",
            "anomaly_type": "promise_amount_exceeds_arrears",
            "entity_type": "PromiseToPay",
            "entity_id": selected_promise.promise_id,
            "related_entity_ids": [selected_snapshot.snapshot_id],
            "expected_validation": "Promised amount must not exceed the customer's current arrears.",
            "description": "Promise amount deliberately increased to arrears plus 1000."
        })

        # -------------------------------------------------
        # ANOMALY 5: Disputed debt treated as confirmed
        # -------------------------------------------------
        disputed_cases = session.query(CollectionCase).filter(
            CollectionCase.case_status == "review"
        ).all()

        selected_disputed_case = None
        selected_disputed_snapshot = None

        for disputed_case in disputed_cases:
            if not disputed_case.snapshot_id:
                continue

            disputed_snapshot = session.query(DelinquencySnapshot).filter(
                DelinquencySnapshot.snapshot_id == disputed_case.snapshot_id
            ).first()

            if disputed_snapshot and disputed_snapshot.disputed:
                selected_disputed_case = disputed_case
                selected_disputed_snapshot = disputed_snapshot
                break

        if not selected_disputed_case:
            raise ValueError("No disputed case in review status found.")

        selected_disputed_case.case_status = "open"

        ground_truth.append({
            "anomaly_id": "ANOM-005",
            "anomaly_type": "disputed_debt_treated_as_confirmed",
            "entity_type": "CollectionCase",
            "entity_id": selected_disputed_case.case_id,
            "related_entity_ids": [
                selected_disputed_snapshot.snapshot_id,
                selected_disputed_snapshot.loan_id
            ],
            "expected_validation": "A disputed debt must remain under review and must not be treated as confirmed for collection.",
            "description": "Collection case changed from review to open while its delinquency snapshot remains disputed."
        })

        # -------------------------------------------------
        # Record anomaly injections in the audit trail
        # -------------------------------------------------
        for item in ground_truth:
            session.add(
                AuditEvent(
                    event_id=f"AUD-{item['anomaly_id']}",
                    entity_type=item["entity_type"],
                    entity_id=item["entity_id"],
                    event_type="anomaly_injected",
                    event_timestamp=now,
                    old_value=None,
                    new_value=item["anomaly_type"],
                    actor_type="system",
                    notes=item["description"]
                )
            )

        session.commit()

        # Keep ground truth separate from operational data.
        output_dir = Path(GROUND_TRUTH_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / "ground_truth.json"
        csv_path = output_dir / "ground_truth.csv"

        for item in ground_truth:
            item["injected_at"] = now.isoformat()

        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(ground_truth, file, indent=4)

        with open(csv_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "anomaly_id",
                    "anomaly_type",
                    "entity_type",
                    "entity_id",
                    "related_entity_ids",
                    "expected_validation",
                    "description",
                    "injected_at"
                ]
            )
            writer.writeheader()

            for item in ground_truth:
                row = item.copy()
                row["related_entity_ids"] = json.dumps(
                    row["related_entity_ids"]
                )
                writer.writerow(row)

        print("\nANOMALY INJECTION COMPLETED")
        print("=" * 50)

        for item in ground_truth:
            print(
                item["anomaly_id"],
                "-",
                item["anomaly_type"],
                "-",
                item["entity_id"]
            )

        print("\nTotal anomalies injected:", len(ground_truth))
        print("Ground truth JSON:", json_path)
        print("Ground truth CSV:", csv_path)
        print("Audit events recorded:", len(ground_truth))

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    inject_anomalies()
