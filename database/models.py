
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean,
    Date, DateTime, Time, ForeignKey, Numeric,
    Text, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


# 1. CUSTOMER
class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    accounts = relationship("Account", back_populates="customer")
    contact_preferences = relationship(
        "ContactPreference", back_populates="customer"
    )


# 2. ACCOUNT
class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String, primary_key=True)
    customer_id = Column(
        String, ForeignKey("customers.customer_id"), nullable=False
    )
    account_status = Column(String(30), nullable=False)
    opened_at = Column(Date, nullable=False)
    closed_at = Column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "account_status IN ('active', 'closed')"
        ),
    )

    customer = relationship("Customer", back_populates="accounts")
    loans = relationship("Loan", back_populates="account")


# 3. LOAN
class Loan(Base):
    __tablename__ = "loans"

    loan_id = Column(String, primary_key=True)
    account_id = Column(
        String, ForeignKey("accounts.account_id"), nullable=False
    )
    principal_amount = Column(Numeric(14, 2), nullable=False)
    annual_interest_rate = Column(Numeric(6, 3), nullable=False)
    term_months = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    loan_status = Column(String(30), nullable=False)

    __table_args__ = (
        CheckConstraint("principal_amount > 0"),
        CheckConstraint("annual_interest_rate >= 0"),
        CheckConstraint("term_months > 0"),
        CheckConstraint(
            "loan_status IN ('active', 'paid_off', 'defaulted')"
        ),
    )

    account = relationship("Account", back_populates="loans")
    installments = relationship("Installment", back_populates="loan")
    payments = relationship("Payment", back_populates="loan")
    snapshots = relationship(
        "DelinquencySnapshot", back_populates="loan"
    )
    collection_cases = relationship(
        "CollectionCase", back_populates="loan"
    )


# 4. INSTALLMENT
class Installment(Base):
    __tablename__ = "installments"

    installment_id = Column(String, primary_key=True)
    loan_id = Column(
        String, ForeignKey("loans.loan_id"), nullable=False
    )
    installment_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    amount_due = Column(Numeric(14, 2), nullable=False)
    amount_paid = Column(Numeric(14, 2), default=0, nullable=False)
    status = Column(String(30), nullable=False)

    __table_args__ = (
        UniqueConstraint("loan_id", "installment_number"),
        CheckConstraint("installment_number > 0"),
        CheckConstraint("amount_due > 0"),
        CheckConstraint("amount_paid >= 0"),
        CheckConstraint(
            "status IN ('scheduled', 'partially_paid', 'paid', 'overdue')"
        ),
    )

    loan = relationship("Loan", back_populates="installments")
    allocations = relationship(
        "PaymentAllocation", back_populates="installment"
    )


# 5. DELINQUENCY SNAPSHOT
class DelinquencySnapshot(Base):
    __tablename__ = "delinquency_snapshots"

    snapshot_id = Column(String, primary_key=True)
    loan_id = Column(
        String, ForeignKey("loans.loan_id"), nullable=False
    )
    snapshot_date = Column(Date, nullable=False)
    days_past_due = Column(Integer, nullable=False)
    total_arrears = Column(Numeric(14, 2), nullable=False)
    outstanding_balance = Column(Numeric(14, 2), nullable=False)
    risk_category = Column(String(30), nullable=False)
    disputed = Column(Boolean, default=False)
    hardship_flag = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("loan_id", "snapshot_date"),
        CheckConstraint("days_past_due >= 0"),
        CheckConstraint("total_arrears >= 0"),
        CheckConstraint("outstanding_balance >= 0"),
        CheckConstraint(
            "risk_category IN ('low', 'medium', 'high')"
        ),
    )

    loan = relationship("Loan", back_populates="snapshots")


# 6. CONTACT PREFERENCE
class ContactPreference(Base):
    __tablename__ = "contact_preferences"

    preference_id = Column(String, primary_key=True)
    customer_id = Column(
        String, ForeignKey("customers.customer_id"), nullable=False
    )
    channel = Column(String(30), nullable=False)
    permitted_start = Column(Time, nullable=False)
    permitted_end = Column(Time, nullable=False)
    timezone = Column(String(50), default="Asia/Kolkata")
    do_not_contact = Column(Boolean, default=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)

    customer = relationship(
        "Customer", back_populates="contact_preferences"
    )
    contact_attempts = relationship(
        "ContactAttempt", back_populates="preference"
    )


# 7. COLLECTION CASE
class CollectionCase(Base):
    __tablename__ = "collection_cases"

    case_id = Column(String, primary_key=True)
    loan_id = Column(
        String, ForeignKey("loans.loan_id"), nullable=False
    )
    snapshot_id = Column(
        String,
        ForeignKey("delinquency_snapshots.snapshot_id"),
        nullable=True
    )
    priority_score = Column(Float, nullable=False)
    priority_band = Column(String(20), nullable=False)
    case_status = Column(String(30), nullable=False)
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    issue_type = Column(String(100), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "priority_score >= 0 AND priority_score <= 100"
        ),
        CheckConstraint(
            "priority_band IN ('low', 'medium', 'high')"
        ),
        CheckConstraint(
            "case_status IN ('open', 'on_hold', 'closed', 'review')"
        ),
    )

    loan = relationship("Loan", back_populates="collection_cases")
    contact_attempts = relationship(
        "ContactAttempt", back_populates="collection_case"
    )
    promises = relationship(
        "PromiseToPay", back_populates="collection_case"
    )


# 8. CONTACT ATTEMPT
class ContactAttempt(Base):
    __tablename__ = "contact_attempts"

    attempt_id = Column(String, primary_key=True)
    case_id = Column(
        String, ForeignKey("collection_cases.case_id"), nullable=False
    )
    preference_id = Column(
        String,
        ForeignKey("contact_preferences.preference_id"),
        nullable=True
    )
    channel = Column(String(30), nullable=False)
    attempted_at = Column(DateTime, nullable=False)
    outcome = Column(String(30), nullable=False)
    blocked = Column(Boolean, default=False)
    block_reason = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('connected', 'no_answer', 'promise', "
            "'dispute', 'refused', 'blocked')"
        ),
    )

    collection_case = relationship(
        "CollectionCase", back_populates="contact_attempts"
    )
    preference = relationship(
        "ContactPreference", back_populates="contact_attempts"
    )
    promises = relationship(
        "PromiseToPay", back_populates="contact_attempt"
    )


# 9. PROMISE TO PAY
class PromiseToPay(Base):
    __tablename__ = "promises_to_pay"

    promise_id = Column(String, primary_key=True)
    case_id = Column(
        String, ForeignKey("collection_cases.case_id"), nullable=False
    )
    attempt_id = Column(
        String, ForeignKey("contact_attempts.attempt_id"), nullable=True
    )
    promised_amount = Column(Numeric(14, 2), nullable=False)
    promised_date = Column(Date, nullable=False)
    promise_status = Column(String(30), nullable=False)

    __table_args__ = (
        CheckConstraint("promised_amount > 0"),
        CheckConstraint(
            "promise_status IN ('pending', 'fulfilled', "
            "'missed', 'cancelled', 'invalid')"
        ),
    )

    collection_case = relationship(
        "CollectionCase", back_populates="promises"
    )
    contact_attempt = relationship(
        "ContactAttempt", back_populates="promises"
    )
    payment_links = relationship(
        "PromisePaymentAllocation", back_populates="promise"
    )


# 10. PAYMENT
class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String, primary_key=True)
    loan_id = Column(
        String, ForeignKey("loans.loan_id"), nullable=False
    )
    payment_date = Column(Date, nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    payment_method = Column(String(30), nullable=False)
    payment_status = Column(String(30), nullable=False)

    __table_args__ = (
        CheckConstraint("amount > 0"),
        CheckConstraint(
            "payment_status IN ('received', 'reversed', 'failed')"
        ),
    )

    loan = relationship("Loan", back_populates="payments")
    allocations = relationship(
        "PaymentAllocation", back_populates="payment"
    )
    promise_links = relationship(
        "PromisePaymentAllocation", back_populates="payment"
    )


# BRIDGE 1: PAYMENT TO INSTALLMENT
class PaymentAllocation(Base):
    __tablename__ = "payment_allocations"

    allocation_id = Column(String, primary_key=True)
    payment_id = Column(
        String, ForeignKey("payments.payment_id"), nullable=False
    )
    installment_id = Column(
        String, ForeignKey("installments.installment_id"), nullable=False
    )
    allocated_amount = Column(Numeric(14, 2), nullable=False)

    __table_args__ = (
        CheckConstraint("allocated_amount > 0"),
    )

    payment = relationship("Payment", back_populates="allocations")
    installment = relationship(
        "Installment", back_populates="allocations"
    )


# BRIDGE 2: PAYMENT TO PROMISE
class PromisePaymentAllocation(Base):
    __tablename__ = "promise_payment_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    promise_id = Column(
        String, ForeignKey("promises_to_pay.promise_id"), nullable=False
    )
    payment_id = Column(
        String, ForeignKey("payments.payment_id"), nullable=False
    )
    allocated_amount = Column(Numeric(14, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("promise_id", "payment_id"),
        CheckConstraint("allocated_amount > 0"),
    )

    promise = relationship("PromiseToPay", back_populates="payment_links")
    payment = relationship("Payment", back_populates="promise_links")


# AUDIT HISTORY
class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id = Column(String, primary_key=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(100), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_timestamp = Column(DateTime, default=datetime.utcnow)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    actor_type = Column(String(30), nullable=False)
    notes = Column(Text, nullable=True)
