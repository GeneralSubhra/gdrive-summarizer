"""
auth.py — Google OAuth2 authentication helpers.

Required environment variables:
  GOOGLE_CLIENT_ID
  GOOGLE_CLIENT_SECRET
  GOOGLE_REDIRECT_URI   (e.g. http://localhost:5000/auth/callback)
"""

import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

CLIENT_CONFIG = {
    "web": {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        "redirect_uris": [os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/callback")],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}


def get_auth_url():
    """Generate the Google OAuth2 authorization URL, state, and PKCE code verifier."""
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = CLIENT_CONFIG["web"]["redirect_uris"][0]
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    # flow.code_verifier is auto-generated for PKCE; must be stored for token exchange
    return auth_url, state, flow.code_verifier


def exchange_code_for_credentials(code: str, code_verifier: str = None) -> Credentials:
    """Exchange an authorization code for OAuth2 credentials."""
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = CLIENT_CONFIG["web"]["redirect_uris"][0]
    flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    return flow.credentials


def refresh_credentials_if_needed(credentials: Credentials) -> Credentials:
    """Refresh credentials if they have expired."""
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    return credentials


def credentials_to_dict(credentials: Credentials) -> dict:
    """Serialize credentials to a JSON-safe dict for session storage."""
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes) if credentials.scopes else SCOPES,
    }


def dict_to_credentials(creds_dict: dict) -> Credentials:
    """Deserialize credentials from a session-stored dict."""
    credentials = Credentials(
        token=creds_dict["token"],
        refresh_token=creds_dict.get("refresh_token"),
        token_uri=creds_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=creds_dict.get("client_id"),
        client_secret=creds_dict.get("client_secret"),
        scopes=creds_dict.get("scopes", SCOPES),
    )
    return refresh_credentials_if_needed(credentials)
