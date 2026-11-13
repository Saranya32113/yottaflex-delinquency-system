
from sqlalchemy import func

from database.database import get_session

from database.models import (
    Customer,
    Account,
    Loan,
    Installment,
    Payment,
    PaymentAllocation,
    DelinquencySnapshot,
    CollectionCase,
    ContactPreference,
    PromiseToPay
)

db = get_session()

try:
    print("\n" + "=" * 60)
    print("          YOTTAFLEX DATABASE VERIFICATION")
    print("=" * 60)

    # 1. DATABASE RECORD SUMMARY
    print("\n1. DATABASE RECORD SUMMARY")
    print("-" * 60)

    print("Customers:", db.query(Customer).count())
    print("Accounts:", db.query(Account).count())
    print("Loans:", db.query(Loan).count())
    print("Installments:", db.query(Installment).count())
    print("Payments:", db.query(Payment).count())
    print("Payment Allocations:", db.query(PaymentAllocation).count())
    print("Delinquency Snapshots:", db.query(DelinquencySnapshot).count())
    print("Collection Cases:", db.query(CollectionCase).count())
    print("Contact Preferences:", db.query(ContactPreference).count())
    print("Promises to Pay:", db.query(PromiseToPay).count())

    # 2. PAYMENT STATUS SUMMARY
    print("\n2. PAYMENT STATUS SUMMARY")
    print("-" * 60)

    for status in ["received", "failed", "reversed"]:
        count = db.query(Payment).filter(
            Payment.payment_status == status
        ).count()

        print(f"{status.capitalize()} Payments: {count}")

    # 3. DELINQUENCY RISK SUMMARY
    print("\n3. DELINQUENCY RISK SUMMARY")
    print("-" * 60)

    for category in ["low", "medium", "high"]:
        count = db.query(DelinquencySnapshot).filter(
            DelinquencySnapshot.risk_category == category
        ).count()

        print(f"{category.capitalize()} Risk: {count}")

    # 4. DISPUTE AND HARDSHIP SUMMARY
    print("\n4. ADDITIONAL INDICATORS")
    print("-" * 60)

    disputed_count = db.query(DelinquencySnapshot).filter(
        DelinquencySnapshot.disputed.is_(True)
    ).count()

    hardship_count = db.query(DelinquencySnapshot).filter(
        DelinquencySnapshot.hardship_flag.is_(True)
    ).count()

    print("Disputed Loans:", disputed_count)
    print("Hardship Loans:", hardship_count)

    # 5. COLLECTION CASE STATUS
    print("\n5. COLLECTION CASE STATUS")
    print("-" * 60)

    for status in ["open", "on_hold", "closed", "review"]:
        count = db.query(CollectionCase).filter(
            CollectionCase.case_status == status
        ).count()

        print(f"{status.capitalize()} Cases: {count}")

    # 6. COLLECTION PRIORITY SUMMARY
    print("\n6. COLLECTION PRIORITY SUMMARY")
    print("-" * 60)

    for band in ["low", "medium", "high"]:
        count = db.query(CollectionCase).filter(
            CollectionCase.priority_band == band
        ).count()

        print(f"{band.capitalize()} Priority: {count}")

    # 7. COLLECTION SCORE SUMMARY
    print("\n7. PRIORITY SCORE SUMMARY")
    print("-" * 60)

    average_score = db.query(
        func.avg(CollectionCase.priority_score)
    ).scalar()

    highest_score = db.query(
        func.max(CollectionCase.priority_score)
    ).scalar()

    lowest_score = db.query(
        func.min(CollectionCase.priority_score)
    ).scalar()

    print("Average Priority Score:", round(average_score or 0, 2))
    print("Highest Priority Score:", round(highest_score or 0, 2))
    print("Lowest Priority Score:", round(lowest_score or 0, 2))

    # 8. CONTACT CHANNEL SUMMARY
    print("\n8. CONTACT CHANNEL SUMMARY")
    print("-" * 60)

    for channel in ["phone", "sms", "email"]:
        count = db.query(ContactPreference).filter(
            ContactPreference.channel == channel
        ).count()

        print(f"{channel.upper()}: {count}")

    # 9. CONTACT RESTRICTIONS
    print("\n9. CONTACT RESTRICTIONS")
    print("-" * 60)

    do_not_contact_count = db.query(ContactPreference).filter(
        ContactPreference.do_not_contact.is_(True)
    ).count()

    permitted_contact_count = db.query(ContactPreference).filter(
        ContactPreference.do_not_contact.is_(False)
    ).count()

    print("Do Not Contact:", do_not_contact_count)
    print("Permitted Contact:", permitted_contact_count)

    # 10. CONTACT TIME WINDOW SUMMARY
    print("\n10. CONTACT TIME WINDOW SUMMARY")
    print("-" * 60)

    valid_windows = db.query(ContactPreference).filter(
        ContactPreference.permitted_start
        < ContactPreference.permitted_end
    ).count()

    invalid_windows = db.query(ContactPreference).filter(
        ContactPreference.permitted_start
        >= ContactPreference.permitted_end
    ).count()

    print("Valid Contact Windows:", valid_windows)
    print("Invalid Contact Windows:", invalid_windows)

    # 11. PROMISE-TO-PAY SUMMARY
    print("\n11. PROMISE-TO-PAY SUMMARY")
    print("-" * 60)

    print(
        "Total Promises:",
        db.query(PromiseToPay).count()
    )

    for status in [
        "pending",
        "fulfilled",
        "missed",
        "cancelled",
        "invalid"
    ]:
        count = db.query(PromiseToPay).filter(
            PromiseToPay.promise_status == status
        ).count()

        print(f"{status.capitalize()}: {count}")

    # 12. PROMISE AMOUNT SUMMARY
    print("\n12. PROMISE AMOUNT SUMMARY")
    print("-" * 60)

    total_promised = db.query(
        func.coalesce(
            func.sum(PromiseToPay.promised_amount), 0
        )
    ).scalar()

    print("Total Promised Amount:", round(float(total_promised), 2))

    # 13. FINAL SUMMARY
    print("\n" + "=" * 60)
    print("       DATABASE VERIFICATION COMPLETED")
    print("=" * 60)

finally:
    db.close()
