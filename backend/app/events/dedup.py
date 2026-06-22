def event_dedup_key(event_type: str, track_id: int | None, zone_id: str | None) -> str:
    return f"{event_type}:{track_id or 'none'}:{zone_id or 'none'}"
