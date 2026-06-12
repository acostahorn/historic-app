import os
from dotenv import load_dotenv
from openai import OpenAI

dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OpenRouter API key not found in environment (OPENROUTER_API_KEY).")

default_model = os.getenv(
    "OPENROUTER_DEFAULT_MODEL",
    "meta-llama/Llama-3.1-8B-Instruct",
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)


def get_ai_response(system_prompt, history, temperature=0.8, language='English', force_english=False):
    messages = [{"role": "system", "content": system_prompt}]

    if force_english:
        lang_instr = "Reply ONLY in English."
    else:
        if (language or "").strip().lower() == "scots":
            lang_instr = (
                "Reply in broad Scots. Never default to modern English. "
                "If the interlocutor seems not to understand, you may add a brief English gloss after the Scots, but keep Scots as the primary language."
            )
        else:
            lang_instr = (
                f"Reply in your native language ({language}). If the interlocutor does not understand, politely ask if they want a translation in English."
            )
    messages.append({"role": "system", "content": lang_instr})
    messages.extend(history)

    try:
        response = client.chat.completions.create(
            model=default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=800,
            timeout=15,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenRouter model {default_model}: {e}")
        return (
            "I am currently unable to respond. (Check your OpenRouter API key "
            "and network connection.)"
        )
