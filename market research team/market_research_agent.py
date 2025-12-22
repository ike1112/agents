
import base64
import json
import os
import re
import time
from datetime import datetime
from io import BytesIO

import requests
from PIL import Image
from dotenv import load_dotenv

from google import genai
from google.genai import types

# --- Local / project ---
import tools
import utils


load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

client = genai.Client(api_key=api_key)

# =========================
# Agent 1: Market Research
# =========================
def market_research_agent():
    # Agent that searches for trends and matches them with internal products.
    # Uses tools: tavily_search_tool, product_catalog_tool.
    
    utils.log_agent_title_html("Market Research Agent", "🕵️‍♂️")

    prompt_ = f"""
You are a fashion market research agent tasked with preparing a trend analysis for a summer sunglasses campaign.

Your goal:
1. Explore current fashion trends related to sunglasses using web search.
2. Review the internal product catalog to identify items that align with those trends.
3. Recommend one or more products from the catalog that best match emerging trends.
4. If needed, today date is {datetime.now().strftime("%Y-%m-%d")}.

You can call the following tools:
- tavily_search_tool: to discover external web trends.
- product_catalog_tool: to inspect the internal sunglasses catalog.

Once your analysis is complete, summarize:
- The top 2–3 trends you found.
- The product(s) from the catalog that fit these trends.
- A justification of why they are a good fit for the summer campaign.
"""
    
    agent_tools = [tools.tavily_search_tool, tools.product_catalog_tool]
    messages = [
        types.Content(
            role="user",
            parts=[types.Part(text=prompt_)]
        )
    ]

    # Turn Limit for safety (Circuit Breaker)
    turn_count = 0
    max_turns = 5

    # Multi-turn loop for tool use
    while True:
        turn_count += 1
        if turn_count > max_turns:
             print("⚠️ Limit reached. Stopping infinite loop.")
             return {"status": "timeout", "content": "I gathered some info but hit the limit before finalizing the report."}

        try:
            # Reconstruct contents properly with types.Part
            # Note: prompt_ is defined above
            
            response = client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=messages,
                config=types.GenerateContentConfig(
                    tools=agent_tools,
                    temperature=0.7 
                )
            )
        except Exception as e:
            print(f"Error calling Gemini: {e}")
            return {"status": "error", "content": "Error during market research."}
        
        # Check if the model wants to call a function
        function_calls = []
        if response.function_calls:
            function_calls = response.function_calls
        
        if function_calls:
            messages.append(response.candidates[0].content)

            parts_for_response = []
            
            for call in function_calls:
                fn_name = call.name
                fn_args = call.args
                
                utils.log_tool_call_html(fn_name, fn_args)

                # Execute tool
                result = None
                if fn_name == "tavily_search_tool":
                    result = tools.tavily_search_tool(**fn_args)
                elif fn_name == "product_catalog_tool":
                    result = tools.product_catalog_tool(**fn_args)
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                utils.log_tool_result_html(result)

                parts_for_response.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response={"result": result}
                    )
                )
            
            messages.append(types.Content(role="user", parts=parts_for_response))
            continue 

        if response.text:
            final_text = response.text
            utils.log_final_summary_html(final_text)
            return {"status": "success", "content": final_text}
        
        break

    return {"status": "error", "content": "No result found."}


# =========================
# Agent 2: Graphic Designer
# =========================
def graphic_designer_agent(trend_insights: str, caption_style: str = "short punchy", size: str = "1024x1024") -> dict:
    # Uses Gemini to generate a marketing prompt/caption and Imagen 3 to generate the image.
    utils.log_agent_title_html("Graphic Designer Agent", "🎨")

    # Step 1: Generate prompt and caption
    system_message = (
        "You are a visual marketing assistant. Based on the input trend insights, "
        "write a creative and visual prompt for an AI image generation model, and also a short caption."
    )

    user_prompt = f"""
Trend insights:
{trend_insights}

Please output:
1. A vivid, descriptive prompt to guide image generation.
2. A marketing caption in style: {caption_style}.

Respond in this format:
{{"prompt": "...", "caption": "..."}}
"""

    try:
        chat_response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=[
                types.Content(role="user", parts=[types.Part(text=system_message + "\n\n" + user_prompt)])
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json", 
                temperature=0.7
            )
        )
        content = chat_response.text.strip()
        parsed = json.loads(content)
        if isinstance(parsed, list):
            parsed = parsed[0]
            
        prompt = parsed.get("prompt")
        caption = parsed.get("caption")

    except Exception as e:
        print(f"Error generating prompt/caption: {e}")
        return {}

    # Step 2: Generate image using Imagen 3
    try:
        image_response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=prompt,
            config={
                'number_of_images': 1,
            }
        )
        
        if not image_response.generated_images:
             raise ValueError("No images generated.")
             
        img = image_response.generated_images[0].image

        filename = f"generated_img_{datetime.now().strftime('%H%M%S')}.png"
        img.save(filename)
        image_path = filename
        
        image_url = filename 

        utils.log_final_summary_html(f"Generated Image saved at: {image_path}, Prompt: {prompt}")
        
        utils.render_image_with_quote_html(image_path, caption) 

        return {
            "image_url": image_url,
            "prompt": prompt,
            "caption": caption,
            "image_path": image_path  
        }

    except Exception as e:
        print(f"Error generating image: {e}")
        print("⚠️ Falling back to placeholder image so pipeline can continue.")
        
        # Create placeholder
        img = Image.new('RGB', (1024, 1024), color=(73, 109, 137))
        filename = f"placeholder_img_{datetime.now().strftime('%H%M%S')}.png"
        img.save(filename)
        
        image_path = filename
        image_url = filename
        
        utils.log_final_summary_html(f"Placeholder Image saved at: {image_path} (Generation Failed)")
        utils.render_image_with_quote_html(image_path, caption or "Placeholder Caption") 

        return {
            "image_url": image_url,
            "prompt": prompt,
            "caption": caption,
            "image_path": image_path  
        }


# =========================
# Agent 3: Copywriter
# =========================
def copywriter_agent(image_path: str, trend_summary: str, model: str = "gemini-3-pro-preview") -> dict:
    # Uses Gemini (Multimodal) to analyze the image and trends to generate a quote.
    utils.log_agent_title_html("Copywriter Agent", "✍️")

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    user_prompt_text = f"""
Here is a visual marketing image and a trend analysis:

Trend summary:
\"\"\"{trend_summary}\"\"\"

Please return a JSON object like:
{{
  "quote": "A short, elegant campaign phrase (max 12 words)",
  "justification": "Why this quote matches the image and trend"
}}
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(inline_data=types.Blob(data=img_bytes, mime_type="image/png")),
                        types.Part(text=user_prompt_text)
                    ]
                )
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7
            )
        )
        
        content = response.text.strip()
        utils.log_final_summary_html(content)
        parsed = json.loads(content)
        parsed["image_path"] = image_path
        return parsed

    except Exception as e:
        print(f"Error in copywriter: {e}")
        return {"error": str(e)}


# =========================
# Agent 4: Packaging
# =========================
def packaging_agent(trend_summary: str, image_url: str, quote: str, justification: str, output_path: str = "campaign_summary.md") -> str:
    # Packages the campaign assets into a markdown report.
    utils.log_agent_title_html("Packaging Agent", "📦")

    styled_image_html = f"![Campaign Image]({image_url})"

    try:
        response = client.models.generate_content(
            model="gemini-3-pro-preview",
            contents=[
                types.Content(
                     role="user",
                     parts=[types.Part(text=f"""
                         You are a marketing communication expert writing elegant campaign summaries for executives.
                         Please rewrite the following trend summary to be clear, professional, and engaging for a CEO audience:

                         \"\"\"{trend_summary.strip()}\"\"\"
                     """)]
                )
            ],
            config=types.GenerateContentConfig(temperature=0.7)
        )
        beautified_summary = response.text.strip()
        utils.log_tool_result_html(beautified_summary)

        markdown_content = f"""# 🕶️ Summer Sunglasses Campaign – Executive Summary

## 📊 Refined Trend Insights
{beautified_summary}

## 🎯 Campaign Visual
{styled_image_html}

## ✍️ Campaign Quote
{quote.strip()}

## ✅ Why This Works
{justification.strip()}

---
*Report generated on {datetime.now().strftime('%Y-%m-%d')}*
"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return output_path

    except Exception as e:
        print(f"Error packaging: {e}")
        return ""


# =========================
# Pipeline Orchestrator
# =========================
def run_sunglasses_campaign_pipeline() -> dict:
    print("Starting Pipeline...")
    
    # --- Step 1: Market Research ---
    # State Capture: We capture the structured result from the Research Agent.
    research_result = market_research_agent()
    
    if research_result["status"] != "success":
        print(f"🛑 Market Research Failed or Timed Out: {research_result['content']}")
        return {}

    trend_summary = research_result["content"]
    print("✅ Market research completed")
    time.sleep(5) # Respect rate limits

    # --- Step 2: Design ---
    # State Handoff: We pass the 'trend_summary' state into the Designer.
    # The Designer relies on this upstream data to know what to draw.
    visual_result = graphic_designer_agent(trend_insights=trend_summary)
    
    if not visual_result or "error" in visual_result or "image_path" not in visual_result:
        print("Stopping pipeline due to graphic design error or quota limits.")
        return {}
        
    # State Capture: We extract the file path from the complex dict returned.
    image_path = visual_result["image_path"] 
    print("🖼️ Image generated")
    time.sleep(5) # Respect rate limits

    # --- Step 3: Copywriting ---
    # Multi-State Handoff: The Copywriter receives state from BOTH Step 1 (trends) and Step 2 (image).
    # This demonstrates the Orchestrator maintaining context across the entire lifecycle.
    quote_result = copywriter_agent(image_path=image_path, trend_summary=trend_summary)
    quote = quote_result.get("quote", "")
    justification = quote_result.get("justification", "")
    print("💬 Quote created")
    time.sleep(5) # Respect rate limits

    # 4. Packaging
    md_path = packaging_agent(
        trend_summary=trend_summary,
        image_url=image_path,  
        quote=quote,
        justification=justification,
        output_path=f"campaign_summary_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"
    )

    print(f"📦 Report generated: {md_path}")
    
    return {
        "trend_summary": trend_summary,
        "visual": visual_result,
        "quote": quote_result,
        "markdown_path": md_path
    }


if __name__ == "__main__":
    results = run_sunglasses_campaign_pipeline()
    if results and "markdown_path" in results:
        print(f"Pipeline finished successfully! Output file: {results['markdown_path']}")
