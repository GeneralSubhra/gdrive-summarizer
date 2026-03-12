# 📄 GDrive Summarizer

> Connect a Google Drive folder or document → extract text from PDFs, DOCXs, TXTs → generate AI summaries via Azure OpenAI → export as PDF or CSV.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![Azure OpenAI](https://img.shields.io/badge/AI-Azure%20OpenAI-0078D4?logo=microsoftazure)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

- 🔐 **Google OAuth2** — Secure read-only Drive access.
- 📁 **Smart Folder Scanning** — Supports Folder IDs OR full Google Drive/Docs URLs.
- 📝 **Robust Text Extraction** — PyMuPDF (PDF), python-docx (DOCX), and native TXT/Markdown/CSV support.
- 🤖 **Azure OpenAI GPT-4o** — High-speed, frontier-level 5–10 sentence summarization.
- 🌐 **Modern Web UI** — Sleek FastAPI-powered interface with real-time status updates.
- 📺 **Descriptive Console Logs** — Watch the progress of downloads, extraction, and summarization live in your terminal.
- 📥 **Flexible Export** — Download summaries as a clean CSV or a professionally formatted PDF report.

---

## 🗂️ Project Structure

```
gdrive-summarizer/
├── app.py              # FastAPI application & route handlers
├── auth.py             # Google OAuth2 integration & token management
├── drive.py            # Google Drive API interaction
├── parser.py           # Document text extraction (PDF, DOCX, etc.)
├── prompts.py          # Centralized AI prompt management
├── summarizer.py       # AI summarization (Azure OpenAI SDK)
├── templates/
│   └── index.html      # Responsive Jinja2 web template
├── requirements.txt    # Python dependencies (FastAPI, OpenAI, etc.)
├── .env                # Environment configuration (Keys & Credits)
└── README.md
```

---

## 🚀 Setup

### 1. Clone & Environment

```bash
git clone https://github.com/GeneralSubhra/gdrive-summarizer.git
cd gdrive-summarizer
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env`

Create a `.env` file from the provided credentials:

```env
FLASK_SECRET_KEY=your_random_secret_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/callback

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-05-01-preview

# Default Config
GDRIVE_FOLDER_ID=root
PORT=5000
```

### 4. Run the App

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

---

## 📖 Usage

1. **Connect**: Sign in with your Google account.
2. **Select**: Paste a **Folder ID** or a **full Google Drive Folder URL**.
3. **Process**: Watch the terminal for live progress as AI summarizes each file.
4. **Review**: Check the summaries in the web table.
5. **Export**: Click "PDF Report" to generate a summary compilation.

---

## 🛡️ Security & Reliability

- **Memory Caching**: Summaries are stored in server-side memory to bypass the 4KB browser cookie limit, allowing you to process dozens of files at once.
- **Traceback Logging**: Full error details are printed to the console for easier troubleshooting.
- **Read-Only**: The app only requests `drive.readonly` access to your files.

---


