
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATABASE_DIR = BASE_DIR / "data"
DATABASE_PATH = DATABASE_DIR / "yottaflex.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

RANDOM_SEED = 20261022

TOTAL_LOANS = 10_000
INSTALLMENTS_PER_LOAN = 3
TOTAL_INSTALLMENTS = TOTAL_LOANS * INSTALLMENTS_PER_LOAN

SNAPSHOT_DATE = "2026-11-13"

EXPORT_DIR = DATABASE_DIR / "exports"
GROUND_TRUTH_DIR = DATABASE_DIR / "ground_truth"

for directory in [DATABASE_DIR, EXPORT_DIR, GROUND_TRUTH_DIR]:
    directory.mkdir(parents=True, exist_ok=True)