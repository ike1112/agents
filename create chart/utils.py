# === Standard Library ===
import os
import re
import json
import base64
import mimetypes
from pathlib import Path
import matplotlib.pyplot as plt
from google import genai
from google.genai import types
from html import escape
from PIL import Image
import pandas as pd
from typing import Any
from dotenv import load_dotenv


load_dotenv()

# Configure Gemini
gemini_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
client = None
if gemini_api_key:
    client = genai.Client(api_key=gemini_api_key)


def get_response(model: str, prompt: str) -> str:
    #https://ai.google.dev/gemini-api/docs/gemini-3?_gl=1*1ona0hk*_up*MQ..&gclid=Cj0KCQiA6NTJBhDEARIsAB7QHD27_qizc81J6NA7pmFRUz8tDmkM3azP7chB2aLKLZIQV9aNTBrOSocaAvaIEALw_wcB&gclsrc=aw.ds&gbraid=0AAAAACn9t66UVn4QMoN0wUam60_oxefKk
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )
    return response.text
    
# === Data Loading ===
def load_and_prepare_data(csv_path: str) -> pd.DataFrame:
    """Load CSV and derive date parts commonly used in charts."""
    df = pd.read_csv(csv_path)
    # Be tolerant if 'date' exists
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["quarter"] = df["date"].dt.quarter
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year
    return df

# === Helpers ===
def make_schema_text(df: pd.DataFrame) -> str:
    """Return a human-readable schema from a DataFrame."""
    return "\n".join(f"- {c}: {dt}" for c, dt in df.dtypes.items())

def ensure_execute_python_tags(text: str) -> str:
    """Normalize code to be wrapped in <execute_python>...</execute_python>."""
    text = text.strip()
    # Strip ```python fences if present
    text = re.sub(r"^```(?:python)?\s*|\s*```$", "", text).strip()
    if "<execute_python>" not in text:
        text = f"<execute_python>\n{text}\n</execute_python>"
    return text

def encode_image_b64(path: str) -> tuple[str, str]:
    """Return (media_type, base64_str) for an image file path."""
    mime, _ = mimetypes.guess_type(path)
    media_type = mime or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return media_type, b64



try:
    from IPython.display import HTML, display
    _HAS_IPYTHON = True
except ImportError:
    _HAS_IPYTHON = False
    def display(obj):
        pass # No-op in terminal if IPython missing
    def HTML(obj):
        return obj


def print_html(content: Any, title: str | None = None, is_image: bool = False):
    """
    Pretty-print inside a styled card (Notebook) or plain text (Terminal).
    """
    # Plain text fallback for terminal
    if not _HAS_IPYTHON:
        if title:
            print(f"\n=== {title} ===")
        if is_image:
             if isinstance(content, str):
                print(f"[Image saved to: {content}]")
        else:
            print(str(content))
        return

    # Original Notebook Logic
    try:
        from html import escape as _escape
    except ImportError:
        _escape = lambda x: x


    def image_to_base64(image_path: str) -> str:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    # Render content
    if is_image and isinstance(content, str):
        b64 = image_to_base64(content)
        rendered = f'<img src="data:image/png;base64,{b64}" alt="Image" style="max-width:100%; height:auto; border-radius:8px;">'
    elif isinstance(content, pd.DataFrame):
        rendered = content.to_html(classes="pretty-table", index=False, border=0, escape=False)
    elif isinstance(content, pd.Series):
        rendered = content.to_frame().to_html(classes="pretty-table", border=0, escape=False)
    elif isinstance(content, str):
        rendered = f"<pre><code>{_escape(content)}</code></pre>"
    else:
        rendered = f"<pre><code>{_escape(str(content))}</code></pre>"

    css = """
    <style>
    .pretty-card{
      font-family: ui-sans-serif, system-ui;
      border: 2px solid transparent;
      border-radius: 14px;
      padding: 14px 16px;
      margin: 10px 0;
      background: linear-gradient(#fff, #fff) padding-box,
                  linear-gradient(135deg, #3b82f6, #9333ea) border-box;
      color: #111;
      box-shadow: 0 4px 12px rgba(0,0,0,.08);
    }
    .pretty-title{
      font-weight:700;
      margin-bottom:8px;
      font-size:14px;
      color:#111;
      font-size:14px;
      color:#111;
    }
    /* 🔒 Only affects INSIDE the card */
    .pretty-card pre, 
    .pretty-card code {
      background: #f3f4f6;
      color: #111;
      padding: 8px;
      border-radius: 8px;
      display: block;
      overflow-x: auto;
      font-size: 13px;
      white-space: pre-wrap;
    }
    .pretty-card img { max-width: 100%; height: auto; border-radius: 8px; }
    .pretty-card table.pretty-table {
      border-collapse: collapse;
      width: 100%;
      font-size: 13px;
      color: #111;
    }
    .pretty-card table.pretty-table th, 
    .pretty-card table.pretty-table td {
      border: 1px solid #e5e7eb;
      padding: 6px 8px;
      text-align: left;
    }
    .pretty-card table.pretty-table th { background: #f9fafb; font-weight: 600; }
    </style>
    """

    title_html = f'<div class="pretty-title">{title}</div>' if title else ""
    card = f'<div class="pretty-card">{title_html}{rendered}</div>'
    display(HTML(css + card))

    

    

def image_gemini_call(model_name: str, prompt: str, media_type: str, b64: str) -> str:
    """
    Call Google Gemini with text + image using google-genai SDK.
    """
    if not client:
         raise ValueError("Gemini client not initialized. Check API key.")

    # Convert base64 back to bytes
    image_data = base64.b64decode(b64)
    
    # Create the image part using types
    image_part = types.Part.from_bytes(data=image_data, mime_type=media_type)
    
    response = client.models.generate_content(
        model=model_name,
        contents=[prompt, image_part]
    )
    
    return response.text