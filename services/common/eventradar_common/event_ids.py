import zlib


def public_id_for(provider: str, external_id: str) -> int:
    """Stable numeric id for the frontend (deterministic per provider + external id)."""
    return zlib.crc32(f"{provider}:{external_id}".encode()) & 0x7FFFFFFF
