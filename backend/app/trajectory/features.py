def center_from_bbox(bbox: list[float]) -> tuple[float, float]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain four coordinates")
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
