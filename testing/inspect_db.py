from sqlalchemy import create_engine, MetaData, Table

# Database connection
DATABASE_URL = "sqlite:///./ecrf.db"  # Replace with your database file path
engine = create_engine(DATABASE_URL)
connection = engine.connect()

# Load metadata
metadata = MetaData()
metadata.reflect(bind=engine)

def show_table_data(table_name):
    table = Table(table_name, metadata, autoload_with=engine)
    result = connection.execute(table.select()).fetchall()
    print(f"Data from table '{table_name}':")
    for row in result:
        print(row)

if __name__ == "__main__":
    # Check data in tables
    show_table_data("users")
    show_table_data("user_profiles")
