# Agentic Tools Demo (multi_tool_agent.py)

This project demonstrates how to turn Python functions into tools for an Agentic AI using the **Google GenAI SDK**. The script is a conversion of the `M3_UGL_1.ipynb` notebook, refactored to run as a standalone Python application.

## Overview

The `multi_tool_agent.py` script initializes a Google Gemini model (`gemini-2.0-flash-exp`) and provides it with a set of custom tools. The agent can intelligently select and execute these tools to fulfill complex user prompts, such as checking the weather, writing files, or generating QR codes.

## Features / Tools

The agent has access to the following tools:

1.  **`get_current_time`**: Returns the current system time.
2.  **`get_weather_from_ip`**: Detects location via IP and retrieves current/daily weather (temperature in Fahrenheit).
3.  **`write_txt_file`**: Writes text content to a specified `.txt` file.
4.  **`generate_qr_code`**: Generates a QR code from a string/URL. Supports embedding an image (logo) into the QR code if provided.

## Prerequisites

1.  **Python 3.10+**
2.  **Google GenAI SDK**: This project uses the v2 SDK.
3.  **API Key**: A valid Google Gemini API key is required.

### Installation

Install the required Python packages:

```bash
pip install google-genai qrcode[pil] requests python-dotenv
```

### Configuration

Create a `.env` file in the root directory (parent of `tools/`) and add your API key:

```env
GEMINI_API_KEY=your_actual_api_key_here
```

## Usage

Run the script from the project root:

```bash
python tools/multi_tool_agent.py
```

### Example Interaction

The script is currently hardcoded with a demonstration prompt:
> "Can you help me create a qr code that goes to www.deeplearning.com from the image dl_logo.jpg? Also write me a txt note with the current weather please."

The agent will:
1.  Check the weather for your location.
2.  Write the weather info to a text file.
3.  Attempt to generate a QR code (note: requires `dl_logo.jpg` to exist, otherwise it returns an error which the agent will report).

## Troubleshooting

### Windows PowerShell Activation Error

If you see an error like `cannot be loaded because running scripts is disabled on this system` when trying to activate the virtual environment, it is due to Windows PowerShell's execution policy.

To fix this for your current terminal session, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
```

Then try activating again:

```powershell
.\venv\Scripts\Activate.ps1
```

Alternatively, you can run the script using the virtual environment's Python executable directly without activating:

```powershell
..\venv\Scripts\python.exe multi_tool_agent.py
```
