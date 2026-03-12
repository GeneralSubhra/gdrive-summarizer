"""
GDrive Summarizer - Main FastAPI Application
"""

import os
import csv
import io
import traceback
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from auth import get_auth_url, exchange_code_for_credentials, credentials_to_dict, dict_to_credentials
from drive import list_documents, download_document
from parser import extract_text
from summarizer import summarize_text

app = FastAPI(title="GDrive Summarizer")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-in-production"),
)

templates = Jinja2Templates(directory="templates")

# Hardcoded folder ID for testing — override with env var
DEFAULT_FOLDER_ID = os.environ.get("GDRIVE_FOLDER_ID", "root")

# Global cache for summaries to avoid cookie size limits
MEM_CACHE = {
    "summaries": []
}


# ── Flash message helpers ────────────────────────────────────────────────────

def add_flash(request: Request, message: str, category: str = "info"):
    """Append a flash message to the session."""
    flashes = request.session.get("_flashes", [])
    flashes.append({"category": category, "message": message})
    request.session["_flashes"] = flashes


def get_flashes(request: Request):
    """Pop all flash messages from the session."""
    flashes = request.session.pop("_flashes", [])
    return flashes


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def index(request: Request):
    """Landing page — show auth status and folder input."""
    authenticated = "credentials" in request.session
    # Get summaries from local memory cache instead of cookie-based session
    summaries = MEM_CACHE.get("summaries", [])
    folder_id = request.session.get("folder_id", DEFAULT_FOLDER_ID)
    flashes = get_flashes(request)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "authenticated": authenticated,
            "summaries": summaries,
            "folder_id": folder_id,
            "flashes": flashes,
        },
    )


@app.get("/auth/login")
async def login(request: Request):
    """Redirect to Google OAuth2 consent screen."""
    auth_url, state, code_verifier = get_auth_url()
    request.session["oauth_state"] = state
    request.session["code_verifier"] = code_verifier
    return RedirectResponse(url=auth_url)


@app.get("/auth/callback")
async def oauth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    """Handle the OAuth2 callback from Google."""
    if not code:
        add_flash(request, "Authentication failed — no code received.", "error")
        return RedirectResponse(url="/", status_code=303)

    if state != request.session.get("oauth_state"):
        add_flash(request, "State mismatch — possible CSRF attack.", "error")
        return RedirectResponse(url="/", status_code=303)

    try:
        code_verifier = request.session.pop("code_verifier", None)
        credentials = exchange_code_for_credentials(code, code_verifier)
        request.session["credentials"] = credentials_to_dict(credentials)
        add_flash(request, "Successfully authenticated with Google Drive!", "success")
    except Exception as e:
        traceback.print_exc()
        add_flash(request, f"Authentication error: {str(e)}", "error")

    return RedirectResponse(url="/", status_code=303)


@app.get("/auth/logout")
async def logout(request: Request):
    """Clear session and log out."""
    request.session.clear()
    add_flash(request, "Logged out successfully.", "info")
    return RedirectResponse(url="/", status_code=303)


@app.post("/process")
async def process(request: Request, folder_id: str = Form(default="")):
    """List, download, parse, and summarize documents from a Drive folder."""
    if "credentials" not in request.session:
        add_flash(request, "Please authenticate first.", "error")
        return RedirectResponse(url="/", status_code=303)
    import re

    raw_input = folder_id.strip() or DEFAULT_FOLDER_ID

    # Extract ID from common Google Drive/Docs URLs
    id_match = re.search(r'/folders/([a-zA-Z0-9_-]+)', raw_input) or \
               re.search(r'/d/([a-zA-Z0-9_-]+)', raw_input) or \
               re.search(r'id=([a-zA-Z0-9_-]+)', raw_input)
    folder_id = id_match.group(1) if id_match else raw_input

    request.session["folder_id"] = folder_id

    print(f"\n--- Starting processing for Folder ID: {folder_id} ---")
    
    credentials = dict_to_credentials(request.session["credentials"])

    try:
        # 1. List documents
        print(f"[*] Scanning folder...")
        documents = list_documents(credentials, folder_id)
        print(f"[+] Found {len(documents)} document(s).")
        if not documents:
            add_flash(request, "No supported documents found in the specified folder.", "warning")
            return RedirectResponse(url="/", status_code=303)

        summaries = []
        errors = []

        for doc in documents:
            file_name = doc["name"]
            file_id = doc["id"]
            mime_type = doc["mimeType"]
            web_link = doc.get("webViewLink", "#")

            try:
                print(f"\n[{file_name}] Processing...")
                
                # 2. Download document
                print(f"    - Downloading...")
                content_bytes, extension = download_document(credentials, file_id, mime_type)

                # 3. Extract text
                print(f"    - Extracting text...")
                text = extract_text(content_bytes, extension)
                if not text or len(text.strip()) < 50:
                    print(f"    - Error: Could not extract meaningful text.")
                    errors.append(f"{file_name}: Could not extract meaningful text.")
                    continue

                # 4. Summarize
                print(f"    - Generating summary...")
                summary = summarize_text(text, file_name)
                print(f"    - Success! Summary generated.")

                summaries.append({
                    "file_name": file_name,
                    "file_id": file_id,
                    "web_link": web_link,
                    "summary": summary,
                    "char_count": len(text),
                    "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })

            except Exception as e:
                traceback.print_exc()
                errors.append(f"{file_name}: {str(e)}")

        # Store in memory cache to avoid cookie size limits
        MEM_CACHE["summaries"] = summaries

        if errors:
            add_flash(request, f"Processed with {len(errors)} error(s): " + "; ".join(errors), "warning")
        if summaries:
            print(f"\n[✔] Finished! Successfully summarized {len(summaries)} document(s).")
            add_flash(request, f"Successfully summarized {len(summaries)} document(s)!", "success")
        
        print(f"--- Processing complete ---\n")

    except Exception as e:
        traceback.print_exc()
        add_flash(request, f"Error accessing Google Drive: {str(e)}", "error")

    return RedirectResponse(url="/", status_code=303)


@app.get("/download/csv")
async def download_csv(request: Request):
    """Download summaries as a CSV file."""
    summaries = MEM_CACHE.get("summaries", [])
    if not summaries:
        add_flash(request, "No summaries to download.", "warning")
        return RedirectResponse(url="/", status_code=303)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["file_name", "summary", "char_count", "processed_at", "web_link"],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(summaries)

    csv_bytes = output.getvalue().encode("utf-8")
    filename = f"summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/download/pdf")
async def download_pdf(request: Request):
    """Generate and download a PDF report."""
    summaries = MEM_CACHE.get("summaries", [])
    if not summaries:
        add_flash(request, "No summaries to download.", "warning")
        return RedirectResponse(url="/", status_code=303)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.enums import TA_CENTER

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=22,
            textColor=colors.HexColor("#1a1a2e"),
            spaceAfter=6,
            alignment=TA_CENTER,
        )
        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#666688"),
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        heading_style = ParagraphStyle(
            "FileHeading",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#2d2d5e"),
            spaceBefore=14,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#333344"),
            leading=15,
            spaceAfter=6,
        )
        meta_style = ParagraphStyle(
            "Meta",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#9999aa"),
            spaceAfter=10,
        )

        story = []
        story.append(Paragraph("GDrive Document Summaries", title_style))
        story.append(Paragraph(
            f"Generated on {datetime.now().strftime('%B %d, %Y at %H:%M')} · {len(summaries)} document(s)",
            subtitle_style,
        ))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#4a4a8a")))
        story.append(Spacer(1, 16))

        for i, item in enumerate(summaries, 1):
            story.append(Paragraph(f"{i}. {item['file_name']}", heading_style))
            story.append(Paragraph(
                f"Characters: {item['char_count']:,}  ·  Processed: {item['processed_at']}",
                meta_style,
            ))
            story.append(Paragraph(item["summary"], body_style))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#ddddee")))
            story.append(Spacer(1, 8))

        doc.build(story)
        buffer.seek(0)

        filename = f"summaries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except ImportError:
        add_flash(request, "reportlab not installed. Run: pip install reportlab", "error")
        return RedirectResponse(url="/", status_code=303)


@app.get("/api/status")
async def api_status(request: Request):
    """Health check endpoint."""
    return JSONResponse({
        "status": "ok",
        "authenticated": "credentials" in request.session,
        "summaries_count": len(request.session.get("summaries", [])),
    })


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 5000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
