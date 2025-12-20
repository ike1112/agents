
# Research Agent with Gemini

This project implements an intelligent research agent using Google's **Gemini 2.0 Flash** model (via the `google-genai` SDK). The agent acts as a comprehensive research pipeline that searches for information, synthesizes a report, critiques its own work using a chain-of-thought process, and publishes the final result as a formatted HTML document.

## Features

1.  **Research & Tool Use**:
    *   **arXiv Search**: Finds academic papers and technical abstracts.
    *   **Tavily Search**: Performs general web searches for up-to-date information.
    *   The agent autonomously decides which tools to use based on the user's prompt.

2.  **Sequential Reflection Loop (Chain of Thought)**:
    *   **Step 1 (Critique)**: The agent adopts an "Academic Reviewer" persona to strictly analyze the draft. It identifies strengths, limitations, and specific opportunities for improvement.
    *   **Step 2 (Rewrite)**: The agent switches to an "Editor" persona and rewrites the report, explicitly incorporating the feedback from the critique step.
    *   This separation ensures higher quality output compared to attempting both tasks simultaneously.

3.  **HTML Publishing**:
    *   The final revised text is converted into a clean, well-structured HTML document ready for sharing.

4.  **Component-Level Evaluation**:
    *   **Why**: 
        *   **Efficiency**: Rerunning the entire pipeline (research → reflect → improve) for every small change is expensive and slow.
        *   **Noise Reduction**: Improvements in research quality might be hidden by randomness in later steps (like reflection or formatting). Evaluating the research component in isolation gives a cleaner signal.
        *   **Team Optimization**: Allows different parts of a system to be optimized independently with clear metrics.
    *   **How**:
        *   Extracts all URLs cited in the draft.
        *   Checks them against a trusted list (arXiv, Wikipedia, Nature, .edu, etc.).
        *   Calculates a "Trusted Source Ratio" (passing threshold: 40%).
        *   **Auto-Correction**: If the report fails, the agent automatically retries the research with specific feedback to improve its sources (up to 3 attempts).

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
2.  Print the process of tool usage, draft generation, critique, and rewriting to the console.
3.  Save the final output as `research_report.html` in the current directory.
