"""Optional Gemini-powered plain-English change summaries."""
import json

from config import GEMINI_API_KEY, GEMINI_MODEL


def is_available():
    return bool(GEMINI_API_KEY)


def summarize_comparison(old_label, new_label, changes, summary):
    """
    Return a plain-English summary of meaningful changes between two versions.
    Falls back to a deterministic summary when Gemini is unavailable.
    """
    meaningful = [c for c in changes if c["type"] != "unchanged"]
    if not meaningful:
        return _fallback_summary(old_label, new_label, summary, meaningful)

    if not is_available():
        return _fallback_summary(old_label, new_label, summary, meaningful)

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)

        payload = {
            "from_version": old_label,
            "to_version": new_label,
            "counts": summary,
            "changes": [
                {
                    "type": c["type"],
                    "old_text": (c.get("old_text") or "")[:500],
                    "new_text": (c.get("new_text") or "")[:500],
                }
                for c in meaningful[:25]
            ],
        }

        prompt = (
            "You are a document review assistant. Given detected block-level changes "
            "between two document versions, write a concise review summary (3-5 sentences) "
            "for a human reviewer. Mention the overall nature of edits, highlight anything "
            "that looks like a factual, policy, numeric, or structural change versus cosmetic "
            "wording. Do not invent changes not present in the input.\n\n"
            f"Changes JSON:\n{json.dumps(payload, indent=2)}"
        )

        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        return text or _fallback_summary(old_label, new_label, summary, meaningful)
    except Exception:
        return _fallback_summary(old_label, new_label, summary, meaningful)


def _fallback_summary(old_label, new_label, summary, meaningful):
    total = summary.get("total_changes", len(meaningful))
    if total == 0:
        return f"No meaningful differences were detected between {old_label} and {new_label}."

    parts = [
        f"Comparing {old_label} to {new_label}: "
        f"{summary.get('addition', 0)} addition(s), "
        f"{summary.get('deletion', 0)} deletion(s), and "
        f"{summary.get('modification', 0)} modification(s) were detected across "
        f"{total} changed block(s)."
    ]

    mods = [c for c in meaningful if c["type"] == "modification"]
    if mods:
        sample = (mods[0].get("old_text") or "")[:80]
        if sample:
            parts.append(f"Example edit: “{sample}…” was revised in place.")

    parts.append(
        "Review additions and deletions carefully for factual or policy impact; "
        "modifications often reflect wording updates but may also change meaning."
    )
    return " ".join(parts)
