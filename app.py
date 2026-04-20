import os
from flask import Flask, render_template, request, jsonify
# We will create characters.py next to handle the 'brains'
from characters import characters_db
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route('/')
def index():
    # This sends our list of characters to the index.html page
    return render_template('index.html', characters=characters_db)

@app.route('/chat/<char_id>', methods=['GET', 'POST'])
def chat_page(char_id):
    # This finds the specific character (like 'leonardo') in our dictionary
    character = characters_db.get(char_id)
    if not character:
        return "Character not found", 404
    if request.method == 'POST':
        user_text = request.json.get('message')
        messages = [{"role": "system", "content": character.persona}]
        messages.extend(character.memory)
        messages.append({"role": "user", "content": user_text})
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages = messages,
        )
        reply= response.choices[0].message.content
        character.memory.append({"role": "user", "content": user_text})
        character.memory.append({"role": "assistant", "content": reply})
        character.save_memory()
        return jsonify({
            "name": character.name,
            "reply": reply
        })
    
    return render_template('chat.html', character=character)

if __name__ == '__main__':
    app.run(debug=True)

if __name__ == '__main__':
# You can change 5000 to 5001, 8080, etc.
    app.run(debug=True, host='127.0.0.1', port=5000)