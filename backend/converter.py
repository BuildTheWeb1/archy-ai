"""
DWG/DXF → PDF via APS Model Derivative API.

Pipeline:
  1. Authenticate (2-legged OAuth, scopes: data:read data:write bucket:create)
  2. Ensure OSS bucket exists
  3. Upload DWG/DXF to OSS via signed S3 URL
  4. Submit Model Derivative translation job (PDF output)
  5. Poll manifest until status = "success"
  6. Find PDF derivative URN in manifest
  7. Download PDF via signed CloudFront URL + cookies

Requires APS_CLIENT_ID and APS_CLIENT_SECRET env vars.
"""

import base64
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

APS_BASE      = "https://developer.api.autodesk.com"
MD_BASE       = f"{APS_BASE}/modelderivative/v2"
POLL_INTERVAL = 5    # seconds between manifest polls
POLL_TIMEOUT  = 600  # 10 minutes


class ConversionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@dataclass
class _CachedToken:
    access_token: str
    expires_at: float

_token_cache: _CachedToken | None = None


def _get_credentials() -> tuple[str, str]:
    client_id     = os.environ.get("APS_CLIENT_ID", "").strip()
    client_secret = os.environ.get("APS_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise ConversionError("APS_CLIENT_ID and APS_CLIENT_SECRET must be set in .env")
    return client_id, client_secret


def _get_token(client_id: str, client_secret: str) -> str:
    """Return a valid 2-legged OAuth token, refreshing when within 60s of expiry."""
    global _token_cache
    now = time.time()
    if _token_cache is not None and _token_cache.expires_at > now + 60:
        return _token_cache.access_token

    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        f"{APS_BASE}/authentication/v2/token",
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type":  "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "client_credentials",
            "scope":      "data:read data:write data:create viewables:read bucket:create bucket:read bucket:delete",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise ConversionError(f"APS auth failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    _token_cache = _CachedToken(
        access_token=data["access_token"],
        expires_at=now + data.get("expires_in", 1799),
    )
    return _token_cache.access_token


# ---------------------------------------------------------------------------
# OSS — Object Storage Service
# ---------------------------------------------------------------------------

def _bucket_key(client_id: str) -> str:
    """Deterministic, globally-unique bucket key derived from client_id."""
    suffix = hashlib.sha256(client_id.encode()).hexdigest()[:12]
    return f"archyai-{suffix}"


def _ensure_bucket(token: str, bucket: str) -> None:
    resp = requests.post(
        f"{APS_BASE}/oss/v2/buckets",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"bucketKey": bucket, "policyKey": "transient"},
        timeout=30,
    )
    if resp.status_code not in (200, 201, 409):
        raise ConversionError(f"OSS bucket creation failed ({resp.status_code}): {resp.text}")


def _upload_to_oss(token: str, bucket: str, object_key: str, file_path: Path) -> str:
    """Upload file to OSS via signed S3 URL. Returns the raw OSS objectId (URN)."""
    init = requests.get(
        f"{APS_BASE}/oss/v2/buckets/{bucket}/objects/{object_key}/signeds3upload",
        headers={"Authorization": f"Bearer {token}"},
        params={"minutesExpiration": 60},
        timeout=30,
    )
    if init.status_code != 200:
        raise ConversionError(f"OSS signed upload URL failed ({init.status_code}): {init.text}")

    upload_data = init.json()
    upload_key  = upload_data["uploadKey"]
    s3_url      = upload_data["urls"][0]

    logger.info("Uploading %s to APS OSS…", file_path.name)
    with open(file_path, "rb") as fh:
        put = requests.put(
            s3_url,
            data=fh,
            headers={"Content-Type": "application/octet-stream"},
            timeout=300,
        )
    if put.status_code not in (200, 204):
        raise ConversionError(f"S3 upload failed ({put.status_code}): {put.text}")

    fin = requests.post(
        f"{APS_BASE}/oss/v2/buckets/{bucket}/objects/{object_key}/signeds3upload",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "uploadKey":             upload_key,
            "ossbucketKey":          bucket,
            "ossSourceFileObjectKey": object_key,
            "access":                "full",
        },
        timeout=30,
    )
    if fin.status_code not in (200, 201):
        raise ConversionError(f"OSS finalization failed ({fin.status_code}): {fin.text}")

    object_id = fin.json()["objectId"]
    logger.info("Upload complete. objectId: %s", object_id)
    return object_id


def _encode_urn(object_id: str) -> str:
    """Base64-encode the OSS objectId to a URL-safe URN without padding."""
    return base64.urlsafe_b64encode(object_id.encode()).decode().rstrip("=")


# ---------------------------------------------------------------------------
# Model Derivative
# ---------------------------------------------------------------------------

def _start_translation(token: str, urn: str) -> None:
    # DWG → PDF via Model Derivative requires translating to SVF2 with
    # "2dviews": "pdf" advanced option. Requesting "type": "pdf" directly
    # is not supported for DWG input and returns 400.
    resp = requests.post(
        f"{MD_BASE}/designdata/job",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        json={
            "input":  {"urn": urn},
            "output": {
                "formats": [{
                    "type":     "svf2",
                    "views":    ["2d"],
                    "advanced": {"2dviews": "pdf"},
                }],
            },
        },
        timeout=30,
    )
    logger.info("Translation job URN sent: %s", urn)
    logger.info("Translation job (%s): %s", resp.status_code, resp.text)
    if resp.status_code not in (200, 201):
        raise ConversionError(f"Translation job failed ({resp.status_code}): {resp.text}")


def _poll_manifest(token: str, urn: str) -> dict:
    """Poll until manifest status is 'success'. Returns the manifest dict."""
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        resp = requests.get(
            f"{MD_BASE}/designdata/{urn}/manifest",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise ConversionError(f"Manifest poll failed ({resp.status_code}): {resp.text}")

        manifest = resp.json()
        status   = manifest.get("status", "")
        progress = manifest.get("progress", "")
        logger.info("Manifest status: %s (%s)", status, progress)

        if status == "success":
            return manifest
        if status == "failed":
            raise ConversionError(f"Translation failed. Manifest: {manifest}")

        time.sleep(POLL_INTERVAL)

    raise ConversionError(f"Translation timed out after {POLL_TIMEOUT}s")


def _find_pdf_derivatives(manifest: dict) -> list[tuple[str, str]]:
    """
    Return [(layout_name, derivative_urn), ...] for every PDF-page derivative
    found in the SVF2 translation manifest.

    DWG 2D layouts appear as children with role="2d". Each has a grandchild
    with role="pdf-page" when the advanced "2dviews": "pdf" option was used.
    """
    results: list[tuple[str, str]] = []
    for derivative in manifest.get("derivatives", []):
        for child in derivative.get("children", []):
            if child.get("role") != "2d":
                continue
            name = child.get("name", f"layout_{len(results)}")
            for grandchild in child.get("children", []):
                if grandchild.get("role") == "pdf-page" and grandchild.get("status") == "success":
                    results.append((name, grandchild["urn"]))
    if not results:
        raise ConversionError(
            "No pdf-page derivatives found in manifest. "
            "Manifest summary: " + str({
                "status": manifest.get("status"),
                "derivatives": [
                    {"outputType": d.get("outputType"), "status": d.get("status")}
                    for d in manifest.get("derivatives", [])
                ],
            })
        )
    return results


def _download_derivative(token: str, urn: str, derivative_urn: str, output_path: Path) -> None:
    """Download a derivative via the signed CloudFront URL + cookies."""
    encoded_deriv_urn = quote(derivative_urn, safe="")
    resp = requests.get(
        f"{MD_BASE}/designdata/{urn}/manifest/{encoded_deriv_urn}/signedcookies",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise ConversionError(f"Signed cookies request failed ({resp.status_code}): {resp.text}")

    dl_url = resp.json()["url"]
    logger.info("Downloading PDF derivative…")

    dl = requests.get(dl_url, cookies=resp.cookies, timeout=300)
    if dl.status_code != 200:
        raise ConversionError(f"PDF download failed ({dl.status_code}): {dl.text[:200]}")

    output_path.write_bytes(dl.content)
    logger.info("Downloaded %s (%d KB)", output_path.name, len(dl.content) // 1024)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_dwg_to_pdfs(dwg_path: str, output_dir: str) -> list[tuple[str, Path]]:
    """
    Convert a DWG/DXF file to per-layout PDFs via APS Model Derivative API.

    Returns [(layout_name, pdf_path), ...] — one entry per 2D layout.
    PDFs are written to output_dir/{index}.pdf.
    Raises ConversionError or RuntimeError on failure.
    """
    dwg = Path(dwg_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if not dwg.exists():
        raise RuntimeError(f"File not found: {dwg}")
    ext = dwg.suffix.lower()
    if ext not in (".dwg", ".dxf"):
        raise RuntimeError(f"Unsupported file format: {ext}")

    logger.info("Converting %s via APS Model Derivative…", dwg.name)

    client_id, client_secret = _get_credentials()
    token  = _get_token(client_id, client_secret)
    bucket = _bucket_key(client_id)

    ts         = int(time.time())
    object_key = f"input_{ts}{ext}"

    _ensure_bucket(token, bucket)
    object_id = _upload_to_oss(token, bucket, object_key, dwg)
    urn       = _encode_urn(object_id)

    _start_translation(token, urn)
    manifest = _poll_manifest(token, urn)

    # Refresh token in case it expired during the poll
    token = _get_token(client_id, client_secret)

    pdf_derivatives = _find_pdf_derivatives(manifest)
    logger.info("Found %d PDF layout(s) in manifest", len(pdf_derivatives))

    results: list[tuple[str, Path]] = []
    for index, (name, derivative_urn) in enumerate(pdf_derivatives):
        pdf_path = out / f"{index}.pdf"
        _download_derivative(token, urn, derivative_urn, pdf_path)
        results.append((name, pdf_path))

    logger.info("Conversion complete: %d layout(s)", len(results))
    return results
