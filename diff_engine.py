"""
diff_engine.py
Core logic for DocDiff: extracts text from uploaded documents and produces
a structured, block-by-block comparison (additions / deletions / modifications).
"""
import difflib
import os
import re

from config import MODIFICATION_SIMILARITY_THRESHOLD


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_blocks(filepath, filename):
    """Return a list of non-empty text blocks (paragraphs) for a document."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".txt" or ext == ".md":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()
        return _split_paragraphs(raw)

    if ext == ".docx":
        import docx
        d = docx.Document(filepath)
        paras = [p.text for p in d.paragraphs]
        raw = "\n".join(paras)
        return _split_paragraphs(raw)

    if ext == ".pdf":
        import pdfplumber
        text_parts = []
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                text_parts.append(t)
        raw = "\n".join(text_parts)
        return _split_paragraphs(raw)

    raise ValueError(f"Unsupported file type: {ext}")


def _split_paragraphs(raw_text):
    """Split raw text into cleaned, non-empty paragraph blocks."""
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = re.split(r"\n\s*\n", raw_text)
    blocks = []
    for chunk in chunks:
        cleaned = " ".join(line.strip() for line in chunk.split("\n") if line.strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            blocks.append(cleaned)

    # Documents extracted from DOCX/PDF often lack blank-line breaks.
    if len(blocks) <= 1 and "\n" in raw_text:
        blocks = [
            re.sub(r"\s+", " ", line.strip())
            for line in raw_text.split("\n")
            if line.strip()
        ]
    return blocks


# ---------------------------------------------------------------------------
# Word-level diff (used to highlight the exact change inside a modified block)
# ---------------------------------------------------------------------------

def word_diff(old_text, new_text):
    """Return (old_html_tokens, new_html_tokens) marking word-level changes."""
    old_words = old_text.split(" ")
    new_words = new_text.split(" ")
    sm = difflib.SequenceMatcher(None, old_words, new_words)

    old_tokens, new_tokens = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        old_seg = " ".join(old_words[i1:i2])
        new_seg = " ".join(new_words[j1:j2])
        if tag == "equal":
            old_tokens.append(("equal", old_seg))
            new_tokens.append(("equal", new_seg))
        elif tag == "replace":
            old_tokens.append(("del", old_seg))
            new_tokens.append(("ins", new_seg))
        elif tag == "delete":
            old_tokens.append(("del", old_seg))
        elif tag == "insert":
            new_tokens.append(("ins", new_seg))
    return old_tokens, new_tokens


# ---------------------------------------------------------------------------
# Block-level diff between two documents
# ---------------------------------------------------------------------------

def compare_blocks(blocks_a, blocks_b):
    """
    Compare two lists of text blocks and return a structured diff:
    a list of dicts, each describing one change unit, in document order.
    """
    sm = difflib.SequenceMatcher(None, blocks_a, blocks_b, autojunk=False)
    ops = sm.get_opcodes()

    changes = []
    order = 0

    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            for k in range(i2 - i1):
                order += 1
                changes.append({
                    "order": order,
                    "type": "unchanged",
                    "old_index": i1 + k + 1,
                    "new_index": j1 + k + 1,
                    "old_text": blocks_a[i1 + k],
                    "new_text": blocks_b[j1 + k],
                })
        elif tag == "delete":
            for k in range(i1, i2):
                order += 1
                changes.append({
                    "order": order,
                    "type": "deletion",
                    "old_index": k + 1,
                    "new_index": None,
                    "old_text": blocks_a[k],
                    "new_text": None,
                })
        elif tag == "insert":
            for k in range(j1, j2):
                order += 1
                changes.append({
                    "order": order,
                    "type": "addition",
                    "old_index": None,
                    "new_index": k + 1,
                    "old_text": None,
                    "new_text": blocks_b[k],
                })
        elif tag == "replace":
            old_slice = blocks_a[i1:i2]
            new_slice = blocks_b[j1:j2]
            pairs, leftover_old, leftover_new = _pair_replace_blocks(old_slice, new_slice)

            # Emit paired modifications first (in old-index order), then leftovers
            for old_local, new_local in pairs:
                order += 1
                old_text = old_slice[old_local]
                new_text = new_slice[new_local]
                old_tokens, new_tokens = word_diff(old_text, new_text)
                changes.append({
                    "order": order,
                    "type": "modification",
                    "old_index": i1 + old_local + 1,
                    "new_index": j1 + new_local + 1,
                    "old_text": old_text,
                    "new_text": new_text,
                    "old_tokens": old_tokens,
                    "new_tokens": new_tokens,
                })
            for old_local in leftover_old:
                order += 1
                if leftover_new:
                    new_local = leftover_new.pop(0)
                    old_text = old_slice[old_local]
                    new_text = new_slice[new_local]
                    old_tokens, new_tokens = word_diff(old_text, new_text)
                    changes.append({
                        "order": order,
                        "type": "modification",
                        "change_kind": "replacement",
                        "old_index": i1 + old_local + 1,
                        "new_index": j1 + new_local + 1,
                        "old_text": old_text,
                        "new_text": new_text,
                        "old_tokens": old_tokens,
                        "new_tokens": new_tokens,
                    })
                else:
                    changes.append({
                        "order": order,
                        "type": "deletion",
                        "old_index": i1 + old_local + 1,
                        "new_index": None,
                        "old_text": old_slice[old_local],
                        "new_text": None,
                    })
            for new_local in leftover_new:
                order += 1
                changes.append({
                    "order": order,
                    "type": "addition",
                    "old_index": None,
                    "new_index": j1 + new_local + 1,
                    "old_text": None,
                    "new_text": new_slice[new_local],
                })

    return changes


def _pair_replace_blocks(old_slice, new_slice):
    """
    Within a 'replace' region, greedily pair up blocks that are similar
    enough to be considered a modification of one another (rather than an
    unrelated deletion + addition). Returns (pairs, leftover_old_idx, leftover_new_idx).
    """
    used_old, used_new = set(), set()
    candidates = []
    for oi, ot in enumerate(old_slice):
        for ni, nt in enumerate(new_slice):
            ratio = difflib.SequenceMatcher(None, ot, nt, autojunk=False).ratio()
            if ratio >= MODIFICATION_SIMILARITY_THRESHOLD:
                candidates.append((ratio, oi, ni))
    candidates.sort(reverse=True, key=lambda x: x[0])

    pairs = []
    for ratio, oi, ni in candidates:
        if oi in used_old or ni in used_new:
            continue
        used_old.add(oi)
        used_new.add(ni)
        pairs.append((oi, ni))

    pairs.sort(key=lambda p: p[0])
    leftover_old = [i for i in range(len(old_slice)) if i not in used_old]
    leftover_new = [i for i in range(len(new_slice)) if i not in used_new]
    return pairs, leftover_old, leftover_new


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def summarize(changes):
    summary = {"unchanged": 0, "addition": 0, "deletion": 0, "modification": 0}
    for c in changes:
        key = {"unchanged": "unchanged", "addition": "addition",
               "deletion": "deletion", "modification": "modification"}[c["type"]]
        summary[key] += 1
    summary["total"] = len(changes)
    total_meaningful = summary["addition"] + summary["deletion"] + summary["modification"]
    summary["total_changes"] = total_meaningful
    return summary
