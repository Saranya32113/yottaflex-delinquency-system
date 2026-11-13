
import json
import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from config import DATABASE_PATH, EXPORT_DIR
from database.database import engine
from database.models import Base


def export_database():
    export_dir = Path(EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "database": "YottaFlex Delinquency Management System",
        "export_format": ["CSV", "JSON", "SQL"],
        "tables": {}
    }

    print("\nYOTTAFLEX DATA EXPORT")
    print("=" * 50)

    # Export every database table to CSV and JSON.
    with engine.connect() as connection:
        for table in Base.metadata.sorted_tables:
            table_name = table.name

            query = text(f'SELECT * FROM "{table_name}"')
            dataframe = pd.read_sql_query(query, connection)

            csv_path = export_dir / f"{table_name}.csv"
            json_path = export_dir / f"{table_name}.json"

            dataframe.to_csv(csv_path, index=False)

            records = dataframe.to_dict(orient="records")

            with open(json_path, "w", encoding="utf-8") as file:
                json.dump(
                    records,
                    file,
                    indent=4,
                    ensure_ascii=False,
                    default=str
                )

            row_count = len(dataframe)

            manifest["tables"][table_name] = {
                "row_count": row_count,
                "csv_file": csv_path.name,
                "json_file": json_path.name
            }

            print(
                f"{table_name}: {row_count} records exported"
            )

    # Export a complete SQLite SQL dump.
    sql_path = export_dir / "yottaflex_database.sql"

    sqlite_connection = sqlite3.connect(str(DATABASE_PATH))

    try:
        with open(sql_path, "w", encoding="utf-8") as file:
            for line in sqlite_connection.iterdump():
                file.write(line + "\n")
    finally:
        sqlite_connection.close()

    # Save export manifest.
    manifest_path = export_dir / "export_manifest.json"

    with open(manifest_path, "w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=4)

    total_tables = len(manifest["tables"])
    total_records = sum(
        item["row_count"]
        for item in manifest["tables"].values()
    )

    print("\nEXPORT COMPLETED")
    print("=" * 50)
    print("Tables exported:", total_tables)
    print("Total records exported:", total_records)
    print("CSV files:", total_tables)
    print("JSON files:", total_tables)
    print("SQL dump:", sql_path)
    print("Manifest:", manifest_path)
    print("Export folder:", export_dir)


if __name__ == "__main__":
    export_database()
