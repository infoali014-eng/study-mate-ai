# StudyMate AI

StudyMate AI is a secure, multi-user exam preparation workspace for organizing notes, chatting with study material, generating quizzes, reviewing flashcards, and planning revision.

It is built with Streamlit, SQLite, PyMuPDF, ChromaDB, and Gemini API support.

## Features

- Create and delete study subjects
- Email/password login with hashed passwords
- Manual email/password authentication with hashed passwords
- User-isolated subjects, documents, quizzes, flashcards, weak topics, and plans
- Upload PDF, image, DOCX, PPTX, TXT, and Markdown notes subject-wise
- Preview uploaded documents in Study Library
- Extract text from PDFs, Office files, text files, and OCR-capable images/scanned pages when OCR is available
- Store searchable note chunks in local ChromaDB
- Chat with uploaded notes
- Generate summaries, quizzes, flashcards, and revision plans
- Store app data locally in SQLite
- Use Gemini API for chat, notes, graphs, quizzes, flashcards, and planning

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
2. Keep `REQUIRE_USER_API_KEYS=true` for public deployments so each visitor uses their own Gemini key.
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

This installs Streamlit, PyMuPDF, python-dotenv, Office parsers, OCR helpers, and other required packages.

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
GEMINI_MODEL=gemini-2.0-flash
APP_ENCRYPTION_KEY=replace_with_a_long_random_secret_for_saved_user_keys
```

StudyMate AI uses Gemini as its only hosted AI provider.

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

To let signed-in users save their own Gemini keys securely, set `APP_ENCRYPTION_KEY` in `.env` locally or in Streamlit Cloud secrets. Use a long random value and never commit the real value.

### 6B. Optional: Create The First Admin

StudyMate AI can create an admin account safely from local environment variables or Streamlit secrets.

Add these placeholder-style keys to your private `.env` file locally, or to Streamlit Cloud secrets:

```text
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_secure_admin_password
ADMIN_NAME=Admin User
```

Use your real admin email and a strong password only in private local `.env` or Streamlit Cloud secrets. Never commit real admin credentials.

When the app starts, it checks these values. If both `ADMIN_EMAIL` and `ADMIN_PASSWORD` exist, the admin user is created or updated with a hashed password and role `admin`.

Admin users can:

- Use all normal StudyMate features with their own isolated `user_id`
- Open Admin Dashboard
- Edit branding and About page content
- Manage the announcement banner and simple feature toggles
- View users and activity counts
- Change roles or disable users while protecting the last active admin

Normal student users cannot see admin navigation, and direct admin page access is blocked server-side.

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
2. Confirm `Gemini API` is selected
3. Confirm Gemini model is `gemini-2.0-flash`
4. Paste your own Gemini API key into the password field
5. Click the save button if `APP_ENCRYPTION_KEY` is configured, or use the temporary-session button
6. Click `Test Gemini Connection`

For public deployments, each user must use their own key. Saved keys are encrypted and linked to that user's account. Temporary keys stay only in that user's current browser session.

## Google Sign-In Status

Google sign-in is temporarily disabled. Use email/password signup and login.

The app intentionally does not call `st.login()`, `st.logout()`, or `st.user`
while Google login is disabled, so invalid Google OAuth settings should not
break the app.

Keep real Google OAuth credentials out of the repository. `.streamlit/secrets.toml` is ignored by Git.

When Google auth is restored later, add setup instructions in a new change.

## Basic Use

1. Open `Dashboard`
2. Create a subject, for example `OOP` or `Database`
3. Open `Upload Notes`
4. Select the subject
5. Upload a PDF, image, DOCX, PPTX, TXT, or Markdown file
6. Open `Study Library` to view uploaded material
7. Open `Chat With Notes` and ask questions from your uploaded notes
8. Use `Quiz Mode`, `Flashcards`, and `Revision Planner` for exam practice

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
If the app says API key saving is not configured, add `APP_ENCRYPTION_KEY` in Streamlit secrets or use `Use Temporarily`.

For private local development, check that `.env` exists and contains:

```text
GEMINI_API_KEY=your_gemini_api_key_here
REQUIRE_USER_API_KEYS=false
APP_ENCRYPTION_KEY=replace_with_a_long_random_secret_for_saved_user_keys
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

### Gemini Model Not Found

Use this model in AI Settings:

```text
gemini-2.0-flash
```

### Uploaded Notes Do Not Answer

Make sure:

- You uploaded notes under the correct subject
- The document has extractable text, or OCR is available for scanned/image-based material
- You selected the same subject in Chat With Notes

For OCR on images or scanned PDFs, `pytesseract` is installed by Python requirements, but the system Tesseract binary must also be available on the deployment. If it is missing, uploads still work and Study Library will show an OCR warning.

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
