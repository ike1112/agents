"""
email_schema.py

This file defines Pydantic models (Schemas) for data validation and serialization.
These schemas are used by FastAPI to validate incoming JSON requests and format outgoing responses.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
from pydantic import ConfigDict  

class EmailCreate(BaseModel):
    """
    Schema for creating a new email.
    """
    recipient: EmailStr  # Validates that the input is a valid email address
    subject: str        # The subject of the email
    body: str           # The body content of the email

class EmailOut(BaseModel):
    """
    Schema for returning email details to the client.
    Includes the database ID and metadata (timestamp, read status).
    """
    id: int
    sender: EmailStr
    recipient: EmailStr
    subject: str
    body: str
    timestamp: datetime
    read: bool

    # Configuration to allow creating Pydantic models from SQLAlchemy objects
    model_config = ConfigDict(from_attributes=True) 
