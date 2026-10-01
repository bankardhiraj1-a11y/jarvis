"""Bounded, read-only lookup of official Dhan contract lot sizes."""

from __future__ import annotations

import csv
import io
import math
from urllib.request import Request, urlopen


DHAN_SECURITY_MASTER_URL = "https://images.dhan.co/api-data/api-scrip-master.csv"
MAX_SECURITY_MASTER_BYTES = 32 * 1024 * 1024


def parse_security_master_lot_sizes(csv_text: str) -> dict[str, int]:
    """Return valid contract-id/lot-size pairs from common official master headers."""
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        return {}
    columns = {str(name).strip().upper(): name for name in reader.fieldnames}
    security_column = next(
        (
            columns[name]
            for name in (
                "SEM_SMST_SECURITY_ID",
                "SECURITY_ID",
                "SECURITYID",
            )
            if name in columns
        ),
        None,
    )
    lot_column = next(
        (
            columns[name]
            for name in ("SEM_LOT_UNITS", "LOT_SIZE", "LOTSIZE")
            if name in columns
        ),
        None,
    )
    if security_column is None or lot_column is None:
        return {}

    result: dict[str, int] = {}
    for row in reader:
        try:
            security_id = str(int(str(row.get(security_column, "")).strip()))
            numeric_lot = float(row.get(lot_column, ""))
            lot_size = int(numeric_lot)
        except (TypeError, ValueError, OverflowError):
            continue
        if (
            int(security_id) > 0
            and math.isfinite(numeric_lot)
            and numeric_lot == lot_size
            and lot_size > 0
        ):
            result[security_id] = lot_size
    return result


def fetch_official_dhan_lot_sizes() -> dict[str, int]:
    """Fetch once at startup with strict time and response-size bounds."""
    request = Request(
        DHAN_SECURITY_MASTER_URL,
        headers={"Accept": "text/csv", "User-Agent": "Jarvis-paper-market-data/1.0"},
        method="GET",
    )
    with urlopen(request, timeout=10) as response:
        if getattr(response, "status", 200) != 200:
            return {}
        content_length = response.headers.get("Content-Length")
        if content_length:
            try:
                if int(content_length) > MAX_SECURITY_MASTER_BYTES:
                    return {}
            except (TypeError, ValueError):
                return {}
        payload = response.read(MAX_SECURITY_MASTER_BYTES + 1)
    if len(payload) > MAX_SECURITY_MASTER_BYTES:
        return {}
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {}
    return parse_security_master_lot_sizes(text)