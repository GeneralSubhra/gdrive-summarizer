"""
drive.py — Google Drive API integration.

Lists and downloads supported document types from a given folder.
Supported MIME types: PDF, DOCX, TXT, Google Docs (exported as DOCX).
"""

import io
from typing import Tuple, List, Dict
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials

# Map MIME types → file extensions for parsing
SUPPORTED_MIME_TYPES: Dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".docx",
    "text/plain": ".txt",
    "text/markdown": ".txt",
    "text/csv": ".txt",
    # Google Workspace types — exported on download
    "application/vnd.google-apps.document": ".docx",
}

# Google Docs MIME → export MIME type
GOOGLE_EXPORT_FORMATS: Dict[str, str] = {
    "application/vnd.google-apps.document": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
}


def _build_service(credentials: Credentials):
    """Build and return a Google Drive API service client."""
    return build("drive", "v3", credentials=credentials)


def list_documents(credentials: Credentials, folder_id: str) -> List[Dict]:
    """
    List all supported documents in a Google Drive folder.

    Args:
        credentials: Valid Google OAuth2 credentials.
        folder_id:   The Google Drive folder ID to scan.

    Returns:
        List of dicts with keys: id, name, mimeType, webViewLink.
    """
    service = _build_service(credentials)
    mime_filter = " or ".join(
        f"mimeType='{mime}'" for mime in SUPPORTED_MIME_TYPES
    )
    query = f"'{folder_id}' in parents and ({mime_filter}) and trashed=false"

    results = []
    page_token = None

    while True:
        response = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="nextPageToken, files(id, name, mimeType, webViewLink, size)",
                pageToken=page_token,
                pageSize=50,
            )
            .execute()
        )

        results.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return results


def download_document(
    credentials: Credentials, file_id: str, mime_type: str
) -> Tuple[bytes, str]:
    """
    Download a file from Google Drive.

    For Google Workspace documents (e.g., Google Docs), the file is exported
    to an appropriate format first.

    Args:
        credentials: Valid Google OAuth2 credentials.
        file_id:     The Google Drive file ID.
        mime_type:   The file's MIME type.

    Returns:
        Tuple of (file_bytes, extension_string).
    """
    service = _build_service(credentials)
    extension = SUPPORTED_MIME_TYPES.get(mime_type, ".txt")

    buffer = io.BytesIO()

    if mime_type in GOOGLE_EXPORT_FORMATS:
        # Export Google Workspace format
        export_mime = GOOGLE_EXPORT_FORMATS[mime_type]
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        # Direct binary download
        request = service.files().get_media(fileId=file_id)

    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buffer.getvalue(), extension
