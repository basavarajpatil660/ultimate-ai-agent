import os
import base64
from google import genai as genai_client
import groq

def analyze_image(image_path, prompt, 
                  GOOGLE_AI_KEY=None, 
                  GROQ_API_KEY=None,
                  OPENROUTER_API_KEY=None):
    if GOOGLE_AI_KEY is None:
        GOOGLE_AI_KEY = os.environ.get("GOOGLE_AI_KEY")
    if GROQ_API_KEY is None:
        GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    if OPENROUTER_API_KEY is None:
        OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    
    # Convert image to base64
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(
            f.read()).decode("utf-8")
    
    # Provider 1: Google Gemini Vision
    if GOOGLE_AI_KEY:
        try:
            client = genai_client.Client(
                api_key=GOOGLE_AI_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    {"inline_data": {
                        "mime_type": "image/png",
                        "data": image_data
                    }},
                    prompt
                ]
            )
            return {"result": response.text, "provider": "gemini-vision"}
        except Exception as e:
            print(f"Gemini vision failed: {e}")
    
    # Provider 2: Groq Vision
    if GROQ_API_KEY:
        try:
            client = groq.Groq(api_key=GROQ_API_KEY)
            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url",
                         "image_url": {
                             "url": f"data:image/png;base64,{image_data}"
                         }},
                        {"type": "text", "text": prompt}
                    ]
                }],
                timeout=30
            )
            return {"result": response.choices[0].message.content, "provider": "groq-vision"}
        except Exception as e:
            print(f"Groq vision failed: {e}")
    
    return None
