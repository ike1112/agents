# code-as-policy

A "Code-as-Policy" customer service agent that dynamically writes and executes Python code to handle requests (purchases, returns, queries) instead of relying on a fixed set of tools.

## Key Features

- **Code-as-Policy:** The LLM (Gemini) generates safe Python scripts using `tinydb` to solve user requests on the fly.
- **Safe Execution:** Generated code runs in a controlled `exec()` sandbox with limited access to globals and locals.
- **Persistent Data:** Uses `TinyDB` for a lightweight, file-based database (`store_db.json`) of inventory and transactions.
- **Transparent Logging:** Provides "Before" and "After" snapshots of the database to verify the agent's actions.

## Files Structure

- **`customer_service_agent.py`**: The main entry point. Contains the `generate_llm_code` and `execute_generated_code` logic.
- **`inv_utils.py`**: Utilities for `TinyDB` database initialization, seeding mock data, and schema helpers.
- **`utils.py`**: General display utilities for pretty-printing output in terminal or notebooks.
- **`tools.py`**: (Alternative) A registry of Pandas/DuckDB tools (not used by the main agent but available for reference).
- **`inventory_utils.py`**: (Alternative) Pandas-based inventory utilities.

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r ../requirements.txt
   ```
   *Make sure `tinydb`, `google-genai`, and `python-dotenv` are installed.*

2. **Environment Variables:**
   Create a `.env` file in the root directory (or ensure your existing one is loaded) with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Run the agent directly from the terminal:

```bash
python customer_service_agent.py
```

This will:
1. Seed the database with random sunglasses inventory.
2. Run a sample query: *"I want to buy 3 pairs of classic sunglasses and 1 pair of aviator sunglasses."*
3. Print the generated plan, execution logs, and final result.

## How It Works

1. **Receive:** You send a request ("Buy 3 Classic sunglasses").
2. **Plan:** The agent receives your request + the database schema. It writes a Python script Using `tinydb` queries.
3. **Execute:** The script is run in a sandbox. It checks stock, updates the inventory, and logs a transaction.
## Takeaways

This project demonstrates the power of the **"Code-as-Policy"** architecture:

1.  **Code > Tools:** Instead of writing dozens of specific functions (`buy_item`, `search_by_price`), we give the LLM one powerful tool: **Python**. It can handle infinite variations of requests dynamically.
2.  **The Sandbox is Key:** We use `exec(code, globals, locals)` to run the generated code safely. The agent only sees the database tables we explicitly pass to it, keeping the rest of the system secure.
3.  **Context is Everything:** The agent succeeds because we inject the **Schema** (data structure) and **Policy** (business rules) into every prompt.
4.  **Robustness Variables:** Real-world reliability requires handling parsing errors (cleaning Markdown tags) and tuning model parameters (lowering temperature for logic precision).

