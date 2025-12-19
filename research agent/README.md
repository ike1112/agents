
# Research Agent with Gemini

This project implements an intelligent research agent using Google's **Gemini 2.0 Flash** model (via the `google-genai` SDK). The agent acts as a comprehensive research pipeline that searches for information, synthesizes a report, critiques its own work, and publishes the final result as a formatted HTML document.

## Features

1.  **Research & Tool Use**:
    *   **arXiv Search**: Finds academic papers and technical abstracts.
    *   **Tavily Search**: Performs general web searches for up-to-date information.
    *   The agent autonomously decides which tools to use based on the user's prompt.

2.  **Reflection Loop**:
    *   After generating a preliminary report, the agent adopts a "Reviewer/Editor" persona.
    *   It critiques the report for strengths, limitations, and opportunities.
    *   It rewrites the report to incorporate these improvements.

3.  **HTML Publishing**:
    *   The final revised text is converted into a clean, well-structured HTML document ready for sharing.

## Prerequisites

- **Python 3.10+**
- **API Keys**:
    - `GEMINI_API_KEY`: Get from [Google AI Studio](https://aistudio.google.com/).
    - `TAVILY_API_KEY`: Get from [Tavily](https://tavily.com/).

## Installation

1.  Install the required Python packages (if you haven't already via the root `requirements.txt`):

    ```bash
    pip install google-genai tavily-python python-dotenv
    ```

2.  Create a `.env` file in the project root (or ensure variables are set) containing:

    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    TAVILY_API_KEY=your_tavily_api_key_here
    ```

## Usage

Run the agent script directly:

```bash
python research_agent.py
```

The script will:
1.  Start researching the default topic (currently hardcoded as "Radio observations of recurrent novae" in `main()`).
2.  Print the process of tool usage, draft generation, and reflection to the console.
3.  Save the final output as `research_report.html` in the current directory.
