from sqlalchemy import create_engine

DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"


def get_db_connection():
  # Creating the database connection URL
  db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

  # Creating the SQLAlchemy engine
  engine = create_engine(db_url)

  return engine
