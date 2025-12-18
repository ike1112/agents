# 📧 AI Email Assistant - Microservices Architecture

This project demonstrates a robust, agentic workflow where an AI Assistant ("The Brain") interacts with a separate Business Domain System ("The Email Server").

## 🏛️ Architecture Overview

The application follows a **Microservices-inspired pattern**, separating the "Business Logic" from the "Intelligence".

![Architecture Diagram](./architecture.png)



---

## 🧩 Component Breakdown & Design Rationale

### 1. The Email Service (`email_service.py`)
*   **Role**: The "Domain System" (mimics Gmail/Outlook).
*   **Tech Stack**: FastAPI, SQLAlchemy, SQLite.
*   **Responsibilities**: 
    *   Manages the database (`emails.db`).
    *   Provides deterministic REST Endpoints (GET `/emails`, POST `/send`).
    *   Serves the Frontend UI (`ui_all.html`).
*   **Design Choice**: **Separation of Concerns**.
    *   **Reasoning**: In the real world, AI agents rarely live *inside* the database. They must interact with external services via APIs. This service is "dumb"; it knows nothing about AI, ensuring the business logic remains stable regardless of the AI model used.

### 2. The LLM Service (`llm_service.py`)
*   **Role**: The "Agnetic Brain".
*   **Tech Stack**: FastAPI, Google GenAI SDK.
*   **Responsibilities**:
    *   Receives natural language prompts (e.g., "Delete Alice's emails").
    *   Configures the "Persona" (System Instructions).
    *   Orchestrates the Function Calling loop.
*   **Design Choice**: **Orchestration Layer**.
    *   **Reasoning**: By keeping the Agent separate, we can scale the intelligence independently. We can swap models (Gemini -> GPT-4) or update the prompt strategy without touching the core Email Server code.

### 3. The Tools Layer (`email_tools.py`)
*   **Role**: The "Translation Layer" (Client Library).
*   **Responsibilities**:
    *   Defines Python functions (e.g., `list_unread_emails()`) that the Agent calls.
    *   Wraps raw HTTP requests to the Email Service.
    *   Handles error states (e.g., catching "Connection Refused" and returning a string the AI can read).
*   **Design Choice**: **Tool Abstraction**.
    *   **Reasoning**: LLMs output text (JSON), not HTTP requests. We need a bridge that converts the LLM's intent ("I want to search") into a concrete executable action (`requests.get(...)`). This file acts as the "Hands" of the Agent.

### 4. The Database (`email_database.py` / `email_models.py`)
*   **Role**: The "Source of Truth".
*   **Tech Stack**: SQLite.
*   **Design Choice**: **SQLAlchemy ORM**.
    *   **Reasoning**: Using an ORM allows us to define the schema in Python (`class Email(Base)`), providing type safety and database agnosticism.

### 5. The Frontend (`templates/ui_all.html`)
*   **Role**: The User Interface.
*   **Tech Stack**: HTML, Vanilla JavaScript.
*   **Design Choice**: **Single Page Application (SPA)**.
    *   **Reasoning**: A simple, unified view that talks to **both services**. It asks the Email Server for data to display, and asks the LLM Server to perform complex actions.

---

## 🔄 The Workflow (Step-by-Step)

Example Task: **"Find unread emails from default@demo.com and mark them as read."**

1.  **User Input**: User types the prompt into the Frontend.
2.  **Request**: Frontend sends POST request to `LLM Service (Port 5001)`.
3.  **Reasoning (Gemini)**:
    *   LLM: "I need to find unread emails first."
    *   LLM Action: Call `search_unread_from_sender(sender='default@demo.com')`.
4.  **Execution (Tool)**:
    *   `email_tools.py` executes.
    *   Sends `GET http://localhost:5000/emails/unread`.
    *   Filters the list in Python.
5.  **Observation**:
    *   Tool returns: `[{id: 5, subject: 'Welcome', ...}]`.
6.  **Reasoning (Gemini)**:
    *   LLM: "I found email ID 5. Now I need to mark it as read."
    *   LLM Action: Call `mark_email_as_read(email_id=5)`.
7.  **Execution (Tool)**:
    *   Tool sends `PATCH http://localhost:5000/emails/5/read`.
8.  **Final Response**:
    *   Gemini: "I have successfully marked the email from default@demo.com as read."
    *   Frontend displays this message.
    *   Frontend refreshes the properties list to reflect the change.

---

## 🚀 Key Takeaways

1.  **Safety**: The Agent is sandboxed. It can only perform actions defined in `tools_list`. It cannot run arbitrary SQL or delete files on the server.
2.  **Modularity**: You can replace the entire backend with Microsoft Outlook's API, and the Agent would still work (you just update `email_tools.py`).
3.  **Realism**: This architecture mirrors how modern Enterprise AI Agents are built: A reasoning engine layer sitting on top of established, deterministic business APIs.
