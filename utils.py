"""Shared helpers for DocDiff templates and report export."""
import re

from markupsafe import Markup, escape


def structure_text(text):
    """Split a block into readable bullet-style segments for display."""
    if not text:
        return []

    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []

    segments = re.split(r"(?<=[.;:])\s+(?=[A-Z0-9(])", cleaned)
    if len(segments) == 1:
        segments = re.split(r"\s+[•\-]\s+", cleaned)

    points = [segment.strip(" -–—•") for segment in segments if segment.strip(" -–—•")]
    return points or [cleaned]


def render_tokens(tokens):
    """Render word-level diff tokens as safe HTML with ins/del highlights."""
    if not tokens:
        return Markup("")

    parts = []
    for kind, text in tokens:
        if not text:
            continue
        safe = escape(text)
        if kind == "equal":
            parts.append(str(safe))
        elif kind == "del":
            parts.append(f'<del class="tok">{safe}</del>')
        elif kind == "ins":
            parts.append(f'<ins class="tok">{safe}</ins>')

    return Markup(" ".join(parts))
