# Agentic Chart Generator

This project works as an AI agent that automatically generates, executes, critiques, and refines data visualizations using Google's Gemini models.

## How it Works

The workflow (`chart_agent.py`) operates in a loop:

1.  **Data Loading**: Loads your dataset (e.g., `coffee_sales.csv`).
2.  **Generation (V1)**: Uses `gemini-3-pro-preview` to write Python code (Matplotlib) based on your natural language instructions.
3.  **Execution (V1)**: Executes the generated code to produce the first chart (`chart_v1.png`).
4.  **Reflection**: Using vision capabilities, the agent looks at the V1 chart, compares it to your original instructions, and provides structured feedback.
5.  **Refinement (V2)**: The agent rewrites the code to address the feedback.
6.  **Execution (V2)**: Executes the improved code to produce the final chart (`chart_v2.png`).

## Prerequisites

- Python 3.10+
- A Google Cloud Project with the Gemini API enabled.
- An API Key.

## Setup

1.  **Clone the repository** (or navigate to the folder).
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Dependencies include: `google-genai`, `pandas`, `matplotlib`, `pillow`, `python-dotenv`.*

3.  **Configure API Key**:
    Create a `.env` file in the project root:
    ```env
    GOOGLE_API_KEY=your_actual_api_key_here
    ```

## Usage

1.  **Prepare your data**: Ensure `coffee_sales.csv` (or your target dataset) is in the directory.
2.  **Run the agent**:
    ```bash
    python chart_agent.py
    ```
3.  **View Results**:
    - Check the terminal for progress logs.
    - View the generated images: `drink_sales_v1.png` and `drink_sales_v2.png`.

## Project Structure

- `M2_UGL_1.py`: The main workflow script. Orchestrates the generation and reflection loop.
- `utils.py`: Helper functions for data loading, image handling, and interacting with the `google-genai` SDK.
- `requirements.txt`: Python package dependencies.
