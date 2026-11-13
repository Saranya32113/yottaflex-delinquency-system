
import sqlite3
from config import DATABASE_PATH


def migrate():
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        # Disable FK enforcement before starting the transaction.
        connection.execute("PRAGMA foreign_keys=OFF")
        connection.execute("BEGIN IMMEDIATE")

        connection.execute("""
            CREATE TEMP TABLE payment_id_map (
                old_id TEXT PRIMARY KEY,
                new_id TEXT NOT NULL UNIQUE
            )
        """)

        connection.execute("""
            INSERT INTO payment_id_map (old_id, new_id)
            SELECT payment_id,
                   'PMT-2026-' ||
                   printf('%06d',
                       ROW_NUMBER() OVER (ORDER BY payment_id)
                   )
            FROM payments
            WHERE payment_id LIKE 'PAY-%'
        """)

        count = connection.execute(
            "SELECT COUNT(*) FROM payment_id_map"
        ).fetchone()[0]

        print("Payment IDs to migrate:", count)

        # Update child tables first.
        connection.execute("""
            UPDATE payment_allocations
            SET payment_id = (
                SELECT new_id
                FROM payment_id_map
                WHERE old_id = payment_allocations.payment_id
            )
            WHERE payment_id IN (
                SELECT old_id FROM payment_id_map
            )
        """)

        connection.execute("""
            UPDATE promise_payment_allocations
            SET payment_id = (
                SELECT new_id
                FROM payment_id_map
                WHERE old_id = promise_payment_allocations.payment_id
            )
            WHERE payment_id IN (
                SELECT old_id FROM payment_id_map
            )
        """)

        # Update parent table.
        connection.execute("""
            UPDATE payments
            SET payment_id = (
                SELECT new_id
                FROM payment_id_map
                WHERE old_id = payments.payment_id
            )
            WHERE payment_id IN (
                SELECT old_id FROM payment_id_map
            )
        """)

        connection.execute("DROP TABLE payment_id_map")

        # Verify foreign-key integrity before committing.
        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                f"Foreign key violations: {violations[:10]}"
            )

        connection.commit()

        connection.execute("PRAGMA foreign_keys=ON")

        print("Payment ID migration completed successfully.")
        print("Migrated payment IDs:", count)
        print("Foreign-key check: PASSED")

    except Exception:
        connection.rollback()
        print("Migration failed. Changes rolled back.")
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate()
