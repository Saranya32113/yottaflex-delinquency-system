
from datetime import datetime, time

from database.database import get_session
from database.models import (
    AuditEvent,
    CollectionCase,
    ContactAttempt,
    PromiseToPay,
)
from config import SNAPSHOT_DATE


def generate_audit_events():
    session = get_session()

    try:
        existing = session.query(AuditEvent).count()

        if existing > 0:
            print(f"Audit events already exist: {existing}")
            print("Skipping to prevent duplicate records.")
            return

        events = []

        # 1. Collection case events
        cases = session.query(CollectionCase).all()

        for case in cases:
            events.append(
                AuditEvent(
                    event_id=f"AUD-CASE-{case.case_id}",
                    entity_type="CollectionCase",
                    entity_id=case.case_id,
                    event_type="collection_case_opened",
                    event_timestamp=case.opened_at,
                    old_value=None,
                    new_value=str(case.case_status),
                    actor_type="system",
                    notes="Synthetic audit record for collection case creation."
                )
            )

        # 2. Contact attempt events
        attempts = session.query(ContactAttempt).all()

        for attempt in attempts:
            events.append(
                AuditEvent(
                    event_id=f"AUD-ATT-{attempt.attempt_id}",
                    entity_type="ContactAttempt",
                    entity_id=attempt.attempt_id,
                    event_type="contact_attempt_recorded",
                    event_timestamp=attempt.attempted_at,
                    old_value=None,
                    new_value=str(attempt.outcome),
                    actor_type="system",
                    notes="Synthetic audit record for contact attempt."
                )
            )

        # 3. Promise status observation events
        promises = session.query(PromiseToPay).all()

        attempts_by_id = {
            attempt.attempt_id: attempt
            for attempt in attempts
        }

        snapshot_datetime = datetime.combine(
            datetime.strptime(SNAPSHOT_DATE, "%Y-%m-%d").date(),
            time(23, 59)
        )

        for promise in promises:
            attempt = attempts_by_id.get(promise.attempt_id)

            # Use the contact attempt timestamp when available.
            # Otherwise record the status at the dataset snapshot.
            event_time = (
                attempt.attempted_at
                if attempt is not None
                else snapshot_datetime
            )

            events.append(
                AuditEvent(
                    event_id=f"AUD-PTP-{promise.promise_id}",
                    entity_type="PromiseToPay",
                    entity_id=promise.promise_id,
                    event_type="promise_status_recorded",
                    event_timestamp=event_time,
                    old_value=None,
                    new_value=str(promise.promise_status),
                    actor_type="system",
                    notes=(
                        "Synthetic audit record of promise status. "
                        "This is a status observation, not a verified "
                        "historical status transition."
                    )
                )
            )

        session.add_all(events)
        session.commit()

        print("\nAUDIT EVENT GENERATION COMPLETED")
        print("=" * 45)
        print(f"Collection case events: {len(cases)}")
        print(f"Contact attempt events: {len(attempts)}")
        print(f"Promise status events: {len(promises)}")
        print(f"Total audit events created: {len(events)}")

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    generate_audit_events()
