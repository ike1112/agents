
import os
import sys
import json
import time
import re # Added for evaluation

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Import local tools
import research_tools

# Load environment variables
load_dotenv()

# Initialize Gemini Client
# Ensure GEMINI_API_KEY is in your .env file
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Map tool names to functions
TOOL_MAPPING = {
    "arxiv_search_tool": research_tools.arxiv_search_tool,
    "tavily_search_tool": research_tools.tavily_search_tool,
    "wikipedia_search_tool": research_tools.wikipedia_search_tool
}

# list of preferred domains for Tavily results
TOP_DOMAINS = {
    # General reference / institutions / publishers
    "wikipedia.org", "nature.com", "science.org", "sciencemag.org", "cell.com",
    "mit.edu", "stanford.edu", "harvard.edu", "nasa.gov", "noaa.gov", "europa.eu",

    # CS/AI venues & indexes
    "arxiv.org", "acm.org", "ieee.org", "neurips.cc", "icml.cc", "openreview.net",

    # Other reputable outlets
    "elifesciences.org", "pnas.org", "jmlr.org", "springer.com", "sciencedirect.com",

    # Extra domains (case-specific additions)
    "pbs.org", "nova.edu", "nvcc.edu", "cccco.edu",
    "cfa.harvard.edu", "nrao.edu", # Astronomy specific

    # Well known programming sites
    "codecademy.com", "datacamp.com"
}

# Why component-level evaluations?
# If the problem lies in the research generation (usually the first step), 
# rerunning the entire pipeline (research → reflect → improve) every time can be expensive and noisy.

# Small improvements in research quality may be hidden by randomness introduced by later components.
# By evaluating the research generation alone, you get a clearer signal of whether that component is improving.

# Component-level evals are also efficient when multiple teams are working on different pieces of a system: each team can optimize its own component using a clear metric, without needing to run or wait for full end-to-end tests.

def evaluate_tavily_results(TOP_DOMAINS, raw: str, min_ratio=0.4):
    """
    Evaluate whether plain-text research results mostly come from preferred domains.
    
    How do we evaluate?
    Our evaluation here is objective, and so can be evaluated using code. It has a specific 
    ground truth - the list of preferred sources for trustworthy research. To build the eval, you will:
    1. Extract the URLs cited in the generated report.
    2. Compare them against a predefined list of preferred domains (e.g., arxiv.org, nature.com, nasa.gov).
    3. Compute the ratio of preferred vs. total results.
    4. Return a PASS/FAIL flag along with a Markdown-formatted summary.

    Args:
        TOP_DOMAINS (set[str]): Set of preferred domains (e.g., 'arxiv.org', 'nature.com').
        raw (str): Plain text or Markdown containing URLs.
        min_ratio (float): Minimum preferred ratio required to pass (e.g., 0.4 = 40%).

    Returns:
        tuple[bool, str]: (flag, markdown_report)
            flag -> True if PASS, False if FAIL
            markdown_report -> Markdown-formatted summary of the evaluation
    """

    # Extract URLs from the text
    url_pattern = re.compile(r'https?://[^\s\]\)>\}]+', flags=re.IGNORECASE)
    urls = url_pattern.findall(raw)

    if not urls:
        return False, """### Evaluation — Tavily Preferred Domains
No URLs detected in the provided text. 
Please include links in your research results.
"""

    # Count preferred vs total
    total = len(urls)
    preferred_count = 0
    details = []

    for url in urls:
        try:
            domain = url.split("/")[2] # Extract domain part after http:// or https://
            # Remove 'www.' for cleaner matching if present (not strictly necessary with substring match but good practice)
            if domain.startswith("www."):
                domain = domain[4:]
                
            preferred = any(td in domain for td in TOP_DOMAINS)
            if preferred:
                preferred_count += 1
            details.append(f"- {url} → {'✅ PREFERRED' if preferred else '❌ NOT PREFERRED'}")
        except IndexError:
            # Handle malformed URLs
            details.append(f"- {url} → ⚠️ MALFORMED")

    ratio = preferred_count / total if total > 0 else 0.0
    flag = ratio >= min_ratio

    # Markdown report
    report = f"""
### Evaluation — Tavily Preferred Domains
- Total results: {total}
- Preferred results: {preferred_count}
- Ratio: {ratio:.2%}
- Threshold: {min_ratio:.0%}
- Status: {"✅ PASS" if flag else "❌ FAIL"}

**Details:**
{chr(10).join(details)}
"""
    return flag, report

def generate_research_report_with_tools(prompt: str, model: str = "gemini-2.0-flash-exp", chat_history: list = None) -> tuple[str, list]:
    """
    Generates a research report using Gemini's tool-calling with arXiv and Tavily tools.

    Args:
        prompt (str): The user prompt.
        model (str): Gemini model name.
        chat_history (list): Optional previous history for conversation continuity.

    Returns:
        tuple[str, list]: (Final assistant research report text, Updated chat history)
    """
    
    tools = [research_tools.arxiv_search_tool, research_tools.tavily_search_tool, research_tools.wikipedia_search_tool]

    
    # System instruction (passed via config)

    system_instruction = (
        "You are a research assistant that can search the web, Wikipedia, and arXiv to write detailed, "
        "accurate, and properly sourced research reports.\n\n"
        "Use tools when appropriate (e.g., to find scientific papers or web content).\n"
        "Cite sources whenever relevant. Do NOT omit citations for brevity.\n"
        "When citing a source, YOU MUST PROVIDE THE EXPLICIT URL. Do not just hyperlink text.\n"
        "For example, write: 'source: https://example.com' or '[Title](https://example.com)'.\n"
        "Use an academic tone, organize output into clearly labeled sections, and include "
        "inline citations or footnotes as needed.\n"
        "Do not include placeholder text such as '(citation needed)' or '(citations omitted)'.\n"
        "ALWAYS include a section called 'References' at the end of the report listing the full URLs of all sources used."
    )
    
    config = types.GenerateContentConfig(
        tools=tools,
        temperature=1.0, 
        system_instruction=system_instruction,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True) # We want to handle it manually as per assignment
    )

    # Initialize or update history
    if chat_history:
        history = chat_history
        history.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
    else:
        history = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    
    max_turns = 10
    final_text = ""

    print(f"Starting research on: {prompt}")

    for _ in range(max_turns):
        # Send message (or history) to model
        response = client.models.generate_content(
            model=model,
            contents=history,
            config=config
        )

        # Append assistant response to history
         
        # In Gemini SDK, response.candidates[0].content is the message content
        if not response.candidates:
            print("No candidates returned.")
            break
            
        assistant_content = response.candidates[0].content
        history.append(assistant_content)
        
        # Check for function calls
        function_calls = []
        for part in assistant_content.parts:
            if part.function_call:
                function_calls.append(part.function_call)
        
        if not function_calls:
            # No tool calls, we are done (assuming the model provided text)
            # Find text part
            text_parts = [p.text for p in assistant_content.parts if p.text]
            final_text = "".join(text_parts)
            print("Final answer obtained.")
            break
        
        # Execute tool calls
        function_responses_parts = []
        for call in function_calls:
            tool_name = call.name
            args = call.args
            
            # Convert args to dict (Gemini args are usually dict-like or standard python dict)
            print(f"Tool Call: {tool_name}({args})")
            
            try:
                tool_func = TOOL_MAPPING.get(tool_name)
                if not tool_func:
                    raise ValueError(f"Tool {tool_name} not found")
                
                # Execute tool
                result = tool_func(**args)
            except Exception as e:
                result = {"error": str(e)}
            
            # Create function response part
            function_responses_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name=tool_name,
                        response={"result": result} # Structure depends on what the model expects, usually a dict
                    )
                )
            )
            
        # Append function responses to history
        history.append(types.Content(role="tool", parts=function_responses_parts))
        
    if not final_text:
        final_text = "No final report generated."
        
    return final_text, history


def critique_report(report, model: str = "gemini-2.0-flash-exp", temperature: float = 0.3) -> str:
    """
    Generates a critique of the research report.
    """
    report_text = research_tools.parse_input(report)

    system_prompt = "You are an academic reviewer."
    
    user_prompt = f"""
    Review the following research report and provide a detailed critique.
    Focus on:
    1. Strengths: What is good?
    2. Limitations: What is missing or weak?
    3. Suggestions: Specific actionable advice for improvement.
    4. Opportunities: Areas for further expansion.

    Report to review:
    {report_text}
    """

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_prompt
        )
    )
    
    return response.text.strip()


def rewrite_report(report, critique, model: str = "gemini-2.0-flash-exp", temperature: float = 0.3) -> str:
    """
    Rewrites the research report based on the provided critique.
    """
    report_text = research_tools.parse_input(report)
    
    system_prompt = "You are an academic editor. Improve the report based on the critique."
    
    user_prompt = f"""
    Rewrite the following research report to incorporate the reviewer's critique.
    
    Original Report:
    {report_text}
    
    Reviewer's Critique:
    {critique}
    
    Return ONLY the revised report text.
    """

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_prompt
        )
    )
    
    return response.text.strip()


def convert_report_to_html(report, model: str = "gemini-2.0-flash-exp", temperature: float = 0.5) -> str:
    """
    Converts a plaintext research report into a styled HTML page.
    """
    
    report_text = research_tools.parse_input(report)

    system_prompt = "You convert plaintext reports into full clean HTML documents."
    
    user_prompt = f"""
    Convert the following research report into a well-structured HTML document.
    - Use <h1> for the title, <h2> for sections.
    - format paragraphs, lists, and citations.
    - Make links clickable.
    - Return ONLY the HTML code.
    
    Report:
    {report_text}
    """

    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_prompt,
        response_mime_type="text/plain" # Or text/html if supported/desired, but plain is fine for code generation
    )

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=config
    )
    
    html = response.text.strip()
    # Clean up markdown code blocks if present
    if html.startswith("```html"):
        html = html[7:]
    if html.startswith("```"):
        html = html[3:]
    if html.endswith("```"):
        html = html[:-3]
        
    return html.strip()


def main():
    # Force UTF-8 for stdout/stderr to avoid encoding issues
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    print("=== C1M3 Assignment: Research Agent with Gemini ===\n")
    
    # 1) Research with tools (with retry loop)
    prompt_ = "Radio observations of recurrent novae"
    
    current_prompt = prompt_
    chat_history = None
    max_retries = 3
    preliminary_report = ""
    
    for attempt in range(max_retries):
        print(f"--- Step 1: Generating Report for '{prompt_}' (Attempt {attempt + 1}/{max_retries}) ---")
        
        preliminary_report, chat_history = generate_research_report_with_tools(current_prompt, chat_history=chat_history)
        
        print("\n=== Research Report (preliminary) ===")
        print(preliminary_report)
        print("=====================================\n")

        if not preliminary_report or preliminary_report == "No final report generated.":
            print("Skipping remaining steps due to empty report.")
            return

        # 1.5) Component-Level Evaluation (New Step)
        print("--- Step 1.5: Component-Level Evaluation (Tavily Results) ---")
        pass_flag, eval_report = evaluate_tavily_results(TOP_DOMAINS, preliminary_report)
        print(eval_report)
        
        if pass_flag:
            print("✅ Quality check passed!")
            break
        else:
            print("⚠️ Warning: Research results did not meet the preferred domain threshold.")
            if attempt < max_retries - 1:
                print("♻️ Retrying with feedback...")
                current_prompt = f"The previous report failed quality checks because of low trusted domain usage.\nEvaluator Report:\n{eval_report}\n\nPlease REWRITE the report. Improve your research by citing specifically from preferred domains like Wikipedia, ArXiv, or .edu sites. ENSURE you include the FULL URL for every citation so it can be verified."
            else:
                print("❌ Max retries reached. Stopping execution.")
                return

    print("============================================================\n")

    # 2) Reflection on the report
    print("--- Step 2: Reflection (Critique) ---")
    critique = critique_report(preliminary_report)
    print("\n=== Critique ===")
    print(critique)
    
    print("\n--- Step 2.5: Rewriting based on Critique ---")
    revised_report = rewrite_report(preliminary_report, critique)
    print("\n=== Revised Report ===")
    print(revised_report)
    print("==================================\n")

    # 3) Convert the report to HTML
    print("--- Step 3: Converting to HTML ---")
    html = convert_report_to_html(revised_report)
    
    print("\n=== Generated HTML (preview) ===")
    print(html[:600], "\n... [truncated]\n")
    
    # Save to file
    output_filename = "research_report.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Full HTML saved to {output_filename}")

if __name__ == "__main__":
    main()
