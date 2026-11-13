
from database.database import create_database
from database.relationships import show_database_tables


def main():
    print("Initializing YottaFlex Database...")

    create_database()

    show_database_tables()

    print("\nDatabase initialization completed!")


if __name__ == "__main__":
    main()
