import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

# Load env variables from root directory
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    # Default fallback
    DATABASE_URL = 'postgresql://postgres:password123@localhost:5432/solar_copilot'

engine = create_engine(DATABASE_URL)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

from sqlalchemy import text

def init_db():
    # Import all models here so they are registered properly on the metadata
    import backend.models_db
    
    # Clean the public schema to wipe legacy tables and key constraints
    print("Wiping public schema to reset database...")
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.commit()
        
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully!")
