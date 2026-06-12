# StudyMate AI

StudyMate AI is an offline AI study assistant for students.

## Features

- Create study subjects
- Upload PDF notes subject-wise
- Extract PDF text with PyMuPDF
- Store searchable note chunks in local ChromaDB
- Chat with uploaded notes using local Ollama models
- Generate quizzes, flashcards, and simple revision plans
- Store app data locally in SQLite

## Setup

Install Python, then run these commands inside this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install Ollama from https://ollama.com, then pull a local model:

```powershell
ollama pull llama3.2
```

Start the Streamlit app:

```powershell
streamlit run app.py
```

If you want to use a different Ollama model, set `OLLAMA_MODEL` before starting Streamlit.

