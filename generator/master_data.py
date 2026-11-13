
import random
from datetime import date, timedelta

from faker import Faker
from sqlalchemy.orm import Session

from config import RANDOM_SEED
from database.models import Customer, Account, Loan

fake = Faker("en_IN")
fake.seed_instance(RANDOM_SEED)
random.seed(RANDOM_SEED)


def generate_master_data(
    session: Session,
    total_loans: int = 10_000
):
    print("Generating master data...")

    # Prevent duplicate generation
    existing_customers = session.query(Customer).count()
    existing_accounts = session.query(Account).count()
    existing_loans = session.query(Loan).count()

    if existing_customers or existing_accounts or existing_loans:
        print("Master data already exists.")
        print("Skipping generation to prevent duplicates.")
        print(f"Customers: {existing_customers}")
        print(f"Accounts: {existing_accounts}")
        print(f"Loans: {existing_loans}")
        return

    customers = []
    accounts = []
    loans = []

    snapshot_date = date(2026, 11, 13)

    for i in range(1, total_loans + 1):

        customer_id = f"CUST-2026-{i:06d}"
        account_id = f"ACC-2026-{i:06d}"
        loan_id = f"LOAN-2026-{i:06d}"

        first_name = fake.first_name()
        last_name = fake.last_name()

        customer = Customer(
            customer_id=customer_id,
            first_name=first_name,
            last_name=last_name,
            email=f"customer{i}@example.com",
            phone=fake.numerify("9#########")
        )

        start_date = (
            snapshot_date
            - timedelta(days=random.randint(180, 700))
        )

        principal = round(
            random.uniform(10000, 500000), 2
        )

        term_months = random.choice([12, 18, 24, 36])

        loan = Loan(
            loan_id=loan_id,
            account_id=account_id,
            principal_amount=principal,
            annual_interest_rate=round(
                random.uniform(8, 18), 3
            ),
            term_months=term_months,
            start_date=start_date,
            end_date=start_date + timedelta(
                days=30 * term_months
            ),
            loan_status="active"
        )

        account = Account(
            account_id=account_id,
            customer_id=customer_id,
            account_status="active",
            opened_at=start_date
        )

        customers.append(customer)
        accounts.append(account)
        loans.append(loan)

        if i % 1000 == 0:
            print(f"Prepared {i} master records")

    try:
        session.add_all(customers)
        session.add_all(accounts)
        session.add_all(loans)

        session.commit()

        print("Master data generation completed!")
        print(f"Customers: {len(customers)}")
        print(f"Accounts: {len(accounts)}")
        print(f"Loans: {len(loans)}")

    except Exception:
        session.rollback()
        raise


if __name__ == "__main__":
    from database.database import get_session

    db = get_session()

    try:
        generate_master_data(db)
    finally:
        db.close()
