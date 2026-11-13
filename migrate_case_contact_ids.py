
import csv
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from config import DATABASE_PATH, GROUND_TRUTH_DIR, EXPORT_DIR


def create_database_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DATABASE_PATH.parent / (
        f"yottaflex_backup_before_case_contact_migration_{timestamp}.db"
    )

    source = sqlite3.connect(DATABASE_PATH)
    destination = sqlite3.connect(backup_path)

    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    return backup_path


def update_ground_truth(case_map, contact_map):
    json_path = GROUND_TRUTH_DIR / "ground_truth.json"
    csv_path = GROUND_TRUTH_DIR / "ground_truth.csv"

    backups = {}
    for path in (json_path, csv_path):
        backup = path.with_name(path.name + ".before_id_migration.bak")
        shutil.copy2(path, backup)
        backups[path] = backup

    payment_map = {
        "PAY-2026-0000001": "PMT-2026-000001"
    }

    def replace_id(value):
        if not isinstance(value, str):
            return value

        return (
            case_map.get(value)
            or contact_map.get(value)
            or payment_map.get(value)
            or value
        )

    try:
        with open(json_path, "r", encoding="utf-8") as file:
            records = json.load(file)

        for record in records:
            record["entity_id"] = replace_id(record["entity_id"])
            record["related_entity_ids"] = [
                replace_id(value)
                for value in record.get("related_entity_ids", [])
            ]

        json_temp = json_path.with_suffix(".json.tmp")
        with open(json_temp, "w", encoding="utf-8") as file:
            json.dump(records, file, indent=4)
        json_temp.replace(json_path)

        with open(csv_path, "r", encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
            fieldnames = list(rows[0].keys()) if rows else []

        for row in rows:
            row["entity_id"] = replace_id(row["entity_id"])

            related = json.loads(row["related_entity_ids"])
            row["related_entity_ids"] = json.dumps([
                replace_id(value) for value in related
            ])

        csv_temp = csv_path.with_suffix(".csv.tmp")
        with open(csv_temp, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        csv_temp.replace(csv_path)

    except Exception:
        for original, backup in backups.items():
            shutil.copy2(backup, original)
        raise


def migrate():
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(DATABASE_PATH)

    backup_path = create_database_backup()
    print("Database backup created:", backup_path)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA foreign_keys = OFF")

    committed = False

    try:
        connection.execute("BEGIN IMMEDIATE")

        old_case_count = connection.execute(
            "SELECT COUNT(*) FROM collection_cases "
            "WHERE case_id LIKE 'CASE-%'"
        ).fetchone()[0]

        old_contact_count = connection.execute(
            "SELECT COUNT(*) FROM contact_attempts "
            "WHERE attempt_id LIKE 'ATT-%'"
        ).fetchone()[0]

        if old_case_count == 0 and old_contact_count == 0:
            raise RuntimeError(
                "No old case/contact IDs found. "
                "Migration may already have been completed."
            )

        existing_new_cases = connection.execute(
            "SELECT COUNT(*) FROM collection_cases "
            "WHERE case_id LIKE 'COL-%'"
        ).fetchone()[0]

        existing_new_contacts = connection.execute(
            "SELECT COUNT(*) FROM contact_attempts "
            "WHERE attempt_id LIKE 'CTP-%'"
        ).fetchone()[0]

        if existing_new_cases or existing_new_contacts:
            raise RuntimeError(
                "New-format IDs already exist. "
                "Stopping to avoid duplicate IDs."
            )

        old_cases = connection.execute(
            "SELECT case_id FROM collection_cases "
            "ORDER BY case_id"
        ).fetchall()

        case_map = {
            old_id: f"COL-2026-{index:06d}"
            for index, (old_id,) in enumerate(old_cases, start=1)
        }

        old_contacts = connection.execute(
            "SELECT attempt_id, case_id FROM contact_attempts "
            "ORDER BY case_id, attempt_id"
        ).fetchall()

        contact_map = {}

        for old_attempt_id, old_case_id in old_contacts:
            if old_case_id not in case_map:
                raise RuntimeError(
                    f"Contact attempt has unknown case: {old_case_id}"
                )

            new_attempt_id = f"CTP-{case_map[old_case_id]}-001"

            if new_attempt_id in contact_map.values():
                raise RuntimeError(
                    f"Duplicate new contact ID: {new_attempt_id}"
                )

            contact_map[old_attempt_id] = new_attempt_id

        print("Collection cases to migrate:", len(case_map))
        print("Contact attempts to migrate:", len(contact_map))

        if len(case_map) != old_case_count:
            raise RuntimeError("Collection case count mismatch.")

        if len(contact_map) != old_contact_count:
            raise RuntimeError("Contact attempt count mismatch.")

        # Update child foreign-key references first.
        for old_id, new_id in case_map.items():
            connection.execute(
                "UPDATE contact_attempts SET case_id=? WHERE case_id=?",
                (new_id, old_id)
            )
            connection.execute(
                "UPDATE promises_to_pay SET case_id=? WHERE case_id=?",
                (new_id, old_id)
            )

        for old_id, new_id in contact_map.items():
            connection.execute(
                "UPDATE promises_to_pay SET attempt_id=? WHERE attempt_id=?",
                (new_id, old_id)
            )

        # Update audit references. Preserve every audit event.
        for old_id, new_id in case_map.items():
            connection.execute(
                "UPDATE audit_events SET entity_id=? "
                "WHERE entity_type='CollectionCase' AND entity_id=?",
                (new_id, old_id)
            )

        for old_id, new_id in contact_map.items():
            connection.execute(
                "UPDATE audit_events SET entity_id=? "
                "WHERE entity_type='ContactAttempt' AND entity_id=?",
                (new_id, old_id)
            )

        # Update primary keys after their references.
        for old_id, new_id in case_map.items():
            connection.execute(
                "UPDATE collection_cases SET case_id=? WHERE case_id=?",
                (new_id, old_id)
            )

        for old_id, new_id in contact_map.items():
            connection.execute(
                "UPDATE contact_attempts SET attempt_id=? WHERE attempt_id=?",
                (new_id, old_id)
            )

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                f"Foreign-key violations detected: {violations[:10]}"
            )

        remaining_cases = connection.execute(
            "SELECT COUNT(*) FROM collection_cases "
            "WHERE case_id LIKE 'CASE-%'"
        ).fetchone()[0]

        remaining_contacts = connection.execute(
            "SELECT COUNT(*) FROM contact_attempts "
            "WHERE attempt_id LIKE 'ATT-%'"
        ).fetchone()[0]

        if remaining_cases or remaining_contacts:
            raise RuntimeError("Old IDs remain in primary tables.")

        connection.commit()
        committed = True

        # Update ground truth files after the database transaction.
        update_ground_truth(case_map, contact_map)

        mapping_path = EXPORT_DIR / "id_migration_map.json"
        mapping_path.parent.mkdir(parents=True, exist_ok=True)

        with open(mapping_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "collection_cases": case_map,
                    "contact_attempts": contact_map,
                    "payment_reference": {
                        "PAY-2026-0000001": "PMT-2026-000001"
                    }
                },
                file,
                indent=4
            )

        print("\nMIGRATION COMPLETED")
        print("Collection cases migrated:", len(case_map))
        print("Contact attempts migrated:", len(contact_map))
        print("Database backup:", backup_path)
        print("ID mapping:", mapping_path)

        print("\nAnomaly ID checks:")
        print("ANOM-001:", case_map.get("CASE-2026-0000001"))
        print("ANOM-002:", contact_map.get("ATT-PTP-0000001"))
        print("ANOM-005:", case_map.get("CASE-2026-0000013"))

    except Exception:
        connection.rollback()

        if committed:
            shutil.copy2(backup_path, DATABASE_PATH)

        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate()
