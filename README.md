# StudyMate AI

StudyMate AI is Ali Shair's personal exam preparation workspace for organizing notes, chatting with study material, generating quizzes, reviewing flashcards, and planning revision.

It is built with Streamlit, SQLite, PyMuPDF, ChromaDB, Gemini, optional Ollama local mode, and Demo Mode fallback.

## Features

- Create and delete study subjects
- Email/password login with hashed passwords
- Optional Google sign-in with Streamlit OIDC
- User-isolated subjects, documents, quizzes, flashcards, weak topics, and plans
- Upload PDF and TXT notes subject-wise
- Preview uploaded documents in Study Library
- Extract PDF text with PyMuPDF
- Store searchable note chunks in local ChromaDB
- Chat with uploaded notes
- Generate summaries, quizzes, flashcards, and revision plans
- Store app data locally in SQLite
- Use Gemini by default, Ollama as optional local mode, or Demo Mode as fallback

## Important Security Rule

Never commit real API keys.

This project ignores private files such as:

```text
.env
*.env
.streamlit/secrets.toml
```

Use `.env.example` as a template only. It must contain placeholders, not real keys.

## Multi-User Security Checklist

Before deploying or sharing the app:

1. Keep `.env` and `.streamlit/secrets.toml` private and never commit them.
2. Keep `REQUIRE_USER_API_KEYS=true` for public deployments so each visitor uses their own Gemini/Groq key.
3. Keep the SQLite database and `data/uploads` folder private to the app server.
4. Test with two separate accounts before sharing the app:
   - User A creates subjects and uploads notes.
   - User A logs out.
   - User B signs up and confirms User A data is not visible.
5. Confirm uploaded files are saved under `data/uploads/{user_id}/{subject_id}/`.
6. Confirm Chat, Study Library, Quiz Mode, Flashcards, and Revision Planner only show the logged-in user's data.
7. Do not expose uploaded files through a public static folder.
8. Use Streamlit secrets only for private deployments where a shared app key is intentional.

## Requirements

Install these before running the app:

1. Python 3.10 or newer
2. Git
3. VS Code, recommended
4. A Gemini API key from Google AI Studio

Get a Gemini API key here:

```text
https://aistudio.google.com/app/apikey
```

## Install On A New Computer

### 1. Clone The Repository

Open PowerShell or VS Code terminal and run:

```powershell
git clone https://github.com/infoali014-eng/study-mate-ai.git
cd study-mate-ai
```

If the folder already exists, open it:

```powershell
cd path\to\study-mate-ai
```

### 2. Open The Project In VS Code

Run:

```powershell
code .
```

If `code .` does not work, open VS Code manually, then choose:

```text
File > Open Folder > study-mate-ai
```

### 3. Create A Virtual Environment

Run:

```powershell
python -m venv .venv
```

If your system uses the Python launcher, use:

```powershell
py -m venv .venv
```

### 4. Activate The Virtual Environment

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

After activation, your terminal should show `(.venv)` at the start of the line.

### 5. Install Dependencies

Run:

```powershell
pip install -r requirements.txt
```

This installs Streamlit, PyMuPDF, python-dotenv, and other required packages.

For Streamlit Cloud, the app uses a lightweight built-in vector fallback so deployment stays simple. If you want ChromaDB locally, run:

```powershell
pip install -r requirements-local.txt
```

### 6. Create Your Local Environment File

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Open `.env`:

```powershell
notepad .env
```

Add your own Gemini key:

```text
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

If you do not use Groq, leave the Groq placeholder as it is.

Optional Gemini model setting:

```text
GEMINI_MODEL=gemini-2.0-flash
```

The app uses `gemini-2.0-flash` by default and can try fallback Gemini models when Gemini is busy.

For public deployments, the app is configured to require each visitor to enter their own AI key in AI Settings:

```text
REQUIRE_USER_API_KEYS=true
```

Only set this to `false` for a private app where you intentionally want everyone to use one shared app key.

### 7. Run The App

Start Streamlit:

```powershell
streamlit run app.py
```

If you want a specific port:

```powershell
streamlit run app.py --server.port 8507
```

Open the browser URL shown in the terminal, usually:

```text
http://localhost:8501
```

or:

```text
http://localhost:8507
```

### 8. Configure AI Settings

Inside the app sidebar:

1. Open `AI Settings`
2. Select `Gemini`
3. Confirm Gemini model is `gemini-2.0-flash`
4. Paste your own Gemini API key into the password field
5. Click `Test Gemini Connection`

For public deployments, each user must paste their own key. The key is stored only in that user's current browser session.

## Optional Google Sign-In

The app supports Google sign-in through Streamlit's built-in OIDC login. Email/password login still works if Google is not configured.

### Local Google Login Setup

1. Create OAuth credentials in Google Cloud Console.
2. Add this authorized redirect URI:

```text
http://localhost:8507/oauth2callback
```

Use `8501` instead of `8507` if you run Streamlit on the default port.

3. Copy the example secrets file:

```powershell
Copy-Item .streamlit\secrets.example.toml .streamlit\secrets.toml
```

4. Edit `.streamlit/secrets.toml` and add your real Google OAuth values:

```toml
[auth]
redirect_uri = "http://localhost:8507/oauth2callback"
cookie_secret = "replace_with_a_long_random_secret"

[auth.google]
client_id = "your_google_oauth_client_id_here"
client_secret = "your_google_oauth_client_secret_here"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

5. Restart Streamlit.

`cookie_secret` is any long random string you generate yourself. `client_secret`
must be the real OAuth client secret copied from Google Cloud Console. Do not
leave either value as a placeholder.

### Streamlit Cloud Google Login Setup

In Streamlit Cloud, open your app settings and add the same TOML under **Secrets**.

Use your deployed URL plus `/oauth2callback`:

```text
https://your-app-name.streamlit.app/oauth2callback
```

Also add that exact redirect URI in Google Cloud Console.

Never commit real Google OAuth credentials. `.streamlit/secrets.toml` is ignored by Git.

## Basic Use

1. Open `Dashboard`
2. Create a subject, for example `OOP` or `Database`
3. Open `Upload Notes`
4. Select the subject
5. Upload a PDF or TXT file
6. Open `Study Library` to view uploaded material
7. Open `Chat With Notes` and ask questions from your uploaded notes
8. Use `Quiz Mode`, `Flashcards`, and `Revision Planner` for exam practice

## Optional Ollama Local Mode

Gemini uses the internet and API quota. Ollama is optional if you want local AI mode.

Install Ollama from:

```text
https://ollama.com
```

Then pull a model:

```powershell
ollama pull llama3.2
```

Start the app, open `AI Settings`, and select `Ollama`.

## Demo Mode

If Gemini quota is finished or Ollama is not installed, select `Demo Mode` in AI Settings.

Demo Mode lets you test the app interface without real AI responses.

## Troubleshooting

### PowerShell Blocks Activation

If this command fails:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Gemini API Key Is Missing

For public deployments, open `AI Settings` and paste your own Gemini key into the password field.

For private local development, check that `.env` exists and contains:

```text
GEMINI_API_KEY=your_gemini_api_key_here
REQUIRE_USER_API_KEYS=false
```

Then restart Streamlit:

```powershell
Ctrl + C
streamlit run app.py
```

### Gemini Quota Or 429 Error

If you see quota or rate-limit errors, your key is valid but Google is blocking more requests for now.

You can:

- Wait and retry later
- Use another Gemini API key
- Check quota at `https://ai.dev/rate-limit`
- Switch to `Ollama`
- Switch to `Demo Mode`

### Gemini Model Not Found

Use this model in AI Settings:

```text
gemini-2.0-flash
```

### Uploaded Notes Do Not Answer

Make sure:

- You uploaded notes under the correct subject
- The PDF contains selectable text, not only scanned images
- You selected the same subject in Chat With Notes

## Developer Commands

Check changed files:

```powershell
git status
```

Check file differences:

```powershell
git diff
```

Run a quick syntax check:

```powershell
python -m py_compile app.py modules\ai_engine.py modules\database.py
```

## Safe Git Reminder

Before committing, make sure `.env` is not staged:

```powershell
git status
```

The committed file should be `.env.example`, not `.env`.
