def event_dedup_key(event_type: str, track_id: int | None, zone_id: str | None) -> str:
    return f"{event_type}:{track_id or 'none'}:{zone_id or 'none'}"


def build_event_dedup_key(
    run_id: str,
    event_type: str,
    track_id: int | None = None,
    zone_id: str | None = None,
    rule_id: str | None = None,
) -> str:
    return ":".join(
        [
            _stable_part(run_id),
            _stable_part(event_type),
            _stable_part(track_id),
            _stable_part(zone_id),
            _stable_part(rule_id),
        ]
    )


def _stable_part(value: object | None) -> str:
    if value is None:
        return "none"
    return str(value)
