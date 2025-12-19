
import os
import sys
import json
import time
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
    "tavily_search_tool": research_tools.tavily_search_tool
}

def generate_research_report_with_tools(prompt: str, model: str = "gemini-2.0-flash-exp") -> str:
    """
    Generates a research report using Gemini's tool-calling with arXiv and Tavily tools.

    Args:
        prompt (str): The user prompt.
        model (str): Gemini model name.

    Returns:
        str: Final assistant research report text.
    """
    
    # helper to convert python function to tool declaration if needed, 
    # but google-genai SDK handles functions directly in 'tools' config.
    tools = [research_tools.arxiv_search_tool, research_tools.tavily_search_tool]
    
    # We will use a chat session to maintain history easily, 
    # or we can manually manage messages as the assignment originally did.
    # To be closer to the "manual loop" exercise of the assignment, let's manage history manually
    # but use the SDK's chat interface which is cleaner for Gemini.
    
    # However, to strictly follow the "manual tool execution" pattern:
    # chat = client.chats.create(model=model)
    
    # System instruction (Gemini 2.0 supports system_instruction at client/chat level, 
    # but here we can just pass it as the first part of the prompt or configure it)
    system_instruction = (
        "You are a research assistant that can search the web and arXiv to write detailed, "
        "accurate, and properly sourced research reports.\n\n"
        "Use tools when appropriate (e.g., to find scientific papers or web content).\n"
        "Cite sources whenever relevant. Do NOT omit citations for brevity.\n"
        "When possible, include full URLs (arXiv links, web sources, etc.).\n"
        "Use an academic tone, organize output into clearly labeled sections, and include "
        "inline citations or footnotes as needed.\n"
        "Do not include placeholder text such as '(citation needed)' or '(citations omitted)'."
    )
    
    # In 'google-genai', we can set system_instruction in config
    config = types.GenerateContentConfig(
        tools=tools,
        temperature=1.0, 
        system_instruction=system_instruction,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True) # We want to handle it manually as per assignment
    )

    # Initial message
    history = [types.Content(role="user", parts=[types.Part(text=prompt)])]
    
    max_turns = 10
    final_text = ""

    print(f"Starting research on: {prompt}")

    for _ in range(max_turns):
        # Send message (or history) to model
        # For manual loop with history, we use chat.send_message but need to be careful with history sync.
        # Easier to just use client.models.generate_content with full history.
        
        response = client.models.generate_content(
            model=model,
            contents=history,
            config=config
        )

        # Append assistant response to history
        # Note: Gemini response might have function calls.
        
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
            print("Final answer:")
            print(final_text)
            break
        
        # Execute tool calls
        function_responses_parts = []
        for call in function_calls:
            tool_name = call.name
            args = call.args
            
            # Convert args to dict (Gemini args are usually dict-like or standard python dict)
            # The SDK handles this well.
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
        
    return final_text if final_text else "No final report generated."


def reflection_and_rewrite(report, model: str = "gemini-2.0-flash-exp", temperature: float = 0.3) -> dict:
    """
    Generates a structured reflection AND a revised research report.
    Accepts raw text.
    """
    
    report_text = research_tools.parse_input(report)

    system_prompt = "You are an academic reviewer and editor."
    
    user_prompt = f"""
    Review the following research report and provide:
    1. A reflection on its strengths, limitations, suggestions for improvement, and opportunities.
    2. A revised version of the report that incorporates these improvements.

    Report to review:
    {report_text}
    """

    # We want JSON output
    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_prompt,
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "reflection": {"type": "STRING"},
                "revised_report": {"type": "STRING"}
            },
            "required": ["reflection", "revised_report"]
        }
    )

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=config
    )
    
    # Parse JSON
    try:
        # In strictly typed SDK, response.text might work if mime_type is json, 
        # or we might need to access parsed fields if using automatic parsing (not yet standard in all SDK versions).
        # Safe way:
        llm_output = response.text
        data = json.loads(llm_output)
        
        return {
            "reflection": data.get("reflection", "").strip(),
            "revised_report": data.get("revised_report", "").strip()
        }
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return {"reflection": "Error", "revised_report": "Error"}


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
    
    # 1) Research with tools
    prompt_ = "Radio observations of recurrent novae"
    print(f"--- Step 1: Generating Report for '{prompt_}' ---")
    preliminary_report = generate_research_report_with_tools(prompt_)
    print("\n=== Research Report (preliminary) ===")
    print(preliminary_report)
    print("=====================================\n")

    if not preliminary_report or preliminary_report == "No final report generated.":
        print("Skipping remaining steps due to empty report.")
        return

    # 2) Reflection on the report
    print("--- Step 2: Reflection and Rewrite ---")
    reflection_text = reflection_and_rewrite(preliminary_report)
    print("\n=== Reflection on Report ===")
    print(reflection_text['reflection'])
    print("\n=== Revised Report ===")
    print(reflection_text['revised_report'])
    print("==================================\n")

    # 3) Convert the report to HTML
    print("--- Step 3: Converting to HTML ---")
    html = convert_report_to_html(reflection_text['revised_report'])
    
    print("\n=== Generated HTML (preview) ===")
    print(html[:600], "\n... [truncated]\n")
    
    # Save to file
    output_filename = "research_report.html"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Full HTML saved to {output_filename}")

if __name__ == "__main__":
    main()
