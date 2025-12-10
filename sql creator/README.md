# SQL Agent with Reflection and External Feedback

This SQL agent demonstrates an **agentic workflow** that uses the "Reflection with External Feedback" pattern to iteratively improve SQL queries.

## Design Overview

### The Problem
Generating correct SQL queries is hard. A naive LLM might produce syntactically correct SQL that doesn't actually answer the user's question. Simply asking "is this query good?" isn't enough—the LLM needs to see the actual results.

### The Solution: Reflection with External Feedback

The workflow follows a **V1 → Execute → Reflect → V2** pattern:

```
User Question
     ↓
[Step 1] Generate Initial SQL (V1)
     ↓
[Step 2] Execute V1 on Database ← Get real data results
     ↓
[Step 3] Reflect: Compare Results vs Question
     ↓
[Step 4] Generate Improved SQL (V2)
     ↓
[Step 5] Execute V2 on Database ← Final Answer
```

## How It Works

### Step 1: Generate SQL (V1)
**Function:** `generate_sql(question, schema, model)`

The LLM receives:
- The database schema
- The user's question

It returns a SQL query without any execution context.

```python
# Example:
# Question: "Which color of product has the highest total sales?"
# Output SQL: SELECT color, SUM(qty_delta * unit_price) as total_sales FROM transactions GROUP BY color ORDER BY total_sales DESC LIMIT 1;
```

### Step 2: Execute V1
The generated SQL is executed against the actual database, producing real results.

```python
df_v1 = utils.execute_sql(sql_v1, db_path)
# Returns a DataFrame with the actual query results
```

### Step 3: Reflect with External Feedback
**Function:** `refine_sql_external_feedback(question, sql_v1, df_feedback, schema, model)`

This is the **key innovation**. The LLM is shown:
1. The original question
2. The V1 SQL query it generated
3. **The actual execution results** (the "external feedback")
4. The schema

The LLM then evaluates:
- "Does this output answer the question?"
- "Is anything missing or wrong?"
- "How can I improve the query?"

```python
# The prompt includes the actual results as markdown:
# 
# SQL Output:
# | color | total_sales |
# |-------|-------------|
# | black | 5000.50     |
# | white | 4500.25     |
# ...
#
# Now the LLM can reason: "This shows colors, but the question 
# asks for THE HIGHEST. I need to add ORDER BY and LIMIT 1."
```

### Step 4: Generate Improved SQL (V2)
Based on the actual results and feedback, the LLM returns:
- **feedback**: A string explaining what was wrong or confirming correctness
- **refined_sql**: An improved SQL query

```python
feedback, sql_v2 = refine_sql_external_feedback(...)
# feedback: "The query returns all colors but should filter for just the highest. Added ORDER BY total_sales DESC LIMIT 1."
# sql_v2: "SELECT color, SUM(qty_delta * unit_price) as total_sales FROM transactions WHERE action='sale' GROUP BY color ORDER BY total_sales DESC LIMIT 1;"
```

### Step 5: Execute V2
The refined SQL is executed to get the final answer.

```python
df_v2 = utils.execute_sql(sql_v2, db_path)
# Returns the corrected, final result
```

## Key Design Principles

### 1. **External Feedback Loop**
Instead of asking "is this good?", the system shows the actual evidence:
- The LLM sees real data, not hypothetical scenarios
- It can verify if assumptions were correct
- It can identify missing filters, groupings, or ordering

### 2. **Agentic Reasoning**
The agent:
- Generates → Executes → Observes → Reflects → Improves
- This mirrors how a human would debug SQL

### 3. **Graceful Degradation**
If the V1 query is already correct, the LLM returns it unchanged:
```python
"refined_sql": "<final SQL to run>"  # Could be the same as V1
```

### 4. **JSON Response Parsing**
Responses are strictly JSON formatted for reliable extraction:
```json
{
  "feedback": "The query correctly identifies black as the color with highest sales of $5000.50.",
  "refined_sql": "SELECT color, SUM(qty_delta * unit_price) as total_sales FROM transactions WHERE action='sale' GROUP BY color ORDER BY total_sales DESC LIMIT 1;"
}
```

## Code Structure

### Main Functions

| Function | Purpose |
|----------|---------|
| `generate_sql()` | Creates V1 SQL from question + schema |
| `refine_sql()` | Simple reflection (without execution feedback) |
| `refine_sql_external_feedback()` | **Core reflection** with actual query results |
| `run_sql_workflow()` | Orchestrates the full workflow |

### Data Flow

```
generate_sql()
     ↓ (returns SQL string)
execute_sql()
     ↓ (returns DataFrame)
refine_sql_external_feedback()
     ↓ (receives DataFrame as input)
     ↓ (returns feedback + refined SQL)
execute_sql()
     ↓ (final results)
```

## Example Execution

```
QUESTION: Which color of product has the highest total sales?

--- Step 1: Schema Extracted ---

--- Step 2: Generated SQL V1 ---
SELECT color, SUM(qty_delta * unit_price) as total_sales 
FROM transactions 
GROUP BY color;

--- Step 3: Executing V1 ---
    color  total_sales
    black    5000.50
    white    4500.25
    red      3200.75
    ...

--- Step 4: Reflecting on Execution Results ---
Feedback: The query shows all colors, but should return only the one with the highest total sales. Need to order by total_sales DESC and limit to 1.
Refined SQL V2: SELECT color, SUM(qty_delta * unit_price) as total_sales FROM transactions GROUP BY color ORDER BY total_sales DESC LIMIT 1;

--- Step 5: Executing V2 (Final Answer) ---
    color  total_sales
    black    5000.50
```

## Configuration

The workflow uses Gemini models by default:

```python
run_sql_workflow(
    db_path="products.db",
    question="Your question here",
    model_generation="gemini-3-pro-preview",      # For V1 generation
    model_evaluation="gemini-3-pro-preview"       # For reflection
)
```

You can use different models for generation vs. evaluation if desired.

## Why This Design Works

1. **Real Feedback**: The LLM sees actual data, not assumptions
2. **Error Detection**: Incorrect queries produce wrong results that the LLM can identify
3. **Iterative Improvement**: The system learns from its mistakes
4. **Human-like Reasoning**: Mirrors how humans would debug SQL
5. **Deterministic Output**: JSON parsing ensures reliable response extraction

