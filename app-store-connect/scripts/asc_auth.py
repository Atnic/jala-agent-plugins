"""App Store Connect API key token creation."""

from __future__ import annotations

import base64
import json
import time

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def make_jwt(connection: dict) -> str:
    """Sign an App Store Connect ES256 token for a team or individual key."""
    header = {"alg": "ES256", "kid": connection["key_id"], "typ": "JWT"}
    issued_at = int(time.time())
    claims = {"iat": issued_at, "exp": issued_at + 15 * 60, "aud": "appstoreconnect-v1"}
    if connection["key_type"] == "team":
        claims["iss"] = connection["issuer_id"]
    else:
        claims["sub"] = "user"

    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}."
        f"{_b64url(json.dumps(claims, separators=(',', ':')).encode())}"
    )
    key = serialization.load_pem_private_key(connection["private_key"].encode("utf-8"), password=None)
    if not isinstance(key, ec.EllipticCurvePrivateKey) or key.curve.name != "secp256r1":
        raise ValueError("The .p8 key must be an unencrypted P-256 private key.")
    der_signature = key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_signature)
    signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{signing_input}.{_b64url(signature)}"
