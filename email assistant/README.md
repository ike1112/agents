# Email Assistant Agent 🤖📧

A simulated AI Email Assistant that uses Google's Gemini LLM to manage your inbox. It follows a microservices architecture with a separate Email Backend and AI Agent.

## 🚀 Quick Start

You need to run **two separate servers** in two different terminals.

### Prerequisites

1.  Make sure you have your `.env` file in the root `agents/` folder with `GEMINI_API_KEY`.
2.  Activate your virtual environment:

    ```powershell
    .\venv\Scripts\Activate.ps1
    ```

---

### Step 1: Start the Email Service (The Inbox)
This simulates the email provider (like Gmail) and serves the UI.

**Terminal 1:**
```powershell
# Navigate to the 'agents' folder if not already there
python -m uvicorn "email assistant.email_server.email_service:app" --reload --port 5000
```
*   ✅ **Verify**: Open [http://localhost:5000](http://localhost:5000) in your browser. You should see the dashboard.

### Step 2: Start the LLM Service (The Agent)
This runs the AI brain that processes your commands.

**Terminal 2:**
```powershell
# Activate venv first!
.\venv\Scripts\Activate.ps1

python -m uvicorn "email assistant.email_server.llm_service:app" --reload --port 5001
```

---

## 🎮 How to Use

1.  Go to **[http://localhost:5000](http://localhost:5000)** in your browser.
2.  Use the **"LLM Prompt Box"** on the right side.
3.  Type commands like:
    *   *"Summarize unread emails"*
    *   *"Find the email from 'Eric' and delete it"*
    *   *"Mark all emails from 'Alice' as read"*
    *   *"Reply to the 'Meeting' email saying I can make it"*

## 📂 Project Structure

*   `email_server/email_service.py`: The Backend API (Database & UI).
*   `email_server/llm_service.py`: The AI Agent API (Google Gemini).
*   `email_server/email_tools.py`: The tools the AI uses to talk to the backend.
*   `email_server/emails.db`: The local SQLite database file.

For a deep dive into how it works, read [ARCHITECTURE.md](ARCHITECTURE.md).
