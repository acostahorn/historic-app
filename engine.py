import os
from dotenv import load_dotenv
from openai import OpenAI

# 1. Load Environment
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("API key not found.")

default_model = os.getenv("OPENROUTER_DEFAULT_MODEL", "meta-llama/Llama-3.1-8B-Instruct")

# 2. Initialize Client with required OpenRouter headers
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
    default_headers={
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "Historical Debate Engine",
    },
)

import requests

def get_ai_response(system_prompt, history, temperature=0.8, language='English', force_english=False):
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Construct your messages list as before
    messages = [{"role": "system", "content": system_prompt}]
    # ... (Keep your language instruction logic here) ...
    messages.extend(history)

    payload = {
        "model": default_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 800
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "Historical Debate Engine",
        "Content-Type": "application/json"
    }

    try:
        # Use requests directly instead of the OpenAI client
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"DEBUG: Response text: {response.text}")
            return "I am currently unable to respond due to an API error."
            
        data = response.json()
        return data['choices'][0]['message']['content']
        
    except Exception as e:
        print(f"Error calling OpenRouter: {e}")
        return "I am currently unable to respond."