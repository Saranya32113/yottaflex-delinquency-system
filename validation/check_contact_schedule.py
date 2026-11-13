
import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import EXPORT_DIR

file_path = EXPORT_DIR / "contact_schedule.csv"

errors = []

if not file_path.exists():
    raise FileNotFoundError(
        f"Schedule file not found: {file_path}"
    )

with open(file_path, "r", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

for row in rows:

    scheduled_at = datetime.fromisoformat(
        row["scheduled_at"]
    )

    if scheduled_at.tzinfo is None:
        errors.append(
            f"Missing timezone: {row['case_id']}"
        )
        continue

    local_time = scheduled_at.astimezone(
        ZoneInfo("Asia/Kolkata")
    )

    if not (9 <= local_time.hour < 18):
        errors.append(
            f"Outside permitted hours: {row['case_id']}"
        )

    if row["timezone"] != "Asia/Kolkata":
        errors.append(
            f"Incorrect timezone: {row['case_id']}"
        )

    if row["contact_status"] != "scheduled":
        errors.append(
            f"Incorrect task status: {row['case_id']}"
        )

print("\nCONTACT SCHEDULE VALIDATION")
print("=" * 40)
print("Scheduled tasks:", len(rows))
print("Validation errors:", len(errors))

if errors:
    print("\nERROR DETAILS:")
    for error in errors[:20]:
        print(error)
    print("\nVALIDATION FAILED")
else:
    print("\nSUCCESS: Contact schedule validation passed!")
