import os
import psycopg2
from dotenv import load_dotenv

# TAG: Connect to the database ""DatabaseConector class is used to connect to the database.""


class DatabaseConnector:
    def __init__(self):
        load_dotenv()
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
            )
            return self.conn
        except (Exception, psycopg2.Error) as e:
            print(f"Error connecting to PostgreSQL: {e}")
            return None

    def disconnect(self):
        if self.conn:
            self.conn.close()
