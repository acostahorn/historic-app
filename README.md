 Features

    Impossible Debates: Generate structured, six-turn arguments between any two historical figures.

    AI-Powered Rhetoric: Utilizes advanced LLMs to emulate the speech patterns and ideologies of specific historical personas.

    Responsive Web Interface: A custom-built UI that allows for seamless interaction and session management.

 Tech Stack

    Framework: Flask (Python)

    AI Integration: OpenRouter API / OpenAI API

    Deployment: Hosted on PythonAnywhere

    Version Control: Git & GitHub

 Project Structure

    /app.py: Main Flask application entry point.

    /engine.py: Core logic for AI prompt engineering and API communication.

    /templates/: HTML/CSS structure for the debate interface.

 How it works

The engine takes two historical figures as input and crafts a contextual prompt for the LLM. By maintaining local memory of the conversation, the engine ensures a coherent, multi-turn debate that adheres to the historical beliefs of the chosen personas.
