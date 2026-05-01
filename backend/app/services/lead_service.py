"""
Lead service — CSV import, deduplication, DND filtering.
"""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.lead import Lead, LeadStatus
from app.schemas.lead import CSVUploadResponse
from app.services.compliance_service import is_in_scrub_list

# Column name aliases for normalisation
_COLUMN_MAP = {
    "name": ["name", "full_name", "fullname", "contact_name"],
    "phone": ["phone", "phone_number", "mobile", "cell", "contact"],
    "age": ["age"],
    "city": ["city", "location", "town"],
    "language": ["language", "lang", "preferred_language"],
    "do_not_call": ["do_not_call", "dnc", "dnd", "opt_out"],
}

LANGUAGE_DEFAULTS = {
    "en": ["english", "eng", "en"],
    "hi": ["hindi", "hin", "hi"],
    "ta": ["tamil", "ta"],
    "te": ["telugu", "te"],
    "bn": ["bengali", "bn"],
    "mr": ["marathi", "mr"],
    "gu": ["gujarati", "gu"],
    "kn": ["kannada", "kn"],
    "ml": ["malayalam", "ml"],
    "pa": ["punjabi", "pa"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename dataframe columns to canonical names."""
    rename_map: dict[str, str] = {}
    lower_cols = {c.lower().strip(): c for c in df.columns}
    for canonical, aliases in _COLUMN_MAP.items():
        for alias in aliases:
            if alias in lower_cols:
                rename_map[lower_cols[alias]] = canonical
                break
    return df.rename(columns=rename_map)


def _clean_phone(phone: str) -> str:
    """Strip formatting from phone numbers."""
    return re.sub(r"[^\d+]", "", str(phone).strip())


def _phone_hash(phone: str) -> str:
    return hashlib.sha256(phone.encode()).hexdigest()


def _detect_language(raw: str) -> str:
    raw = str(raw).lower().strip()
    for code, aliases in LANGUAGE_DEFAULTS.items():
        if raw in aliases:
            return code
    return "en"


def _parse_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes", "y")


@dataclass
class ImportStats:
    total_rows: int = 0
    imported: int = 0
    duplicates: int = 0
    dnd_filtered: int = 0
    errors: int = 0
    leads: list[Lead] = field(default_factory=list)


async def import_leads_from_csv(
    file_bytes: bytes,
    campaign_id: int,
    db: AsyncSession,
    country: str = "generic",
) -> CSVUploadResponse:
    """
    Parse CSV bytes, deduplicate by phone, DND-filter, and bulk-insert leads.
    """
    stats = ImportStats()

    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as exc:
        raise ValueError(f"Could not parse CSV: {exc}") from exc

    df = _normalize_columns(df)

    if "name" not in df.columns or "phone" not in df.columns:
        raise ValueError("CSV must contain 'name' and 'phone' columns")

    stats.total_rows = len(df)

    # Fetch existing phone hashes for this campaign to detect duplicates
    existing_result = await db.execute(
        select(Lead.phone_hash).where(Lead.campaign_id == campaign_id)
    )
    existing_hashes: set[str] = {row[0] for row in existing_result.fetchall()}

    new_leads: list[Lead] = []

    for _, row in df.iterrows():
        try:
            raw_phone = str(row.get("phone", "")).strip()
            if not raw_phone:
                stats.errors += 1
                continue

            phone = _clean_phone(raw_phone)
            phone_hash = _phone_hash(phone)

            # Deduplication
            if phone_hash in existing_hashes:
                stats.duplicates += 1
                continue

            # DNC flag in CSV
            do_not_call = _parse_bool(row.get("do_not_call", False))

            # Scrub list check
            if not do_not_call and is_in_scrub_list(phone, country):
                do_not_call = True
                stats.dnd_filtered += 1

            lang_raw = row.get("language", "en")
            language = _detect_language(lang_raw) if pd.notna(lang_raw) else "en"

            age_raw = row.get("age")
            age = int(age_raw) if pd.notna(age_raw) else None

            city_raw = row.get("city")
            city = str(city_raw).strip() if pd.notna(city_raw) else None

            lead = Lead(
                campaign_id=campaign_id,
                name=str(row["name"]).strip(),
                phone=phone,
                phone_hash=phone_hash,
                age=age,
                city=city,
                language=language,
                do_not_call=do_not_call,
                status=LeadStatus.NEW,
            )
            new_leads.append(lead)
            existing_hashes.add(phone_hash)
            if not do_not_call:
                stats.imported += 1

        except Exception:
            stats.errors += 1

    if new_leads:
        db.add_all(new_leads)
        await db.flush()

    return CSVUploadResponse(
        total_rows=stats.total_rows,
        imported=stats.imported,
        duplicates=stats.duplicates,
        dnd_filtered=stats.dnd_filtered,
        errors=stats.errors,
    )
