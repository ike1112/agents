
import re
import json
import utils

print("\n--- Loading Data ---")
try:
    df = utils.load_and_prepare_data('coffee_sales.csv')
    # Grab a random sample to display
    print("Random Sample of Coffee Sales Data:")
    print(df.sample(n=5))
except Exception as e:
    print(f"Error loading data: {e}")
    df = None


def generate_chart_code(instruction: str, model: str, out_path_v1: str) -> str:
    """Generate Python code to make a plot with matplotlib using tag-based wrapping."""

    prompt = f"""
    You are a data visualization expert.

    Return your answer *strictly* in this format:

    <execute_python>
    # valid python code here
    </execute_python>

    Do not add explanations, only the tags and the code.

    The code should create a visualization from a DataFrame 'df' with these columns:
    - date (M/D/YY)
    - time (HH:MM)
    - cash_type (card or cash)
    - card (string)
    - price (number)
    - coffee_name (string)
    - quarter (1-4)
    - month (1-12)
    - year (YYYY)

    User instruction: {instruction}

    Requirements for the code:
    1. Assume the DataFrame is already loaded as 'df'.
    2. Use matplotlib for plotting.
    3. Add clear title, axis labels, and legend if needed.
    4. Save the figure as '{out_path_v1}' with dpi=300.
    5. Do not call plt.show().
    6. Close all plots with plt.close().
    7. Add all necessary import python statements

    Return ONLY the code wrapped in <execute_python> tags.
    """

    response = utils.get_response(model, prompt)
    return response



def reflect_on_image_and_regenerate(
    chart_path: str,
    instruction: str,
    model_name: str,
    out_path_v2: str,
    code_v1: str,  
) -> tuple[str, str]:
    """
    Critique the chart IMAGE and the original code against the instruction, 
    then return refined matplotlib code.
    Returns (feedback, refined_code_with_tags).
    Supports Google Gemini.
    """
    media_type, b64 = utils.encode_image_b64(chart_path)
    

    prompt = f"""
    You are a data visualization expert.
    Your task: critique the attached chart and the original code against the given instruction,
    then return improved matplotlib code.

    Original code (for context):
    {code_v1}

    OUTPUT FORMAT (STRICT!):
    1) First line: a valid JSON object with ONLY the "feedback" field.
    Example: {{"feedback": "The legend is unclear and the axis labels overlap."}}

    2) After a newline, output ONLY the refined Python code wrapped in:
    <execute_python>
    ...
    </execute_python>

    3) Import all necessary libraries in the code. Don't assume any imports from the original code.

    HARD CONSTRAINTS:
    - Do NOT include Markdown, backticks, or any extra prose outside the two parts above.
    - Use pandas/matplotlib only (no seaborn).
    - Assume df already exists; do not read from files.
    - Save to '{out_path_v2}' with dpi=300.
    - Always call plt.close() at the end (no plt.show()).
    - Include all necessary import statements.

    Schema (columns available in df):
    - date (M/D/YY)
    - time (HH:MM)
    - cash_type (card or cash)
    - card (string)
    - price (number)
    - coffee_name (string)
    - quarter (1-4)
    - month (1-12)
    - year (YYYY)

    Instruction:
    {instruction}
    """


    # Use Gemini helper
    content = utils.image_gemini_call(model_name, prompt, media_type, b64)

    # --- Parse ONLY the first JSON line (feedback) ---
    lines = content.strip().splitlines()
    json_line = lines[0].strip() if lines else ""

    try:
        obj = json.loads(json_line)
    except Exception as e:
        # Fallback: try to capture the first {...} in all the content
        m_json = re.search(r"\{.*?\}", content, flags=re.DOTALL)
        if m_json:
            try:
                obj = json.loads(m_json.group(0))
            except Exception as e2:
                obj = {"feedback": f"Failed to parse JSON: {e2}", "refined_code": ""}
        else:
            obj = {"feedback": f"Failed to find JSON: {e}", "refined_code": ""}

    # --- Extract refined code from <execute_python>...</execute_python> ---
    m_code = re.search(r"<execute_python>([\s\S]*?)</execute_python>", content)
    refined_code_body = m_code.group(1).strip() if m_code else ""
    refined_code = utils.ensure_execute_python_tags(refined_code_body)

    feedback = str(obj.get("feedback", "")).strip()
    return feedback, refined_code


# ### 4. Put it all together — creating the end-to-end workflow

def run_workflow(
    dataset_path: str,
    user_instructions: str,
    generation_model: str,
    reflection_model: str,   
    image_basename: str = "chart",
):
    """
    End-to-end pipeline:
      1) load dataset
      2) generate V1 code
      3) execute V1 → produce chart_v1.png
      4) reflect on V1 (image + original code) → feedback + refined code
      5) execute V2 → produce chart_v2.png

    Returns a dict with all artifacts (codes, feedback, image paths).
    """
    # 0) Load dataset; utils handles parsing and feature derivations (e.g., year/quarter)
    print("\n[Workflow] Loading Data...")
    df = utils.load_and_prepare_data(dataset_path)
    print("Random Sample of Dataset:")
    print(df.sample(n=5))

    # Paths to store charts
    out_v1 = f"{image_basename}_v1.png"
    out_v2 = f"{image_basename}_v2.png"

    # 1) Generate code (V1)
    print("\n[Workflow] Step 1: Generating chart code (V1)...")
    code_v1 = generate_chart_code(
        instruction=user_instructions,
        model=generation_model,
        out_path_v1=out_v1,
    )
    print("--- V1 Code Generated ---")
    print(code_v1)

    # 2) Execute V1 (hard-coded: extract <execute_python> block and run immediately)
    print("\n[Workflow] Step 2: Executing chart code (V1)...")
    match = re.search(r"<execute_python>([\s\S]*?)</execute_python>", code_v1)
    if match:
        initial_code = match.group(1).strip()
        exec_globals = {"df": df}
        try:
            exec(initial_code, exec_globals)
            print(f"Chart V1 saved to: {out_v1}")
        except Exception as e:
            print(f"Error executing V1 code: {e}")
    else:
        print("No <execute_python> block found in V1 code.")

    # 3) Reflect on V1 (image + original code) to get feedback and refined code (V2)
    print("\n[Workflow] Step 3: Reflecting on V1 (image + code) and generating improvements...")
    feedback, code_v2 = reflect_on_image_and_regenerate(
        chart_path=out_v1,
        instruction=user_instructions,
        model_name=reflection_model,
        out_path_v2=out_v2,
        code_v1=code_v1,  # pass original code for context
    )
    print("--- Reflection Feedback ---")
    print(feedback)
    print("--- V2 Code Generated ---")
    print(code_v2)

    # 4) Execute V2 (hard-coded: extract <execute_python> block and run immediately)
    print("\n[Workflow] Step 4: Executing refined chart code (V2)...")
    match = re.search(r"<execute_python>([\s\S]*?)</execute_python>", code_v2)
    if match:
        reflected_code = match.group(1).strip()
        exec_globals = {"df": df}
        try:
            exec(reflected_code, exec_globals)
            print(f"Chart V2 saved to: {out_v2}")
        except Exception as e:
            print(f"Error executing V2 code: {e}")
    else:
        print("No <execute_python> block found in V2 code.")

    return {
        "code_v1": code_v1,
        "chart_v1": out_v1,
        "feedback": feedback,
        "code_v2": code_v2,
        "chart_v2": out_v2,
    }


# ### 4.2. Try the workflow

if __name__ == "__main__":
    print("\n--- Starting Main Execution ---")
    
    # You can change these parameters
    user_instructions = "Create a plot comparing Q1 coffee sales in 2024 and 2025 using the data in coffee_sales.csv."
    generation_model = "gemini-3-pro-preview"
    reflection_model = "gemini-3-pro-preview"
    image_basename = "drink_sales"

    print(f"Instruction: {user_instructions}")

    if df is not None:
        # Run the complete agentic workflow
        try:
            _ = run_workflow(
                dataset_path="coffee_sales.csv",
                user_instructions=user_instructions,
                generation_model=generation_model,
                reflection_model=reflection_model,
                image_basename=image_basename
            )
            print("\n--- Workflow Completed ---")
        except Exception as e:
                print(f"Workflow failed: {e}")
    else:
        print("Data parsing failed, cannot run workflow.")
