import os
import requests
import json
from google import genai
from core.fallback import call_with_fallback, ProviderError

def call_llm(prompt, system_prompt="", truncate=True):
    if truncate:
        prompt = prompt[:4000]
        system_prompt = system_prompt[:4000]
        
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    provider_chain = [
        {
            'provider_name': 'mistral',
            'api_key': os.environ.get("MISTRAL_API_KEY"),
            'model': 'mistral-large-latest',
            'max_retries': 3,
            'backoff_seconds': [2, 4, 8]
        },
        {
            'provider_name': 'cerebras',
            'api_key': os.environ.get("CEREBRAS_API_KEY"),
            'model': 'llama-3.3-70b',
            'max_retries': 3,
            'backoff_seconds': [2, 4, 8]
        },
        {
            'provider_name': 'groq',
            'api_key': os.environ.get("GROQ_API_KEY"),
            'model': 'llama-3.3-70b-versatile',
            'max_retries': 3,
            'backoff_seconds': [2, 4, 8]
        },
        {
            'provider_name': 'openrouter',
            'api_key': os.environ.get("OPENROUTER_API_KEY"),
            'model': 'meta-llama/llama-3.3-70b-instruct:free',
            'max_retries': 3,
            'backoff_seconds': [2, 4, 8]
        },
        {
            'provider_name': 'google',
            'api_key': os.environ.get("GOOGLE_AI_KEY"),
            'model': 'gemini-2.5-flash',
            'max_retries': 3,
            'backoff_seconds': [2, 4, 8]
        }
    ]
    
    def llm_call_func(provider):
        name = provider['provider_name']
        api_key = provider['api_key']
        model = provider['model']
        
        if name == 'google':
            client = genai.Client(api_key=api_key)
            try:
                full_prompt = system_prompt + "\n\n" + prompt if system_prompt else prompt
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=full_prompt
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
                'mistral': "https://api.mistral.ai/v1/chat/completions",
                'cerebras': "https://api.cerebras.ai/v1/chat/completions",
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
                "messages": messages,
                "temperature": 0.7
            }
            
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            if resp.status_code == 200:
                try:
                    return resp.json()['choices'][0]['message']['content']
                except Exception:
                    raise ProviderError(500, "Invalid JSON structure")
            else:
                raise ProviderError(resp.status_code, resp.text)

    return call_with_fallback(provider_chain, llm_call_func)

def call_gemma4(prompt):
    provider_chain = [
        {
            'provider_name': 'openrouter',
            'api_key': os.environ.get("OPENROUTER_API_KEY"),
            'model': 'google/gemma-4-27b-it:free',
            'max_retries': 3,
            'backoff_seconds': [3, 6, 12]
        },
        {
            'provider_name': 'google',
            'api_key': os.environ.get("GOOGLE_AI_KEY"),
            'model': 'gemini-2.5-flash',
            'max_retries': 3,
            'backoff_seconds': [3, 6, 12]
        }
    ]
    
    def gemma_call_func(provider):
        name = provider['provider_name']
        api_key = provider['api_key']
        model = provider['model']
        
        if name == 'google':
            client = genai.Client(api_key=api_key)
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
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
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/ultimate-ai-agent"
            }
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            resp = requests.post(url, headers=headers, json=data, timeout=30)
            if resp.status_code == 200:
                return resp.json()['choices'][0]['message']['content']
            else:
                raise ProviderError(resp.status_code, resp.text)
                
    return call_with_fallback(provider_chain, gemma_call_func)
