
import random
from datetime import date, time, timedelta

from database.models import Customer, ContactPreference

RANDOM_SEED = 20261022
SNAPSHOT_DATE = date(2026, 11, 13)


def generate_contact_preferences(session):

    print("Generating contact preferences...")

    existing = session.query(ContactPreference).count()

    if existing > 0:
        print("Contact preferences already exist.")
        print("Existing records:", existing)
        return

    rng = random.Random(RANDOM_SEED + 500)

    customers = session.query(Customer).order_by(
        Customer.customer_id
    ).all()

    channels = ["phone", "sms", "email"]

    preferences = []

    for index, customer in enumerate(customers, start=1):

        channel = rng.choice(channels)

        # Permitted contact window: 09:00 to 18:00
        permitted_start = time(9, 0)
        permitted_end = time(18, 0)

        # Synthetic do-not-contact restriction
        do_not_contact = rng.random() < 0.04

        preference = ContactPreference(
            preference_id=f"PREF-2026-{index:07d}",
            customer_id=customer.customer_id,
            channel=channel,
            permitted_start=permitted_start,
            permitted_end=permitted_end,
            timezone="Asia/Kolkata",
            do_not_contact=do_not_contact,
            effective_from=SNAPSHOT_DATE - timedelta(days=365),
            effective_to=None
        )

        preferences.append(preference)

        if index % 1000 == 0:
            print(f"Processed {index} customers")

    try:
        session.add_all(preferences)
        session.commit()

        print("\nContact preference generation completed!")
        print("Total preferences:", len(preferences))
        print(
            "Do not contact:",
            sum(1 for p in preferences if p.do_not_contact)
        )

    except Exception:
        session.rollback()
        raise


if __name__ == "__main__":

    from database.database import get_session

    db = get_session()

    try:
        generate_contact_preferences(db)
    finally:
        db.close()
