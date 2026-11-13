
from database.database import get_session
from database.models import ContactPreference, ContactAttempt


def test_contact_preferences_and_restrictions():
    session = get_session()

    try:
        total_preferences = session.query(ContactPreference).count()

        dnc_customers = session.query(ContactPreference).filter(
            ContactPreference.do_not_contact.is_(True)
        ).count()

        permitted_customers = session.query(ContactPreference).filter(
            ContactPreference.do_not_contact.is_(False)
        ).count()

        total_attempts = session.query(ContactAttempt).count()

        assert total_preferences == 10000
        assert dnc_customers == 400
        assert permitted_customers == 9600
        assert total_attempts == 1718

    finally:
        session.close()
