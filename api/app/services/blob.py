"""Download files from Vercel Blob storage or base64 data URLs."""

from __future__ import annotations

import base64
import io
import logging

import httpx
import pandas as pd

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
MAX_ROW_COUNT = 100_000


async def download_and_parse(blob_url: str) -> pd.DataFrame:
    """Download a CSV or Excel file from a Blob URL / data URL and return a DataFrame.

    Raises:
        ValueError: If the file is too large, empty, unreadable, or exceeds row limits.
    """
    raw_content: bytes = b""

    # Handle data: URLs (useful for local dev / direct payload)
    if str(blob_url).startswith("data:"):
        header, encoded = str(blob_url).split(",", 1)
        raw_content = base64.b64decode(encoded)
    else:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(str(blob_url))
            response.raise_for_status()
            raw_content = response.content

    content_length = len(raw_content)
    if content_length > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File is too large ({content_length / 1024 / 1024:.1f} MB). "
            f"Maximum allowed is {MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB."
        )

    if content_length == 0:
        raise ValueError("The uploaded file is empty.")

    url_str = str(blob_url).lower()

    try:
        if url_str.endswith(".xlsx") or "spreadsheetml" in url_str:
            df = pd.read_excel(io.BytesIO(raw_content), engine="openpyxl")
        elif url_str.endswith(".xls"):
            raise ValueError("Legacy .xls format is not supported. Please convert to .xlsx or .csv.")
        else:
            for encoding in ("utf-8", "latin-1", "cp1252"):
                try:
                    text = raw_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("Could not decode file encoding.")
            df = pd.read_csv(io.StringIO(text))
    except ValueError:
        raise
    except Exception as exc:
        logger.exception("Failed to parse uploaded file")
        raise ValueError(f"Could not parse file: {exc}") from exc

    if df.empty or len(df.columns) == 0:
        raise ValueError("The file contains no data or no recognizable columns.")

    if len(df) > MAX_ROW_COUNT:
        raise ValueError(f"Exceeds {MAX_ROW_COUNT:,} row limit.")

    return df
