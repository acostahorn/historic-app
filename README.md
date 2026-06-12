# Historical Debate Engine

A unique web application that simulates persuasive, civil exchanges between historical figures who never shared a table. This project explores rhetoric, history, and the practical application of Large Language Models (LLMs) in a user-centric web interface.

##  Key Features
* **Cross-Century Debates:** Generate structured, six-turn arguments between any two historical figures.
* **Persona Emulation:** Utilizes advanced prompt engineering to emulate the speech patterns, rhetoric, and ideologies of specific historical personas.
* **Local Memory Persistence:** Tracks conversation flow to maintain context over a multi-turn debate.
* **Modern Interface:** A clean, responsive UI designed for a focused reading experience.

##  Technical Stack
* **Framework:** Flask (Python)
* **Core Logic:** OpenAI/OpenRouter API integration
* **Deployment:** Hosted on PythonAnywhere via Git-based CI/CD
* **Version Control:** Git & GitHub

##  Project Architecture
```text
/
├── app.py          # Main Flask application entry point
├── engine.py       # Core logic for AI prompt engineering & API handling
├── requirements.txt# Project dependencies
├── static/         # CSS and asset files
└── templates/      # HTML structures for the interface
