"""
llm_service.py

This file acts as the "Brain" or "Agent" of the system.
It exposes a POST /prompt endpoint that accepts natural language instructions.
It uses the Google GenAI SDK to reason about the user's request and calls 
available tools (defined in email_tools.py) to interact with the Email Service.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
# from .display_functions import pretty_print_chat_completion_html
import markdown

# Import the tools that the Agent is allowed to use
from .email_tools import (
    list_all_emails,
    list_unread_emails,
    search_emails,
    filter_emails,
    get_email,
    mark_email_as_read,
    mark_email_as_unread,
    send_email,
    delete_email,
    search_unread_from_sender
)

# Load environment variables (API Key)
load_dotenv()

# Setup Google Client
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    # Try finding .env in parent directory if not in current
    parent_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(parent_env):
        load_dotenv(parent_env)
        api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("WARNING: GEMINI_API_KEY not found. Agent will fail.")

client = genai.Client(api_key=api_key)

app = FastAPI(title="LLM Email Prompt Executor")

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PromptInput(BaseModel):
    """
    Schema for the input request.
    """
    prompt: str

@app.post("/prompt")
async def handle_prompt(payload: PromptInput):
    """
    Main endpoint for the Agent.
    
    1. Receives a user prompt (e.g., "Check unread emails").
    2. Configures the System Instruction (Persona).
    3. Calls Google GenAI with the list of tools enabled.
    4. The SDK handles the Tool Calling loop automatically (Model wants tool -> SDK calls tool -> SDK returns result -> Model repeats).
    5. returns the final text response from the Agent.
    """
    prompt = payload.prompt

    # System Instruction: logic for the Agent's persona and rules
    system_instruction = """
    You are an AI assistant specialized in managing emails. 
    - You can perform various actions such as listing, searching, filtering, and manipulating emails. 
    - Use the provided tools to interact with the email system.
    - Never ask the user for confirmation before performing an action (Autonomous Mode).
    - If needed, my email address is "you@email.com".
    """

    # List of Python functions available to the Agent
    tools_list = [
        list_all_emails,
        list_unread_emails,
        search_emails,
        filter_emails,
        get_email,
        mark_email_as_read,
        mark_email_as_unread,
        send_email,
        delete_email,
        search_unread_from_sender
    ]

    try:
        # Generate content with tools
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp", # Using the latest Flash model for speed/reasoning
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=tools_list,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=False, # Enable automatic execution
                    maximum_remote_calls=20 # Safety limit for loops
                )
            )
        )
        
        # Convert Markdown to HTML for the UI
        final_text = markdown.markdown(response.text)
        
        # Simple styled container for the response
        html_response = f"""
        <div style="border-left: 4px solid #28a745; margin: 20px 0; padding: 10px; background: #eafbe7;">
            <strong style="color:#222;">✅ Agent Output:</strong>
            <p style="color:#000;">{final_text}</p>
        </div>
        """

        return {
            "response": final_text,
            "html_response": html_response 
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
