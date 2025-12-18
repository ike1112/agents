"""
email_models.py

This file defines the SQLAlchemy Object-Relational Mapping (ORM) models.
It maps Python classes to database tables.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime
from .email_database import Base

class Email(Base):
    """
    Represents an email message in the 'emails' table.
    """
    __tablename__ = "emails"

    # Unique identifier for each email
    id = Column(Integer, primary_key=True, index=True)
    
    # Email address of the sender
    sender = Column(String, default="default@demo.com")
    
    # Email address of the recipient
    recipient = Column(String, nullable=False)
    
    # Subject line of the email
    subject = Column(String, nullable=False)
    
    # Full body content of the email
    body = Column(Text, nullable=False)
    
    # Timestamp when the email was created/sent (UTC)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Status to track if the email has been read
    read = Column(Boolean, default=False)  
