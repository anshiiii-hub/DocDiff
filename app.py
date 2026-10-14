"""DocDiff — Flask web application for document version comparison."""
import datetime
import os
import uuid

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    Response,
    url_for,
)
from werkzeug.utils import secure_filename

import gemini_summary
from config import (
    ALLOWED_EXTENSIONS,
    BASE_DIR,
    DEFAULT_PORT,
    MAX_CONTENT_LENGTH,
    MAX_VERSIONS,
    SECRET_KEY,
    UPLOAD_DIR,
)
from diff_engine import compare_blocks, extract_blocks, summarize
from utils import render_tokens, structure_text

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

app.jinja_env.filters["structure_text"] = structure_text
app.jinja_env.filters["render_tokens"] = render_tokens

REPORTS = {}


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/workspace")
def workspace():
    return render_template("index.html", max_versions=MAX_VERSIONS)


@app.route("/compare", methods=["POST"])
def compare():
    labels = request.form.getlist("labels")
    files = request.files.getlist("documents")
    files = [f for f in files if f and f.filename]

    if len(files) < 2:
        flash("Please upload at least two document versions to compare.")
        return redirect(url_for("workspace"))

    if len(files) > MAX_VERSIONS:
        flash(f"You can compare up to {MAX_VERSIONS} versions at once.")
        return redirect(url_for("workspace"))

    for f in files:
        if not allowed_file(f.filename):
            flash(
                f"Unsupported file type: {f.filename}. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
            return redirect(url_for("workspace"))

    report_id = uuid.uuid4().hex[:10]
    work_dir = os.path.join(UPLOAD_DIR, report_id)
    os.makedirs(work_dir, exist_ok=True)

    versions = []
    for idx, f in enumerate(files):
        safe_name = secure_filename(f.filename) or f"document{idx + 1}"
        saved_path = os.path.join(work_dir, f"{idx}_{safe_name}")
        f.save(saved_path)
        try:
            blocks = extract_blocks(saved_path, safe_name)
        except Exception as exc:
            flash(f"Could not read '{f.filename}': {exc}")
            return redirect(url_for("workspace"))

        label = (
            labels[idx].strip()
            if idx < len(labels) and labels[idx].strip()
            else f"Version {idx + 1}"
        )
        versions.append({
            "label": label,
            "filename": f.filename,
            "blocks": blocks,
            "block_count": len(blocks),
        })

    comparisons = []
    for i in range(len(versions) - 1):
        old_v, new_v = versions[i], versions[i + 1]
        changes = compare_blocks(old_v["blocks"], new_v["blocks"])
        summary = summarize(changes)
        ai_summary = gemini_summary.summarize_comparison(
            old_v["label"], new_v["label"], changes, summary
        )
        comparisons.append({
            "old_label": old_v["label"],
            "new_label": new_v["label"],
            "old_filename": old_v["filename"],
            "new_filename": new_v["filename"],
            "old_block_count": old_v["block_count"],
            "new_block_count": new_v["block_count"],
            "changes": changes,
            "summary": summary,
            "ai_summary": ai_summary,
        })

    overall = {
        "addition": sum(c["summary"]["addition"] for c in comparisons),
        "deletion": sum(c["summary"]["deletion"] for c in comparisons),
        "modification": sum(c["summary"]["modification"] for c in comparisons),
        "unchanged": sum(c["summary"]["unchanged"] for c in comparisons),
    }
    overall["total_changes"] = (
        overall["addition"] + overall["deletion"] + overall["modification"]
    )

    REPORTS[report_id] = {
        "id": report_id,
        "created": datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        "version_labels": [v["label"] for v in versions],
        "versions": [
            {
                "label": v["label"],
                "filename": v["filename"],
                "block_count": v["block_count"],
            }
            for v in versions
        ],
        "comparisons": comparisons,
        "overall": overall,
        "ai_enabled": gemini_summary.is_available(),
    }

    return redirect(url_for("report", report_id=report_id))


@app.route("/report/<report_id>")
def report(report_id):
    data = REPORTS.get(report_id)
    if not data:
        abort(404)
    return render_template("report.html", report=data)


@app.route("/report/<report_id>/download")
def download_report(report_id):
    data = REPORTS.get(report_id)
    if not data:
        abort(404)

    lines = [
        "DOCUMENT VERSION COMPARISON REPORT",
        f"Generated: {data['created']}",
        f"Versions compared: {' -> '.join(data['version_labels'])}",
        "=" * 70,
        "",
        "OVERALL SUMMARY",
        f"  Additions:     {data['overall']['addition']}",
        f"  Deletions:     {data['overall']['deletion']}",
        f"  Modifications: {data['overall']['modification']}",
        f"  Unchanged:     {data['overall']['unchanged']}",
        "",
    ]

    for comp in data["comparisons"]:
        lines.extend([
            "-" * 70,
            f"{comp['old_label']}  ->  {comp['new_label']}",
            "-" * 70,
        ])
        if comp.get("ai_summary"):
            lines.extend(["", "AI REVIEW SUMMARY", comp["ai_summary"], ""])

        for c in comp["changes"]:
            if c["type"] == "unchanged":
                continue
            if c["type"] == "addition":
                lines.append(
                    f"[ADDITION]   New block #{c['new_index']} | "
                    f"Introduced in: {comp['new_label']}"
                )
                for item in structure_text(c["new_text"]):
                    lines.append(f"  + {item}")
            elif c["type"] == "deletion":
                lines.append(
                    f"[DELETION]   Old block #{c['old_index']} | "
                    f"Removed from: {comp['old_label']}"
                )
                for item in structure_text(c["old_text"]):
                    lines.append(f"  - {item}")
            elif c["type"] == "modification":
                kind = (
                    "REPLACEMENT"
                    if c.get("change_kind") == "replacement"
                    else "MODIFICATION"
                )
                lines.append(
                    f"[{kind}]   Block #{c['old_index']} -> #{c['new_index']}"
                )
                lines.append(f"  Removed from: {comp['old_label']}")
                for item in structure_text(c["old_text"]):
                    lines.append(f"  - {item}")
                lines.append(f"  Added in: {comp['new_label']}")
                for item in structure_text(c["new_text"]):
                    lines.append(f"  + {item}")
            lines.append("")

    body = "\n".join(lines)
    return Response(
        body,
        mimetype="text/plain",
        headers={
            "Content-Disposition": f"attachment; filename=diff_report_{report_id}.txt"
        },
    )


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


@app.errorhandler(413)
def too_large(_error):
    flash("Upload too large. Total upload size must be under 20 MB.")
    return redirect(url_for("workspace"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    app.run(debug=True, host="0.0.0.0", port=port)
