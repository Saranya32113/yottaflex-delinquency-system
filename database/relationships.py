
from database.models import Base


def show_database_tables():
    print("\nDATABASE TABLES")
    print("=" * 40)

    for table_name, table in Base.metadata.tables.items():
        print(f"\nTable: {table_name}")

        for column in table.columns:
            print(
                f"  {column.name} | "
                f"Type: {column.type} | "
                f"Primary Key: {column.primary_key} | "
                f"Nullable: {column.nullable}"
            )

        for foreign_key in table.foreign_keys:
            print(
                f"  Foreign Key: {foreign_key.parent.name} "
                f"-> {foreign_key.target_fullname}"
            )


if __name__ == "__main__":
    show_database_tables()
