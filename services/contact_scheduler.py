
import csv
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from database.database import get_session
from database.models import (
    CollectionCase,
    Loan,
    Account,
    Customer,
    ContactPreference,
    DelinquencySnapshot
)

from config import EXPORT_DIR


SNAPSHOT_DATE = date(2026, 11, 13)
SCHEDULE_START_DATE = SNAPSHOT_DATE + timedelta(days=1)

TIMEZONE = ZoneInfo("Asia/Kolkata")

SLOT_INTERVAL_MINUTES = 15
INITIAL_CONTACT_TIME = 10


def get_next_allowed_slot(candidate, preference):
    """Find the next slot within the customer's permitted hours."""

    start_time = preference.permitted_start
    end_time = preference.permitted_end

    while True:

        allowed_start = candidate.replace(
            hour=start_time.hour,
            minute=start_time.minute,
            second=0,
            microsecond=0
        )

        allowed_end = candidate.replace(
            hour=end_time.hour,
            minute=end_time.minute,
            second=0,
            microsecond=0
        )

        if candidate < allowed_start:
            candidate = allowed_start

        if candidate >= allowed_end:
            next_day = candidate.date() + timedelta(days=1)

            candidate = datetime.combine(
                next_day,
                start_time,
                tzinfo=TIMEZONE
            )

            continue

        return candidate


def generate_contact_schedule(session):

    print("Building contact schedule...")

    # Get eligible open cases
    records = (
        session.query(
            CollectionCase,
            Loan,
            Account,
            Customer,
            ContactPreference,
            DelinquencySnapshot
        )
        .join(Loan, CollectionCase.loan_id == Loan.loan_id)
        .join(Account, Loan.account_id == Account.account_id)
        .join(Customer, Account.customer_id == Customer.customer_id)
        .join(
            ContactPreference,
            ContactPreference.customer_id == Customer.customer_id
        )
        .join(
            DelinquencySnapshot,
            DelinquencySnapshot.snapshot_id
            == CollectionCase.snapshot_id
        )
        .filter(
            CollectionCase.case_status == "open",
            ContactPreference.do_not_contact.is_(False),
            ContactPreference.effective_from <= SCHEDULE_START_DATE,
            (
                ContactPreference.effective_to.is_(None)
                | (
                    ContactPreference.effective_to
                    >= SCHEDULE_START_DATE
                )
            ),
            DelinquencySnapshot.disputed.is_(False),
            DelinquencySnapshot.hardship_flag.is_(False),
            Loan.loan_status == "active"
        )
        .order_by(
            CollectionCase.priority_score.desc(),
            CollectionCase.case_id
        )
        .all()
    )

    if not records:
        print("No eligible collection cases found.")
        return

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = EXPORT_DIR / "contact_schedule.csv"

    scheduled_tasks = []
    skipped_count = 0

    candidate = datetime.combine(
        SCHEDULE_START_DATE,
        datetime.min.time(),
        tzinfo=TIMEZONE
    ).replace(hour=INITIAL_CONTACT_TIME)

    for (
        case,
        loan,
        account,
        customer,
        preference,
        snapshot
    ) in records:

        # Check customer contact restrictions
        if preference.do_not_contact:
            skipped_count += 1
            continue

        if snapshot.disputed or snapshot.hardship_flag:
            skipped_count += 1
            continue

        # Find an allowed contact time
        candidate = get_next_allowed_slot(
            candidate,
            preference
        )

        scheduled_tasks.append({
            "case_id": case.case_id,
            "loan_id": loan.loan_id,
            "customer_id": customer.customer_id,
            "channel": preference.channel,
            "scheduled_at": candidate.isoformat(),
            "timezone": preference.timezone,
            "priority_score": round(case.priority_score, 2),
            "priority_band": case.priority_band,
            "days_past_due": snapshot.days_past_due,
            "contact_status": "scheduled"
        })

        # Move to the next 15-minute slot
        candidate += timedelta(
            minutes=SLOT_INTERVAL_MINUTES
        )

    # Export schedule
    fieldnames = [
        "case_id",
        "loan_id",
        "customer_id",
        "channel",
        "scheduled_at",
        "timezone",
        "priority_score",
        "priority_band",
        "days_past_due",
        "contact_status"
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as csvfile:

        writer = csv.DictWriter(
            csvfile,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(scheduled_tasks)

    print("\nCONTACT SCHEDULING COMPLETED")
    print("=" * 45)

    print("Eligible cases:", len(records))
    print("Scheduled tasks:", len(scheduled_tasks))
    print("Skipped tasks:", skipped_count)
    print("Slot interval:", SLOT_INTERVAL_MINUTES, "minutes")
    print("Timezone:", "Asia/Kolkata")
    print("Output file:", output_file)


if __name__ == "__main__":

    db = get_session()

    try:
        generate_contact_schedule(db)
    finally:
        db.close()
