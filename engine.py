import os
import time
import random
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Setup Environment
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing!")

genai.configure(api_key=api_key)

# 2. Define Helper with Resilient Retry Logic
def get_ai_response(system_prompt, history, temperature=0.8, language='English', force_english=False, retry_count=0):
    # Using the most stable model identifier
    model = genai.GenerativeModel('models/gemini-3.1-flash-lite')

    try:
        chat = model.start_chat(history=[])
        chat.send_message(f"SYSTEM: {system_prompt}")
        
        for msg in history:
            chat.send_message(msg['content'])
            
        response = chat.history[-1].parts[0].text
        return response

    except Exception as e:
        # Handle Rate Limiting (429) with Exponential Backoff
        if "429" in str(e) and retry_count < 3:
            wait_time = (2 ** retry_count) + random.uniform(0, 1)
            print(f"DEBUG: Rate limit hit. Retrying in {wait_time:.2f}s...")
            time.sleep(wait_time)
            return get_ai_response(system_prompt, history, temperature, retry_count + 1)
        
        print(f"DEBUG: Critical AI Error: {e}")
        return "I am currently unable to respond due to high traffic."