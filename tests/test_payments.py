
from database.database import get_session
from validation.check_payments import validate_payments


def test_payment_reconciliation():
    session = get_session()

    try:
        result = validate_payments(session)

        assert result["errors"] == []
        assert result["received_checked"] == 20685
        assert result["failed_checked"] == 605
        assert result["reversed_checked"] == 266

        # Six installments are excluded because of ANOM-003.
        assert result["installments_checked"] == 29994
        assert result["installments_skipped"] == 6

        assert result["wrong_loan_allocations"] == 1

    finally:
        session.close()
