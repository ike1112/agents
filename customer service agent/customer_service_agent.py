"""
# ==========================================
# FILE: customer_service_agent.py
# PURPOSE: The main Agent Entry Point.
#          It implements a "Code-as-Policy" agent that:
#          1. Receives a user request.
#          2. Uses an LLM (Gemini) to generate Python code to handle the request (instead of calling fixed tools).
#          3. Executes the generated code in a safe environment against a TinyDB database.
#          4. Updates inventory/transactions and returns a natural language response.
# ==========================================
"""
from __future__ import annotations
import json
import re
import io
import sys
import traceback
import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from tinydb import TinyDB, Query, where
from google import genai
from google.genai.types import GenerateContentConfig
import utils
import inv_utils  # functions for inventory, transactions, schema building, and TinyDB seeding

load_dotenv()

# Initialize Gemini Client
# Ensure GEMINI_API_KEY is set in your .env file
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=api_key)

# Seed the database
db, inventory_tbl, transactions_tbl = inv_utils.seed_db()

# Initial display of tables (using utils)
utils.print_html(json.dumps(inventory_tbl.all(), indent=2), title="Inventory Table")
utils.print_html(json.dumps(transactions_tbl.all(), indent=2), title="Transactions Table")

PROMPT = """You are a senior data assistant. PLAN BY WRITING PYTHON CODE USING TINYDB.

Database Schema & Samples (read-only):
{schema_block}

Execution Environment (already imported/provided):
- Variables: db, inventory_tbl, transactions_tbl  # TinyDB Table objects
- Helpers: get_current_balance(tbl) -> float, next_transaction_id(tbl, prefix="TXN") -> str
- Natural language: user_request: str  # the original user message

PLANNING RULES (critical):
- Derive ALL filters/parameters from user_request (shape/keywords, price ranges "under/over/between", stock mentions,
  quantities, buy/return intent). Do NOT hard-code values.
- Build TinyDB queries dynamically with Query(). If a constraint isn't in user_request, don't apply it.
- Be conservative: if intent is ambiguous, do read-only (DRY RUN).

TRANSACTION POLICY (hard):
- Do NOT create aggregated multi-item transactions.
- If the request contains multiple items, create a separate transaction row PER ITEM.
- For each item:
  - compute its own line total (unit_price * qty),
  - insert ONE transaction with that amount,
  - update balance sequentially (balance += line_total),
  - update the item’s stock.
- If any requested item lacks sufficient stock, do NOT mutate anything; reply with STATUS="insufficient_stock".

HUMAN RESPONSE REQUIREMENT (hard):
- You MUST set a variable named `answer_text` (type str) with a short, customer-friendly sentence (1–2 lines).
- This sentence is the only user-facing message. No dataframes/JSON, no boilerplate disclaimers.
- If nothing matches, politely say so and offer a nearby alternative (closest style/price) or a next step.

ACTION POLICY:
- If the request clearly asks to change state (buy/purchase/return/restock/adjust):
    ACTION="mutate"; SHOULD_MUTATE=True; perform the change and write a matching transaction row.
  Otherwise:
    ACTION="read"; SHOULD_MUTATE=False; simulate and explain briefly as a dry run (in logs only).

FAILURE & EDGE-CASE HANDLING (must implement):
- Do not capture outer variables in Query.test. Pass them as explicit args.
- Always set a short `answer_text`. Also set a string `STATUS` to one of:
  "success", "no_match", "insufficient_stock", "invalid_request", "unsupported_intent".
- no_match: No items satisfy the filters → suggest the closest in style/price, or invite a different range.
- insufficient_stock: Item found but stock < requested qty → state available qty and offer the max you can fulfill.
- invalid_request: Unable to parse essential info (e.g., quantity for a purchase/return) → ask for the missing piece succinctly.
- unsupported_intent: The action is outside the store’s capabilities → provide the nearest supported alternative.
- In all cases, keep the tone helpful and concise (1–2 sentences). Put technical details (e.g., ACTION/DRY RUN) only in stdout logs.

OUTPUT CONTRACT:
- Return ONLY executable Python between these tags (no extra text):
  <execute_python>
  # your python
  </execute_python>

CODE CHECKLIST (follow in code):
1) Parse intent & constraints from user_request (regex ok).
2) Build TinyDB condition incrementally; query inventory_tbl.
3) If mutate: validate stock, update inventory, insert a transaction (new id, amount, balance, timestamp).
4) ALWAYS set:
   - `answer_text` (human sentence, required),
   - `STATUS` (see list above).
   Also print a brief log to stdout, e.g., "LOG: ACTION=read DRY_RUN=True STATUS=no_match".
5) Optional: set `answer_rows` or `answer_json` if useful, but `answer_text` is mandatory.

TONE EXAMPLES (for `answer_text`):
- success: "Thanks for your order! You’ve successfully purchased 3 Classic and 1 Aviator sunglasses."
- no_match: "We don’t have round frames under $100 in stock right now, but our Moon round frame is available at $120."
- insufficient_stock: "We only have 1 pair of Classic left; I can reserve that for you."
- invalid_request: "I can help with that—how many pairs would you like to purchase?"
- unsupported_intent: "We can’t refurbish frames, but I can suggest similar new models."

Constraints:
- Use TinyDB Query for filtering. Standard library imports only if needed.
- Keep code clear and commented with numbered steps.

User request:
{question}
"""

def generate_llm_code(
    prompt: str,
    *,
    inventory_tbl,
    transactions_tbl,
    model: str = "gemini-2.0-flash-exp",
    temperature: float = 0.2,
) -> str:
    """
    Ask the LLM to produce a plan-with-code response.
    Returns the FULL assistant content.

    give the LLM the context it needs to write correct code.

    schema_block contains a description of your database tables (
        inventory
        and 
        transactions
        ). It lists column names (like item_id, price, quantity_in_stock) and data types.

            
    """


    schema_block = inv_utils.build_schema_block(inventory_tbl, transactions_tbl)
    full_prompt = PROMPT.format(schema_block=schema_block, question=prompt)
    print("\n\nFull prompt:\n", full_prompt)

    try:
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=GenerateContentConfig(
                temperature=temperature,
                system_instruction="You write safe, well-commented TinyDB code to handle data questions and updates."
            )
        )
        return response.text
    except Exception as e:
        return f"Error calling Gemini: {e}"


def _extract_execute_block(text: str) -> str:
    """
    Returns the Python code inside <execute_python>...</execute_python> or markdown blocks.
    Robustly strips markdown fences and whitespace.
    """
    if not text:
        raise RuntimeError("Empty content passed to code executor.")
    
    clean_text = text.strip()

    # 1. Try <execute_python> tags
    m = re.search(r"<execute_python>(.*?)</execute_python>", clean_text, re.DOTALL | re.IGNORECASE)
    if m:
        clean_text = m.group(1).strip()
    
    # 2. Try markdown code blocks (```python ... ``` or just ``` ... ```)
    m_md = re.search(r"```(?:\w+)?\n?(.*?)```", clean_text, re.DOTALL)
    if m_md:
        clean_text = m_md.group(1).strip()

    # 3. Final Cleanup: explicitly remove any stray tags if regex missed them 
    # (sometimes models put tags inside code blocks or mix formats)
    clean_text = re.sub(r"</?execute_python>", "", clean_text, flags=re.IGNORECASE).strip()
    
    # Remove strictly leading/trailing backticks if they still exist
    if clean_text.startswith("```"):
        clean_text = re.sub(r"^```(?:\w+)?\s*", "", clean_text)
    if clean_text.endswith("```"):
        clean_text = re.sub(r"\s*```$", "", clean_text)
        
    return clean_text


def execute_generated_code(
    code_or_content: str,
    *,
    db,
    inventory_tbl,
    transactions_tbl,
    user_request: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute code in a controlled namespace.
    Accepts either raw Python code OR full content with <execute_python> tags.
    Returns minimal artifacts: stdout, error, and extracted answer.
    """
    # Extract code here
    code = _extract_execute_block(code_or_content)

    # Globals: It gives the code access to specific helper functions
    SAFE_GLOBALS = {
        "Query": Query,
        "get_current_balance": inv_utils.get_current_balance,
        "next_transaction_id": inv_utils.next_transaction_id,
        "user_request": user_request or "",
    }
    
    # Locals: It gives the code access to the database and tables
    SAFE_LOCALS = {
        "db": db,
        "inventory_tbl": inventory_tbl,
        "transactions_tbl": transactions_tbl,
    }

    # Capture stdout from the executed code
    _stdout_buf, _old_stdout = io.StringIO(), sys.stdout
    sys.stdout = _stdout_buf
    err_text = None
    try:
        exec(code, SAFE_GLOBALS, SAFE_LOCALS)
    except Exception:
        err_text = traceback.format_exc()
        # Print error to stdout buffer as well so it's captured
        print(f"\n[Execution Error]\n{err_text}")
    finally:
        sys.stdout = _old_stdout
    printed = _stdout_buf.getvalue().strip()

    # Extract possible answers set by the generated code
    answer = (
        SAFE_LOCALS.get("answer_text")
        or SAFE_LOCALS.get("answer_rows")
        or SAFE_LOCALS.get("answer_json")
    )

    return {
        "code": code,
        "stdout": printed,
        "error": err_text,
        "answer": answer,
        "transactions_tbl": transactions_tbl.all(),
        "inventory_tbl": inventory_tbl.all(),
    }


def customer_service_agent(
    question: str,
    *,
    db,
    inventory_tbl,
    transactions_tbl,
    model: str = "gemini-2.0-flash-exp",
    temperature: float = 1.0,
    reseed: bool = False,
) -> dict:
    """
    End-to-end helper:
      1) (Optional) reseed inventory & transactions
      2) Generate plan-as-code from `question`
      3) Execute in a controlled namespace
      4) Render before/after snapshots and return artifacts
    """
    # 0) Optional reseed
    if reseed:
        inv_utils.create_inventory()
        inv_utils.create_transactions()

    # 1) Show the question
    utils.print_html(question, title="User Question")

    # 2) Generate plan-as-code (FULL content)
    full_content = generate_llm_code(
        question,
        inventory_tbl=inventory_tbl,
        transactions_tbl=transactions_tbl,
        model=model,
        temperature=0.1,
    )
    utils.print_html(full_content, title="Plan with Code (Full Response)")

    # 3) Before snapshots
    utils.print_html(json.dumps(inventory_tbl.all(), indent=2), title="Inventory Table - Before")
    utils.print_html(json.dumps(transactions_tbl.all(), indent=2), title="Transactions Table - Before")

    # 4) Execute
    exec_res = execute_generated_code(
        full_content,
        db=db,
        inventory_tbl=inventory_tbl,
        transactions_tbl=transactions_tbl,
        user_request=question,
    )

    # 5) After snapshots + final answer
    utils.print_html(exec_res["answer"], title="Plan Execution - Extracted Answer")
    utils.print_html(json.dumps(inventory_tbl.all(), indent=2), title="Inventory Table - After")
    utils.print_html(json.dumps(transactions_tbl.all(), indent=2), title="Transactions Table - After")

    # 6) Return artifacts
    return {
        "full_content": full_content,
        "exec": {
            "code": exec_res["code"],
            "stdout": exec_res["stdout"],
            "error": exec_res["error"],
            "answer": exec_res["answer"],
            "inventory_after": inventory_tbl.all(),
            "transactions_after": transactions_tbl.all(),
        },
    }

if __name__ == "__main__":
    # Test with a prompt
    prompt = "Do you have any round sunglasses in stock that are under $100?"
    
    print(f"--- Running Customer Service Agent with Prompt: {prompt} ---")
    
    out = customer_service_agent(
        prompt,
        db=db,
        inventory_tbl=inventory_tbl,
        transactions_tbl=transactions_tbl,
        model="gemini-2.0-flash-exp",
        temperature=1.0,
        reseed=True, 
    )
    
    # Print the FINAL ANSWER for the user
    final_answer = out['exec'].get('answer')
    if final_answer:
        print("\n" + "="*40)
        print("🤖 AGENT RESPONSE:")
        print("="*40)
        print(final_answer)
        print("="*40 + "\n")

    # We can print execution logs
    if out['exec']['stdout']:
        print("\n--- Execution Stdout ---\n")
        print(out['exec']['stdout'])
