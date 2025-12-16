import os
import sys
import json
import requests
import qrcode
from qrcode.image.styledpil import StyledPilImage
from datetime import datetime
from dotenv import load_dotenv

from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

def get_current_time():
    """
    Returns the current time as a string.
    """
    return datetime.now().strftime("%H:%M:%S")

def get_weather_from_ip():
    """
    Gets the current, high, and low temperature in Fahrenheit for the user's
    location and returns it to the user.
    """
    try:
        # Get location coordinates from the IP address
        response = requests.get('https://ipinfo.io/json', timeout=10)
        data = response.json()
        if 'loc' not in data:
            return "Could not determine location from IP."
        
        lat, lon = data['loc'].split(',')

        # Set parameters for the weather API call
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m",
            "daily": "temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "auto"
        }

        # Get weather data
        weather_response = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
        weather_data = weather_response.json()

        # Format and return the simplified string
        # Added safe access in case keys are missing
        current_temp = weather_data.get('current', {}).get('temperature_2m', 'N/A')
        daily = weather_data.get('daily', {})
        high = daily.get('temperature_2m_max', ['N/A'])[0]
        low = daily.get('temperature_2m_min', ['N/A'])[0]

        return (
            f"Current: {current_temp}°F, "
            f"High: {high}°F, "
            f"Low: {low}°F"
        )
    except Exception as e:
        return f"Error getting weather: {str(e)}"

def write_txt_file(file_path: str, content: str):
    """
    Write a string into a .txt file (overwrites if exists).
    Args:
        file_path (str): Destination path.
        content (str): Text to write.
    Returns:
        str: Path to the written file.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File written to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def generate_qr_code(data: str, filename: str, image_path: str):
    """Generate a QR code image given data and an image path.

    Args:
        data: Text or URL to encode
        filename: Name for the output PNG file (without extension)
        image_path: Path to the image to be used in the QR code. Must exist.
    """
    try:
        # Check if image_path exists, otherwise standard QR
        if not os.path.exists(image_path):
             return f"Error: Image path '{image_path}' does not exist. Cannot embed image."
        
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
        qr.add_data(data)

        img = qr.make_image(image_factory=StyledPilImage, embedded_image_path=image_path)
        output_file = f"{filename}.png"
        img.save(output_file)

        return f"QR code saved as {output_file} containing: {data[:50]}..."
    except Exception as e:
        return f"Error generating QR code: {str(e)}"


def run_agent():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        return

    print("Initializing Google GenAI Client...")
    client = genai.Client(api_key=api_key)

    # Tool list
    tools_list = [get_current_time, get_weather_from_ip, write_txt_file, generate_qr_code]

    # Prompt
    prompt = "Can you help me create a qr code that goes to www.deeplearning.com from the image dl_logo.jpg, which is located in the tools folder? Also write me a txt note with the current weather please."
    
    print(f"\nUser Prompt: {prompt}\n")
    print("Agent working...")

    # Model configuration
    # Using gemini-2.0-flash-exp for best performance with tools
    model_id = "gemini-2.0-flash-exp" 

    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=tools_list,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    # Enable the model to automatically call functions and handle the execution loop
                    disable=False,
                    # Limit the number of sequential tool calls to prevent infinite loops (e.g. weather -> write_file -> done)
                    maximum_remote_calls=10 
                )
            )
        )
        
        print("\n--- Agent Response ---")
        print(response.text)
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_agent()
