"""
email_tools.py

This library acts as the "Client Side" helper for the Agent.
It defines Python functions that wrap HTTP requests to the Email API.
Crucially, these functions include docstrings that the LLM reads to understand HOW to use them.

The Agent does NOT query the database directly. It uses this library to talk to the Email Server 
over HTTP, maintaining a clean microservice boundary.
"""

from dotenv import load_dotenv
import requests
import os
import sys

# --- Environment Setup ---
# Robustly find .env file to get the server URL
current_dir = os.path.dirname(os.path.abspath(__file__))
# Try looking up two levels (agents/)
env_path = os.path.join(os.path.dirname(os.path.dirname(current_dir)), ".env")
load_dotenv(env_path)

# Fallback to current dir
load_dotenv() 

# Base URL for the Email Service (e.g. http://localhost:5000)
BASE_URL = os.getenv("M3_EMAIL_SERVER_API_URL", "http://127.0.0.1:5000")

def _safe_request(method, endpoint, **kwargs):
    """
    Internal helper to perform HTTP requests to the backend.
    It catches exceptions (like Connection Refused) and returns them as
    JSON errors so the LLM can see "Connection Error" instead of crashing.
    """
    if not BASE_URL:
        return {"error": "Configuration Error: M3_EMAIL_SERVER_API_URL is not set."}
    
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(method, url, **kwargs)
        try:
            return response.json()
        except Exception:
            # If backend returns non-JSON (e.g., 500 error page), handle gracefuly
            return {"status": response.status_code, "text": response.text}
    except requests.exceptions.ConnectionError:
        return {"error": f"Connection refused. Is the Email Server running at {url}?"}
    except Exception as e:
        return {"error": str(e)}

# --- Tool Definitions ---

def list_all_emails() -> list | dict:
    """Fetch all emails stored in the system, ordered from newest to oldest."""
    return _safe_request("GET", "/emails")

def list_unread_emails() -> list | dict:
    """Fetch all unread emails only."""
    return _safe_request("GET", "/emails/unread")

def search_emails(query: str) -> list | dict:
    """
    Search emails containing the query in subject, body, or sender.
    Args:
        query (str): A keyword or phrase to search for.
    """
    return _safe_request("GET", "/emails/search", params={"q": query})

def filter_emails(recipient: str = None, date_from: str = None, date_to: str = None) -> list | dict:
    """
    Filter emails based on recipient and/or a date range.
    Args:
        recipient (str): Email address to filter by (optional).
        date_from (str): Start date in 'YYYY-MM-DD' format (optional).
        date_to (str): End date in 'YYYY-MM-DD' format (optional).
    """
    params = {}
    if recipient: params["recipient"] = recipient
    if date_from: params["date_from"] = date_from
    if date_to: params["date_to"] = date_to
    return _safe_request("GET", "/emails/filter", params=params)

def get_email(email_id: int) -> dict:
    """Retrieve a specific email by its ID."""
    return _safe_request("GET", f"/emails/{email_id}")

def mark_email_as_read(email_id: int) -> dict:
    """Mark a specific email as read."""
    return _safe_request("PATCH", f"/emails/{email_id}/read")

def mark_email_as_unread(email_id: int) -> dict:
    """Mark a specific email as unread."""
    return _safe_request("PATCH", f"/emails/{email_id}/unread")

def send_email(recipient: str, subject: str, body: str) -> dict:
    """
    Send an email.
    Args:
        recipient (str): The email address of the recipient.
        subject (str): The subject of the email.
        body (str): The message body content.
    """
    payload = {"recipient": recipient, "subject": subject, "body": body}
    return _safe_request("POST", "/send", json=payload)

def delete_email(email_id: int) -> dict:
    """Delete an email by its ID."""
    return _safe_request("DELETE", f"/emails/{email_id}")

def search_unread_from_sender(sender: str) -> list | dict:
    """
    Return all unread emails from a specific sender (case-insensitive match).
    This function combines 'list_unread_emails' and local client-side logic
    to simplify the task for the LLM.
    """
    unread = list_unread_emails()
    # Check for error in response
    if isinstance(unread, dict) and "error" in unread:
        return unread
    
    # Filter the list python-side
    if isinstance(unread, list):
        return [e for e in unread if e.get('sender', '').lower() == sender.lower()]
    return []
