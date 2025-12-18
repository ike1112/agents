"""
email_service.py

This file is the main "Backend API" for the simulated Email Service.
It provides REST endpoints to manage emails (send, list, search, delete).
It mimics a real email provider like Gmail or Outlook.

Key Features:
- FastAPI based web server
- SQLite database backend
- Pre-loads sample emails on startup
- Serves the frontend UI (Jinja2 templates)
"""

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.templating import Jinja2Templates
from typing import List
from sqlalchemy.orm import Session
from .email_database import SessionLocal, engine
from .email_models import Base, Email
from .email_schema import EmailCreate, EmailOut
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import random
import os

app = FastAPI(title="Email Simulation API")

# --- CORS Middleware ---
# Allows requests from any origin. Useful for development when frontend and backend run on different ports.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Static Files & Templates Setup ---
# Setup paths to serve the UI (HTML/CSS)
_THIS_DIR = Path(__file__).resolve().parent               # email_server/
_TEMPLATES_DIR = _THIS_DIR / "templates"
_REPO_ROOT = _THIS_DIR.parent                              # Repository root

# Try to mount a static directory if it exists
_STATIC_CANDIDATES = [
    _THIS_DIR / "static",
    _REPO_ROOT / "static",
]
for _static_dir in _STATIC_CANDIDATES:
    if _static_dir.exists() and _static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
        break 

# Initialize Jinja2 templates for rendering HTML
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request):
    """
    Serves the main User Interface (ui_all.html).
    This endpoint retrieves the HTML template and renders it.
    It passes the API URLs for the email and LLM servers so the frontend knows where to send requests.
    """
    ui_email_server = os.getenv("UI_EMAIL_SERVER", "http://127.0.0.1:5000")
    ui_llm_server   = os.getenv("UI_LLM_SERVER", "http://127.0.0.1:5001") 
    return templates.TemplateResponse(
        "ui_all.html",
        {"request": request, "UI_EMAIL_SERVER": ui_email_server, "UI_LLM_SERVER": ui_llm_server}
    )

# --- Database Setup ---
# create tables if they don't exist
Base.metadata.create_all(bind=engine)

def get_db():
    """
    Dependency generator for database sessions.
    FastAPI calls this function to get a DB session for a request.
    
    Why 'yield' instead of 'return'?
    This allows us to run code AFTER the request is finished.
    1. 'db = SessionLocal()' creates the connection.
    2. 'yield db' pauses this function and gives the connection to your endpoint.
    3. After your endpoint finishes, this function RESUMES and runs the 'finally' block.
    4. 'db.close()' ensures the connection is closed, preventing leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def preload_emails():
    """
    Event handler that runs automatically when the server starts.
    It cleans the database and populates it with sample emails.
    This ensures a consistent state for testing/demo purposes every time you run the app.
    """
    db = SessionLocal()
    try:
        # Clear existing emails
        db.execute(delete(Email))
        db.commit()

        now = datetime.utcnow()
        # Create sample data
        samples = [
            Email(sender="boss@email.com", recipient="you@email.com",
                  subject="Quarterly Report", body="Please finalize the report ASAP.",
                  timestamp=now, read=False),
            Email(sender="alice@work.com", recipient="you@email.com",
                  subject="Lunch?", body="Free for lunch today?",
                  timestamp=now, read=False),
            Email(sender="bob@work.com", recipient="you@email.com",
                  subject="Code Review", body="I left some comments on your PR.",
                  timestamp=now, read=False),
            Email(sender="charlie@work.com", recipient="you@email.com",
                  subject="Meeting", body="Can we reschedule?",
                  timestamp=now, read=False),
            Email(sender="eric@work.com", recipient="you@email.com",
                  subject="Happy Hour", body="We're planning drinks this Friday!",
                  timestamp=now, read=False),
            Email(sender="you@mail.com", recipient="boss@email.com",
                  subject="Days off", body="Can I get some days off the coming week?",
                  timestamp=now, read=False),
        ]
        random.shuffle(samples)
        db.add_all(samples)
        db.commit()
    finally:
        db.close()

# --- API Endpoints ---

@app.post("/send", response_model=EmailOut)
def send_email(email: EmailCreate, db: Session = Depends(get_db)):
    """
    Endpoint to send an email. 
    1. Validates input using EmailCreate schema (recipient, subject, body).
    2. Creates a new database Email object (auto-filling sender as you@mail.com).
    3. Saves it to the database.
    4. Returns the created email object.
    """
    new_email = Email(
        recipient=email.recipient,
        subject=email.subject,
        body=email.body,
        sender="you@mail.com",
    )
    db.add(new_email)
    db.commit()
    db.refresh(new_email)
    return new_email

@app.get("/emails", response_model=List[EmailOut])
def list_emails(db: Session = Depends(get_db)):
    """
    Endpoint to retrieve all emails.
    Returns a list of all emails in the database, sorted by timestamp (newest first).
    FastAPI automatically serializes the database objects to JSON matching EmailOut.
    """
    return db.query(Email).order_by(Email.timestamp.desc()).all()

@app.get("/emails/search", response_model=List[EmailOut])
def search_emails(
    q: str = Query(..., description="Keyword to search in subject/body/sender"),
    db: Session = Depends(get_db),
):
    """
    Endpoint to search emails.
    Accepts a query parameter 'q'.
    Performs a case-insensitive 'ILIKE' query across subject, body, and sender fields.
    Returns matching emails.
    """
    return db.query(Email).filter(
        (Email.subject.ilike(f"%{q}%")) |
        (Email.body.ilike(f"%{q}%")) |
        (Email.sender.ilike(f"%{q}%"))
    ).order_by(Email.timestamp.desc()).all()

@app.get("/emails/filter", response_model=List[EmailOut])
def filter_emails(
    recipient: str | None = Query(None, description="Recipient email address (optional)"),
    date_from: str | None = Query(None, description="Start date YYYY-MM-DD (optional)"),
    date_to: str | None = Query(None, description="End date YYYY-MM-DD (optional)"),
    db: Session = Depends(get_db),
):
    """
    Endpoint to filter emails with multiple optional criteria.
    - recipient: exact match
    - date_from/date_to: range filtering on timestamp
    Constructs the query dynamically based on which parameters are provided.
    """
    query = db.query(Email)

    if recipient:
        query = query.filter(Email.recipient == recipient)

    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Email.timestamp >= date_from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")

    if date_to:
        try:
            date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            query = query.filter(Email.timestamp <= date_to_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")

    return query.order_by(Email.timestamp.desc()).all()

@app.get("/emails/unread", response_model=List[EmailOut])
def get_unread_emails(db: Session = Depends(get_db)):
    """
    Endpoint to get unread emails.
    Filters the database for records where column 'read' is False/0.
    """
    return db.query(Email).filter(Email.read == False).order_by(Email.timestamp.desc()).all()

@app.get("/emails/{email_id}", response_model=EmailOut)
def get_email(email_id: int, db: Session = Depends(get_db)):
    """
    Endpoint to get a specific email by ID.
    If the email doesn't exist, it stops execution and returns a 404 HTTP error.
    """
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email

@app.patch("/emails/{email_id}/read", response_model=EmailOut)
def mark_email_as_read(email_id: int, db: Session = Depends(get_db)):
    """
    Endpoint to mark an email as read.
    1. Finds the email.
    2. Updates 'read' status to True.
    3. Commits to DB.
    """
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    email.read = True
    db.commit()
    db.refresh(email)
    return email

@app.patch("/emails/{email_id}/unread", response_model=EmailOut)
def mark_email_as_unread(email_id: int, db: Session = Depends(get_db)):
    """
    Endpoint to mark an email as unread.
    Updates 'read' status to False.
    """
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    email.read = False
    db.commit()
    db.refresh(email)
    return email

@app.delete("/emails/{email_id}")
def delete_email(email_id: int, db: Session = Depends(get_db)):
    """
    Endpoint to delete an email.
    Finds the email, deletes it from the session, commits the transaction.
    Returns a simple success message.
    """
    email = db.query(Email).filter(Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    db.delete(email)
    db.commit()
    return {"message": "Email deleted"}

@app.get("/reset_database")
def reset_database():
    """
    Helper Endpoint.
    Manually triggers the 'preload_emails' logic to wipe the DB and reload sample data.
    """
    preload_emails()
    return {"message": "Database reset and emails reloaded"}

@app.get("/health")
def health():
    """
    Simple check to see if the server is up and running.
    Useful for monitoring tools.
    """
    return {"status": "ok"}
