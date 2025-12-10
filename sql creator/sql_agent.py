import json
import pandas as pd
from dotenv import load_dotenv
import utils 

# 1. Setup Environment
load_dotenv()

def generate_sql(question: str, schema: str, model: str) -> str:
    """
    Generates the initial SQL query (V1) based on the question and schema.
    """
    prompt = f"""
    You are a SQL assistant. Given the schema and the user's question, write a SQL query for SQLite.

    Schema:
    {schema}

    User question:
    {question}

    Respond with the SQL only.
    """
    response = utils.get_response(model, prompt)
    return response.strip()

def refine_sql(
    question: str,
    sql_query: str,
    schema: str,
    model: str,
) -> tuple[str, str]:
    """
    Reflect on whether a query's *shown output* answers the question,
    and propose an improved SQL if needed.
    Returns (feedback, refined_sql).
    """
    prompt = f"""
You are a SQL reviewer and refiner.

User asked:
{question}

Original SQL:
{sql_query}

Table Schema:
{schema}

Step 1: Briefly evaluate if the SQL OUTPUT fully answers the user's question.
Step 2: If improvement is needed, provide a refined SQL query for SQLite.
If the original SQL is already correct, return it unchanged.

Return STRICT JSON with two fields:
{{
  "feedback": "<1-3 sentences explaining the gap or confirming correctness>",
  "refined_sql": "<final SQL to run>"
}}
"""
    response = utils.get_response(model, prompt)
    content = response.strip()
    try:
        obj = json.loads(content)
        feedback = str(obj.get("feedback", "")).strip()
        refined_sql = str(obj.get("refined_sql", sql_query)).strip()
        if not refined_sql:
            refined_sql = sql_query
    except Exception:
        # Fallback if model doesn't return valid JSON
        feedback = content.strip()
        refined_sql = sql_query

    return feedback, refined_sql

def refine_sql_external_feedback(
    question: str,
    sql_query: str,
    df_feedback: pd.DataFrame,
    schema: str,
    model: str,
) -> tuple[str, str]:
    """
    Reflects on the execution results of V1 to generate a V2 query.
    This is the core "Reflection with External Feedback" pattern.
    """
    
    # We convert the dataframe to markdown to give the LLM context on what went wrong
    feedback_markdown = df_feedback.to_markdown(index=False)

    prompt = f"""
    You are a SQL reviewer and refiner.

    User asked:
    {question}

    Original SQL:
    {sql_query}

    SQL Output:
    {feedback_markdown}

    Table Schema:
    {schema}

    Step 1: Briefly evaluate if the SQL output answers the user's question.
    Step 2: If the SQL could be improved, provide a refined SQL query.
    If the original SQL is already correct, return it unchanged.

    Return a strict JSON object with two fields:
    - "feedback": brief evaluation and suggestions
    - "refined_sql": the final SQL to run
    """

    response = utils.get_response(model, prompt)
    content = response.strip()
    
    # Parse the JSON response
    try:
        obj = json.loads(content)
        feedback = str(obj.get("feedback", "")).strip()
        refined_sql = str(obj.get("refined_sql", sql_query)).strip()
        if not refined_sql:
            refined_sql = sql_query
    except Exception:
        # Fallback if model doesn't return valid JSON
        feedback = content.strip()
        refined_sql = sql_query

    return feedback, refined_sql

def run_sql_workflow(
    db_path: str,
    question: str,
    model_generation: str = "gemini-3-pro-preview",
    model_evaluation: str = "gemini-3-pro-preview",
):
    """
    Orchestrates the V1 generation -> Execution -> Reflection -> V2 Execution workflow.
    """
    print(f"\n{'='*50}")
    print(f"QUESTION: {question}")
    print(f"{'='*50}\n")

    # 1. Extract Schema
    schema = utils.get_schema(db_path)
    print("--- Step 1: Schema Extracted ---")

    # 2. Generate SQL (V1)
    sql_v1 = generate_sql(question, schema, model_generation)
    print(f"\n--- Step 2: Generated SQL V1 ---\n{sql_v1}")

    # 3. Execute V1
    print("\n--- Step 3: Executing V1 ---")
    df_v1 = utils.execute_sql(sql_v1, db_path)
    print(df_v1.to_string())

    # 4. Reflect on V1 with execution feedback
    print("\n--- Step 4: Reflecting on Execution Results ---")
    feedback, sql_v2 = refine_sql_external_feedback(
        question=question,
        sql_query=sql_v1,
        df_feedback=df_v1, # Pass the actual data output for reflection
        schema=schema,
        model=model_evaluation,
    )
    
    print(f"Feedback: {feedback}")
    print(f"Refined SQL V2: {sql_v2}")

    # 5. Execute V2
    print("\n--- Step 5: Executing V2 (Final Answer) ---")
    df_v2 = utils.execute_sql(sql_v2, db_path)
    print(df_v2.to_string())
    print("\nDone.")

if __name__ == "__main__":
    # Initialize the specific database used in the course
    print("Initializing Database...")
    utils.create_transactions_db()
    
    # Run the workflow
    run_sql_workflow(
        db_path="products.db", 
        question="Which color of product has the highest total sales?",
        model_generation="gemini-3-pro-preview",
        model_evaluation="gemini-3-pro-preview"
    )