# ================================
# Standard library imports
# ================================
import base64
import json
import uuid
from html import escape
from typing import Any

# ================================
# Third-party imports
# ================================
import pandas as pd

# Try importing IPython
try:
    from IPython import get_ipython
    if not get_ipython():
        raise ImportError("Not in IPython")
    from IPython.display import display, HTML
    IS_NOTEBOOK = True
except (ImportError, NameError):
    IS_NOTEBOOK = False
    display = None
    HTML = None


# Generic display helper
def _display_html(html_content: str, plain_text_fallback: str = ""):
    if IS_NOTEBOOK:
        display(HTML(html_content))
    else:
        if plain_text_fallback:
            print(plain_text_fallback)


def render_pretty_table_html(df: pd.DataFrame, title: str = "Data Table") -> str:
    if IS_NOTEBOOK:
        table_html = df.to_html(index=False, classes="styled-table")
        return f"""
        <style>
          .styled-table {{
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
            width: 100%;
            color: black;
            box-shadow: 0 0 5px rgba(0,0,0,0.1);
          }}
          .styled-table th, .styled-table td {{
            border: 1px solid #ddd;
            padding: 8px;
          }}
          .styled-table th {{
            background-color: #007acc;
            color: white;
            text-align: left;
          }}
          .styled-table tr:nth-child(even) {{ background-color: #e6f4ff; }}
          .styled-table tr:nth-child(odd)  {{ background-color: white;    }}
        </style>
        <h3>{escape(title)}</h3>
        {table_html}
        """
    else:
        # Fallback for terminal
        return f"\n--- {title} ---\n{df.to_string(index=False)}\n"


def format_logs_as_pretty_html(logs: list[dict], logo_path: str = "dl_logo.jpg") -> str:
    # This function creates a large HTML string. In terminal, we just simplify it or ignore.
    if IS_NOTEBOOK:
        status_styles = {
            "success": {"bg": "#e0f0ff", "color": "#000000"},
            "fixed":   {"bg": "#fffbe6", "color": "#333333"},
            "error":   {"bg": "#ffe6e6", "color": "#000000"},
        }
        card_blocks = ""
        for log in logs:
            status = log.get("status", "success")
            style = status_styles.get(status, {"bg": "#f4f4f4", "color": "#000000"})
            bg, text_color = style["bg"], style["color"]
            step = escape(str(log.get("step", "")))
            desc = escape(str(log.get("description", "")))
            stxt = escape(str(status))
            card_blocks += f"""
            <div style="display:flex;align-items:center;background-color:{bg};margin:12px 0;
                        padding:12px 16px;border-radius:8px;box-shadow:2px 2px 5px rgba(0,0,0,0.05);">
              <img src="https://coursera-university-assets.s3.amazonaws.com/b4/5cb90bb92f420b99bf323a0356f451/Icon.png"
                   alt="Logo" style="height:60px;margin-right:16px;border-radius:6px;"/>
              <div style="color:{text_color};">
                <h3 style="margin:0 0 4px 0;">Step {step}</h3>
                <p style="margin:4px 0;font-size:14px;">{desc}</p>
                <p style="margin:4px 0;"><strong>Status:</strong> <code>{stxt}</code></p>
              </div>
            </div>
            """
        return f"""
        <div style="font-family:Arial,sans-serif;max-width:800px;margin:auto;">
          <div style="text-align:center;padding:20px 0;">
            <img src="https://learn.deeplearning.ai/assets/dlai-logo.png" alt="Logo" style="max-height:80px;"/>
            <h2 style="margin-top:10px;">Customer Return Workflow Summary</h2>
          </div>
          {card_blocks}
        </div>
        """
    else:
        # Text Summary
        lines = ["--- Workflow Summary ---"]
        for log in logs:
            lines.append(f"Step {log.get('step')}: {log.get('status')} - {log.get('description')}")
        return "\n".join(lines)


def render_image_with_quote_html(image_url: str, quote: str, width: int = 512) -> None:
    if IS_NOTEBOOK:
        html = f"""
        <div style="position:relative;width:{width}px;margin-bottom:20px;">
          <img src="{escape(image_url)}" style="width:100%;border-radius:8px;display:block;">
          <div style="
              position:absolute;bottom:20px;left:50%;transform:translateX(-50%);
              background:rgba(0,0,0,0.6);color:white;padding:10px 20px;border-radius:8px;
              font-size:1.2em;font-family:'Segoe UI',sans-serif;font-weight:500;text-align:center;
              text-shadow:1px 1px 4px #000;">
            {escape(quote)}
          </div>
        </div>
        """
        _display_html(html)
    else:
        print(f"\n[IMAGE RENDERED] path: {image_url}")
        print(f"[OVERLAY QUOTE] {quote}\n")


def log_tool_call_html(tool_name: str, arguments: Any) -> None:
    if IS_NOTEBOOK:
        _display_html(f"""
          <div style="border-left:4px solid #1976D2;padding:.8em;margin:1em 0;
                      background-color:#e3f2fd;color:#0D47A1;font-family:'Segoe UI',sans-serif;">
            <div style="font-size:15px;font-weight:bold;margin-bottom:4px;">
              📞 <span style="color:#0B3D91;">Tool Call:</span> <span style="color:#0B3D91;">{escape(str(tool_name))}</span>
            </div>
            <code style="display:block;background:#e8f0fe;color:#1b1b1b;padding:6px;border-radius:4px;
                         font-size:13px;white-space:pre-wrap;">{escape(str(arguments))}</code>
          </div>
        """)
    else:
        print(f"\n[📞 TOOL CALL] {tool_name}")
        print(f"Args: {arguments}\n")


def log_tool_result_html(result: Any) -> None:
    if IS_NOTEBOOK:
        _display_html(f"""
          <div style="border-left:4px solid #558B2F;padding:.8em;margin:1em 0;
                      background-color:#f1f8e9;color:#33691E;">
            <strong>✅ Tool Result:</strong>
            <pre style="white-space:pre-wrap;font-size:13px;color:#2E7D32;">{escape(str(result))}</pre>
          </div>
        """)
    else:
        print(f"[✅ RESULT] {str(result)[:500]}..." if len(str(result)) > 500 else f"[✅ RESULT] {result}")


def log_final_summary_html(content: str) -> None:
    if IS_NOTEBOOK:
        _display_html(f"""
          <div style="border-left:4px solid #2E7D32;padding:1em;margin:1em 0;
                      background-color:#e8f5e9;color:#1B5E20;">
            <strong>✅ Final Summary:</strong>
            <pre style="white-space:pre-wrap;font-size:13px;color:#1B5E20;">{escape(content.strip())}</pre>
          </div>
        """)
    else:
        print("\n" + "="*40)
        print("✅ FINAL SUMMARY")
        print("="*40)
        print(content.strip() + "\n")


def log_unexpected_html() -> None:
    if IS_NOTEBOOK:
        _display_html("""
          <div style="border-left:4px solid #F57C00;padding:1em;margin:1em 0;
                      background-color:#fff3e0;color:#E65100;">
            <strong>⚠️ Unexpected:</strong> No tool_calls or content returned.
          </div>
        """)
    else:
        print("\n[⚠️ UNEXPECTED] No tool_calls or content returned.\n")


def log_agent_title_html(title: str, icon: str = "🕵️‍♂️") -> None:
    if IS_NOTEBOOK:
        _display_html(f"""
          <div style="padding:1em;margin:1em 0;background-color:#f0f4f8;border-left:6px solid #1976D2;">
            <h2 style="margin:0;color:#0D47A1;font-family:'Segoe UI',sans-serif;">
              {escape(icon)} {escape(title)}
            </h2>
          </div>
        """)
    else:
        print("\n" + "#"*40)
        print(f"{icon} {title}")
        print("#"*40 + "\n")


def print_html(content: Any, title: str | None = None, is_image: bool = False) -> None:
    """
    Pretty-print inside a styled card.
    - If is_image=True and content is a string: treat as image path/URL and render <img>.
    - If content is a pandas DataFrame/Series: render as an HTML table.
    - Otherwise (strings): show as code/text in <pre><code>.
    """
    def image_to_base64(image_path: str) -> str:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    if IS_NOTEBOOK:
        if is_image and isinstance(content, str):
            b64 = image_to_base64(content)
            rendered = f'<img src="data:image/png;base64,{b64}" alt="Image" style="max-width:100%;height:auto;border-radius:8px;">'
        elif isinstance(content, pd.DataFrame):
            rendered = content.to_html(classes="pretty-table", index=False, border=0, escape=False)
        elif isinstance(content, pd.Series):
            rendered = content.to_frame().to_html(classes="pretty-table", border=0, escape=False)
        elif isinstance(content, str):
            rendered = f"<pre><code>{escape(content)}</code></pre>"
        else:
            rendered = f"<pre><code>{escape(str(content))}</code></pre>"

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
          }
          /* 🔒 Scopeado SOLO a la tarjeta */
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
          .pretty-card img { max-width:100%; height:auto; border-radius:8px; }
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
        title_html = f'<div class="pretty-title">{escape(title)}</div>' if title else ""
        card = f'<div class="pretty-card">{title_html}{rendered}</div>'
        if display and HTML:
            display(HTML(css + card))
    else:
        # Terminal Fallback
        if title:
            print(f"--- {title} ---")
        print(content)
        print("")

