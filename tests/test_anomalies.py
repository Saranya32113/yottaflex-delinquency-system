
from database.database import get_session
from validation.check_anomalies import detect_anomalies


def test_all_five_ground_truth_anomalies_are_detected():
    session = get_session()

    try:
        detected = detect_anomalies(session)

        detected_pairs = {
            (item["anomaly_type"], item["entity_id"])
            for item in detected
        }

        expected_pairs = {
            (
                "paid_off_loan_in_collection",
                "COL-2026-000001",
            ),
            (
                "contact_outside_allowed_window",
                "CTP-COL-2026-000001-001",
            ),
            (
                "payment_allocated_to_wrong_installment",
                "ALLOC-2026-0000001",
            ),
            (
                "promise_amount_exceeds_arrears",
                "PTP-2026-0000002",
            ),
            (
                "disputed_debt_treated_as_confirmed",
                "COL-2026-000011",
            ),
        }

        assert expected_pairs.issubset(detected_pairs)
        assert len(detected_pairs) == 5

    finally:
        session.close()
