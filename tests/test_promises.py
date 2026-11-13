
from database.database import get_session
from database.models import PromiseToPay, ContactAttempt


def test_promise_records_and_contact_attempts():
    session = get_session()

    try:
        promises = session.query(PromiseToPay).count()
        attempts = session.query(ContactAttempt).count()

        statuses = {
            status: count
            for status, count in (
                session.query(
                    PromiseToPay.promise_status,
                    __import__("sqlalchemy").func.count()
                )
                .group_by(PromiseToPay.promise_status)
                .all()
            )
        }

        assert promises == 1787
        assert attempts == 1718
        assert statuses.get("fulfilled", 0) == 352
        assert statuses.get("missed", 0) == 856
        assert statuses.get("pending", 0) == 579

    finally:
        session.close()
