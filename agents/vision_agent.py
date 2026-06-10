import os
import base64
import requests
from google import genai
from core.fallback import call_with_fallback, ProviderError

def analyze_image(image_path, prompt):
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
    except Exception:
        return {"provider": "local", "result": f"Could not read image at {image_path}"}
        
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    provider_chain = [
        {
            'provider_name': 'google',
            'api_key': os.environ.get("GOOGLE_AI_KEY"),
            'model': 'gemini-2.5-flash',
            'max_retries': 2,
            'backoff_seconds': [2, 4]
        },
        {
            'provider_name': 'groq',
            'api_key': os.environ.get("GROQ_API_KEY"),
            'model': 'llama-3.2-11b-vision-preview', 
            'max_retries': 2,
            'backoff_seconds': [2, 4]
        },
        {
            'provider_name': 'openrouter',
            'api_key': os.environ.get("OPENROUTER_API_KEY"),
            'model': 'meta-llama/llama-3.2-11b-vision-instruct:free',
            'max_retries': 2,
            'backoff_seconds': [2, 4]
        }
    ]
    
    def vision_call_func(provider):
        name = provider['provider_name']
        api_key = provider['api_key']
        model = provider['model']
        
        if name == 'google':
            client = genai.Client(api_key=api_key)
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        {"mime_type": "image/jpeg", "data": image_bytes},
                        prompt
                    ]
                )
                return response.text
            except Exception as e:
                msg = str(e).lower()
                if '429' in msg or 'quota' in msg:
                    raise ProviderError(429, str(e))
                elif '401' in msg or 'auth' in msg:
                    raise ProviderError(401, str(e))
                else:
                    raise ProviderError(500, str(e))
                    
        else:
            endpoints = {
                'groq': "https://api.groq.com/openai/v1/chat/completions",
                'openrouter': "https://openrouter.ai/api/v1/chat/completions"
            }
            url = endpoints[name]
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            if name == 'openrouter':
                headers["HTTP-Referer"] = "https://github.com/ultimate-ai-agent"
                
            data = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                        ]
                    }
                ],
                "temperature": 0.7
            }
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            else:
                raise ProviderError(resp.status_code, resp.text)
                
    return call_with_fallback(provider_chain, vision_call_func)
