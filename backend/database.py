import psycopg2

def get_db_connection():
    conn = psycopg2.connect(
        host="localhost",
        database="emergency_response",
        user="admin",           # Use the user you set in pgAdmin
        password="Jothi@2006"  # Use your password
    )
    return conn

# Test the connection
try:
    connection = get_db_connection()
    print("Successfully connected to PostgreSQL!")
    connection.close()
except Exception as e:
    print(f"Connection failed: {e}")