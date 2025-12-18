"""
email_database.py

This file handles the database connection and session management using SQLAlchemy.
It creates the SQLite database engine and a session factory for database transactions.

SQLite is a lightweight, file-based database. Unlike PostgreSQL or MySQL, which require a separate server process, 
SQLite stores everything in a single file on your disk (in this case, emails.db).

The file email_database.py, is using SQLAlchemy, which is a Python library that makes 
working with databases easier (an ORM).
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Path to the local SQLite database file
DATABASE_URL = "sqlite:///./emails.db"

# Create the SQLAlchemy engine
# check_same_thread=False is needed for SQLite to allow multi-threaded access (e.g., FastAPI)
# This establishes the connection to the file emails.db.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Create a session factory
# This is a factory for creating "Sessions".
# Think of a Session as a "scratchpad" or a "transaction". When you want to talk to the database (add an email, search for an email), you open a Session.
# autocommit=False ensures we manually commit transactions
# autoflush=False ensures changes aren't pushed to DB until we say so
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Base class for our SQLAlchemy models
# This creates a Python class that all your database models will inherit from.
Base = declarative_base()
 
 