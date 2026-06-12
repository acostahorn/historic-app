# Historical Debate Engine

A web-based platform facilitating impossible historical dialogues, allowing users to engage in civil discourse with legendary figures from the past.

## Project Overview
The Historical Debate Engine bridges the gap between historical perspective and modern inquiry. By leveraging advanced Large Language Model (LLM) technology, it provides a persistent, interactive space where users can challenge the arguments and perspectives of deceased historical figures.

## Technical Architecture & Design
The application is built with a focus on **security**, **portability**, and **low-latency performance**.

### 1. LLM Selection: Gemini 3.1 Flash-Lite
For the core engine, I selected **Gemini 3.1 Flash-Lite**. This model was chosen specifically for its:
* **Latency Efficiency:** Designed for fast inference, providing near-instant responses that simulate a natural, conversational flow.
* **Cost-Effectiveness:** Highly optimized for high-frequency interactive applications.
* **Balanced Reasoning:** Capable of maintaining character persona while providing historically grounded analysis.

### 2. Implementation Technique: Resilient Interaction
To achieve the goal of a stable, long-running debate, the engine utilizes:
* **System Prompting:** Initializing the LLM with a structured persona-base to ensure character consistency throughout the session.
* **Resilient Retry Logic:** The engine includes error handling to manage rate limiting (429 errors) through exponential backoff, ensuring the conversation remains uninterrupted.
* **State Management:** The backend dynamically manages chat history to provide context-aware responses without session bloat.

### 3. Security & Production Standards
I have prioritized a "Production-Ready" security posture:
* **Environment Variable Management:** Secrets (API keys) are decoupled from source code using `python-dotenv` and absolute path resolution, preventing credential exposure.
* **Separation of Concerns:** The WSGI configuration is strictly limited to application entry, while logic and environment configuration are isolated in modular files.

### 4. Integration with Openclaw
The development and maintenance lifecycle is governed by **Openclaw**. Openclaw acts as the project’s autonomous administrative agent, ensuring all file operations are sandboxed and that the project structure remains strictly within its designated directory. This ensures high-integrity file management and prevents unauthorized system interactions during deployment and maintenance.
