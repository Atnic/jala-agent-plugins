"""OAuth and service-account credentials for Google Play developer APIs."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request

from runtime import StorageError, profile_by_name, load_secret, update_secret


OAUTH_SCOPES = (
    "https://www.googleapis.com/auth/androidpublisher",
    "https://www.googleapis.com/auth/playdeveloperreporting",
)
OAUTH_AUTHORIZE = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH_TOKEN = "https://oauth2.googleapis.com/token"
CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9._-]+\.apps\.googleusercontent\.com$")


@dataclass(frozen=True)
class OAuthClient:
    client_id: str
    client_secret: str = ""


def new_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def validate_client_id(client_id: str) -> str:
    value = client_id.strip() if isinstance(client_id, str) else ""
    if len(value) > 256 or not CLIENT_ID_RE.fullmatch(value):
        raise ValueError("The uploaded JSON must contain a Google Cloud Desktop OAuth client ID.")
    return value


def validate_oauth_client(value: dict) -> OAuthClient:
    if not isinstance(value, dict) or not isinstance(value.get("installed"), dict):
        raise ValueError("Choose the JSON file downloaded for a Google Cloud Desktop app OAuth client.")
    installed = value["installed"]
    client_id = validate_client_id(installed.get("client_id"))
    client_secret = installed.get("client_secret", "")
    if not isinstance(client_secret, str) or len(client_secret) > 1024:
        raise ValueError("The Desktop OAuth client JSON contains an invalid client secret.")
    return OAuthClient(client_id=client_id, client_secret=client_secret)


def build_authorization_url(client: OAuthClient, redirect_uri: str, state: str, challenge: str) -> str:
    client_id = validate_client_id(client.client_id)
    query = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
    })
    return OAUTH_AUTHORIZE + "?" + query


def exchange_code(client: OAuthClient, code: str, redirect_uri: str, verifier: str) -> dict:
    client_id = validate_client_id(client.client_id)
    if not isinstance(code, str) or not code or len(code) > 8192:
        raise ValueError("Google did not return a valid authorization code.")
    form_data = {
        "client_id": client_id,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    if client.client_secret:
        form_data["client_secret"] = client.client_secret
    form = urllib.parse.urlencode(form_data).encode("ascii")
    request = urllib.request.Request(
        OAUTH_TOKEN,
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            token_data = json.loads(response.read(64 * 1024))
    except urllib.error.HTTPError as error:
        try:
            details = json.loads(error.read(4096)).get("error_description", "")
        except Exception:
            details = ""
        raise ValueError("Google OAuth authorization failed. " + (details[:240] if isinstance(details, str) and details else "Review the Desktop OAuth client JSON and consent configuration, then retry.")) from None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise ValueError("Could not complete Google OAuth. Check the network and retry setup.") from None
    refresh_token = token_data.get("refresh_token")
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in")
    if not isinstance(refresh_token, str) or not refresh_token or not isinstance(access_token, str) or not access_token:
        raise ValueError("Google did not return an offline refresh token. Run setup again and approve the requested access.")
    if not isinstance(expires_in, (int, float)) or expires_in <= 0:
        expires_in = 3600
    return {
        "authType": "oauth",
        "clientId": client_id,
        "clientSecret": client.client_secret,
        "refreshToken": refresh_token,
        "accessToken": access_token,
        "expiry": (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat(),
        "tokenUri": OAUTH_TOKEN,
        "scopes": list(OAUTH_SCOPES),
    }


def validate_service_account(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("type") != "service_account":
        raise ValueError("Choose a Google Cloud service-account JSON key file.")
    client_email = value.get("client_email")
    private_key = value.get("private_key")
    if not isinstance(client_email, str) or not client_email.endswith(".iam.gserviceaccount.com"):
        raise ValueError("The JSON file does not contain a Google Cloud service-account email.")
    if not isinstance(private_key, str) or "-----BEGIN PRIVATE KEY-----" not in private_key:
        raise ValueError("The JSON file does not contain an unencrypted service-account private key.")
    token_uri = value.get("token_uri") or OAUTH_TOKEN
    if token_uri != OAUTH_TOKEN:
        raise ValueError("The service-account JSON uses an unexpected token endpoint. Create a standard Google Cloud service-account key file.")
    copied = dict(value)
    copied["token_uri"] = OAUTH_TOKEN
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        credential = service_account.Credentials.from_service_account_info(copied, scopes=list(OAUTH_SCOPES))
        credential.refresh(Request())
    except Exception:
        raise ValueError("Google could not authenticate this service-account key. Check the JSON file and network, then retry.") from None
    return copied


def _oauth_access_token(profile: dict, secret: dict) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    expiry = None
    if isinstance(secret.get("expiry"), str):
        try:
            expiry = datetime.fromisoformat(secret["expiry"].replace("Z", "+00:00"))
        except ValueError:
            expiry = None
    credentials = Credentials(
        token=secret.get("accessToken"),
        refresh_token=secret["refreshToken"],
        token_uri=OAUTH_TOKEN,
        client_id=secret["clientId"],
        client_secret=secret.get("clientSecret") or None,
        scopes=list(OAUTH_SCOPES),
        expiry=expiry,
    )
    if not credentials.valid:
        try:
            credentials.refresh(Request())
        except Exception:
            raise StorageError(f"Google OAuth for profile {profile['name']!r} needs reauthorization. Run gpc_setup for this profile.") from None
        updated = {
            **secret,
            "accessToken": credentials.token,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else "",
            "refreshToken": credentials.refresh_token or secret["refreshToken"],
        }
        update_secret(profile, updated)
    return credentials.token


def _service_account_access_token(secret: dict) -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account

    try:
        credentials = service_account.Credentials.from_service_account_info(
            secret["serviceAccount"], scopes=list(OAUTH_SCOPES)
        )
        credentials.refresh(Request())
    except Exception:
        raise StorageError("Google could not authenticate the saved service-account key. Reconnect the profile or create a new key.") from None
    if not credentials.token:
        raise StorageError("Google returned no access token for the service-account profile.")
    return credentials.token


def access_token(profile_name: str) -> tuple[str, dict]:
    profile = profile_by_name(profile_name)
    secret = load_secret(profile)
    if profile["authType"] == "oauth":
        return _oauth_access_token(profile, secret), profile
    return _service_account_access_token(secret), profile
