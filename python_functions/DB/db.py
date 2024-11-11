import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

def connect_to_database():
    """
    Establish a connection to the MySQL database using MySQL Connector.
    Reads database configuration from environment variables.
    Returns a tuple of connection and cursor.
    """
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        cursor = conn.cursor(dictionary=True)  # Using dictionary cursor for named columns
        return conn, cursor
    except Error as err:
        print(f"Error: {err}")
        return None, None

def get_message_by_code(code):
    conn, cursor = connect_to_database()
    if conn is None or cursor is None:
        return "Database connection error"

    try:
        query = "SELECT english FROM errors_1 WHERE code = %s"  # Replace 'messages_table' with your table name
        cursor.execute(query, (code,))
        result = cursor.fetchone()  # Fetch a single result as a dictionary
        error_type=code[5].lower()

        if result:
            return error_type,result['english']  # Access the 'english' key from the dictionary
        else:
            return "Message not found"
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return "Error fetching message"
    finally:
        cursor.close()
        conn.close()