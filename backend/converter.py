"""
DWG/DXF → PDF via Autodesk Platform Services (APS) Model Derivative API.

Pipeline:
  1. Authenticate with APS (2-legged OAuth)
  2. Create/ensure an OSS bucket
  3. Upload DWG/DXF to OSS via signed S3 URL
  4. Submit a Model Derivative translation job (DWG → PDF)
  5. Poll the manifest until translation succeeds or fails
  6. Download the resulting PDF

Requires APS_CLIENT_ID and APS_CLIENT_SECRET env vars.
"""

import base64
import logging
import os
import time
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

APS_BASE      = "https://developer.api.autodesk.com"
BUCKET_KEY    = "archyai-drawings"
POLL_INTERVAL = 10   # seconds between manifest polls
POLL_TIMEOUT  = 600  # 10 minutes


class ConversionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _get_credentials() -> tuple[str, str]:
    client_id     = os.environ.get("APS_CLIENT_ID", "").strip()
    client_secret = os.environ.get("APS_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise ConversionError(
            "APS_CLIENT_ID and APS_CLIENT_SECRET must be set in .env"
        )
    return client_id, client_secret


def _get_token(client_id: str, client_secret: str) -> str:
    """Obtain a 2-legged OAuth access token from APS."""
    resp = requests.post(
        f"{APS_BASE}/authentication/v2/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     client_id,
            "client_secret": client_secret,
            "scope":         "data:read data:write data:create bucket:create bucket:read bucket:update code:all",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise ConversionError(f"APS auth failed ({resp.status_code}): {resp.text}")
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# OSS — Object Storage Service
# ---------------------------------------------------------------------------

def _ensure_bucket(token: str) -> None:
    """Create the OSS bucket if it does not already exist."""
    resp = requests.post(
        f"{APS_BASE}/oss/v2/buckets",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"bucketKey": BUCKET_KEY, "policyKey": "temporary"},
        timeout=30,
    )
    # 409 = bucket already exists — fine
    if resp.status_code not in (200, 201, 409):
        raise ConversionError(f"OSS bucket creation failed ({resp.status_code}): {resp.text}")


def _upload_to_oss(token: str, object_key: str, file_path: Path) -> str:
    """
    Upload a file to OSS via signed S3 URL.
    Returns the full OSS object URN (not yet base64-encoded).
    """
    init_resp = requests.get(
        f"{APS_BASE}/oss/v2/buckets/{BUCKET_KEY}/objects/{object_key}/signeds3upload",
        headers={"Authorization": f"Bearer {token}"},
        params={"minutesExpiration": 60},
        timeout=30,
    )
    if init_resp.status_code != 200:
        raise ConversionError(f"OSS signed upload URL failed ({init_resp.status_code}): {init_resp.text}")

    upload_data = init_resp.json()
    upload_key  = upload_data["uploadKey"]
    s3_url      = upload_data["urls"][0]

    logger.info("Uploading %s to APS OSS…", file_path.name)
    with open(file_path, "rb") as fh:
        put_resp = requests.put(
            s3_url,
            data=fh,
            headers={"Content-Type": "application/octet-stream"},
            timeout=300,
        )
    if put_resp.status_code not in (200, 204):
        raise ConversionError(f"S3 upload failed ({put_resp.status_code}): {put_resp.text}")

    fin_resp = requests.post(
        f"{APS_BASE}/oss/v2/buckets/{BUCKET_KEY}/objects/{object_key}/signeds3upload",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"uploadKey": upload_key},
        timeout=30,
    )
    if fin_resp.status_code not in (200, 201):
        raise ConversionError(f"OSS upload finalization failed ({fin_resp.status_code}): {fin_resp.text}")

    fin_data = fin_resp.json()
    logger.info("Finalize response: %s", fin_data)
    urn = fin_data["objectId"]
    logger.info("Upload complete. URN: %s", urn)
    return urn


def _encode_urn(urn: str) -> str:
    return base64.urlsafe_b64encode(urn.encode()).decode().rstrip("=")


# ---------------------------------------------------------------------------
# Model Derivative — translation job
# ---------------------------------------------------------------------------

def _submit_translation(token: str, encoded_urn: str) -> None:
    payload = {
        "input": {
            "urn": encoded_urn,
            "compressedUrn": False,
        },
        "output": {
            "formats": [
                {
                    "type": "pdf",
                }
            ],
        },
    }
    logger.info("Submitting translation job. encoded_urn=%s payload=%s", encoded_urn, payload)
    resp = requests.post(
        f"{APS_BASE}/modelderivative/v2/designdata/job",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        json=payload,
        timeout=30,
    )
    logger.info("Translation job response (%s): %s", resp.status_code, resp.text)
    if resp.status_code not in (200, 201):
        raise ConversionError(f"Translation job submission failed ({resp.status_code}): {resp.text}")
    logger.info("Translation job submitted.")


def _poll_manifest(token: str, encoded_urn: str) -> dict:
    """Poll until translation succeeds or fails. Returns the manifest."""
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        resp = requests.get(
            f"{APS_BASE}/modelderivative/v2/designdata/{encoded_urn}/manifest",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise ConversionError(f"Manifest poll failed ({resp.status_code}): {resp.text}")

        manifest = resp.json()
        status   = manifest.get("status", "")
        progress = manifest.get("progress", "")
        logger.info("Translation status: %s  %s", status, progress)

        if status == "success":
            return manifest
        if status == "failed":
            messages = [
                msg.get("message", "")
                for d in manifest.get("derivatives", [])
                for msg in d.get("messages", [])
            ]
            raise ConversionError(f"Translation failed: {'; '.join(messages) or 'unknown error'}")

        time.sleep(POLL_INTERVAL)

    raise ConversionError(f"Translation timed out after {POLL_TIMEOUT}s")


def _find_pdf_derivative(manifest: dict) -> dict | None:
    for derivative in manifest.get("derivatives", []):
        if derivative.get("outputType") == "pdf":
            for child in derivative.get("children", []):
                if child.get("mime") == "application/pdf":
                    return child
    return None


def _download_derivative(token: str, encoded_urn: str, derivative_urn: str, output_path: Path) -> None:
    encoded_deriv = requests.utils.quote(derivative_urn, safe="")
    resp = requests.get(
        f"{APS_BASE}/modelderivative/v2/designdata/{encoded_urn}/manifest/{encoded_deriv}/signedcookies",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code == 200:
        policy  = resp.json()
        dl_url  = policy.get("url", "")
        dl_resp = requests.get(dl_url, cookies=resp.cookies, timeout=300)
    else:
        dl_resp = requests.get(
            f"{APS_BASE}/modelderivative/v2/designdata/{encoded_urn}/manifest/{encoded_deriv}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=300,
        )

    if dl_resp.status_code != 200:
        raise ConversionError(f"Derivative download failed ({dl_resp.status_code}): {dl_resp.text[:200]}")

    output_path.write_bytes(dl_resp.content)
    logger.info("Downloaded PDF: %s (%d KB)", output_path.name, len(dl_resp.content) // 1024)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert_dwg_to_pdf(dwg_path: str, output_dir: str) -> Path:
    """
    Convert a DWG/DXF file to a PDF via APS Model Derivative API.

    Returns the Path to the output PDF.
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

    logger.info("Converting %s via APS…", dwg.name)

    client_id, client_secret = _get_credentials()
    token = _get_token(client_id, client_secret)

    object_key = f"{dwg.stem}_{int(time.time())}{ext}"

    _ensure_bucket(token)
    urn         = _upload_to_oss(token, object_key, dwg)
    encoded_urn = _encode_urn(urn)

    _submit_translation(token, encoded_urn)
    manifest = _poll_manifest(token, encoded_urn)

    # Refresh token — poll can take several minutes
    token = _get_token(client_id, client_secret)

    pdf_child = _find_pdf_derivative(manifest)
    if pdf_child is None:
        raise ConversionError("No PDF derivative found in translation manifest.")

    pdf_path = out / "output.pdf"
    _download_derivative(token, encoded_urn, pdf_child["urn"], pdf_path)

    logger.info("Conversion complete: %s", pdf_path)
    return pdf_path
