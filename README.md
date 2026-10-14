# DocDiff

**A simpler way to understand what changed between two documents.**

DocDiff is a document comparison tool I built to make reviewing different versions of a document less tedious. Instead of going through files line by line, it compares their content, identifies changes, and presents them in a structured report.

It supports text files, Markdown, Word documents, and PDFs, with word-level highlighting to make smaller edits easier to spot.

The idea is simple: comparing documents shouldn't mean reading the same thing twice just to find a few changes.

## What it does

- Compares two or more document versions.
- Identifies added, deleted, modified, and unchanged content.
- Matches similar paragraphs to help distinguish edits from completely new content.
- Highlights individual word changes inside modified paragraphs.
- Generates a structured report with change summaries and statistics.
- Supports optional AI-generated summaries using Google Gemini.
- Works without an AI API key using a rule-based summary fallback.
- Allows comparison reports to be downloaded as plain text.

## Getting started

You'll need Python and pip installed on your system.

**1. Clone the repository**

```bash
git clone <YOUR_REPOSITORY_URL>
cd DocDiff
```

Replace the repository URL with your GitHub repository's clone URL.

**2. Create a virtual environment**

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**3. Install the dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the application**

```bash
python app.py
```

Open [http://127.0.0.1:3000/](http://127.0.0.1:3000/) in your browser.

From there, open the workspace, upload your documents, and run a comparison.

## How the comparison works

DocDiff follows a straightforward pipeline.

**1. Text extraction**

The uploaded documents are converted into text and separated into paragraph-level blocks.

**2. Block comparison**

The extracted blocks are compared using Python's `difflib.SequenceMatcher`. For multiple versions, comparisons happen between consecutive documents, such as `v1 → v2` and `v2 → v3`.

**3. Change classification**

Each block is classified as unchanged, added, deleted, or modified. Similarity-based matching helps identify paragraphs that have been edited rather than entirely replaced.

**4. Word-level comparison**

When a paragraph is modified, DocDiff compares its wording to highlight the specific changes. This makes it easier to review small edits without rereading the entire paragraph.

**5. Report generation**

The results are presented in a report with change details and summary statistics. A review summary can be generated using Google Gemini or the built-in rule-based fallback.

## Project structure

```text
DocDiff/
├── app.py
├── diff_engine.py
├── config.py
├── utils.py
├── gemini_summary.py
├── templates/
├── samples/
├── requirements.txt
└── README.md
```

A quick overview of the main files:

| File | What it does |
|---|---|
| `app.py` | Handles the Flask application, uploads, comparisons, reports, and downloads. |
| `diff_engine.py` | Contains the document extraction and comparison logic. |
| `config.py` | Stores application settings and configuration values. |
| `utils.py` | Provides helper functions and Jinja template filters. |
| `gemini_summary.py` | Handles optional AI-assisted summaries. |
| `templates/` | Contains the landing page, workspace, and report interface. |
| `samples/` | Contains example documents for testing. |

## Optional: AI summaries with Gemini

DocDiff does not require an AI API key to perform comparisons. If you want natural-language summaries, you can configure Google Gemini.

On macOS or Linux:

```bash
export GEMINI_API_KEY="your-api-key"
export GEMINI_MODEL="gemini-2.0-flash"

python app.py
```

On Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="your-api-key"
$env:GEMINI_MODEL="gemini-2.0-flash"

python app.py
```

Without the key, the application falls back to its rule-based summaries.

Keep your API key out of source control. If you use a `.env` file, make sure it is excluded from Git and that the application is configured to load it.

## Configuration

The application supports the following settings:

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `3000` | Port used by the application. |
| `GEMINI_API_KEY` | Not set | Enables Gemini summaries. |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Selects the Gemini model. |
| `DIFF_SIMILARITY_THRESHOLD` | `0.35` | Controls similarity-based block pairing. |
| `SECRET_KEY` | Development default | Used for Flask session signing. |

For public deployments, replace the development secret with a strong, private value.

## Routes

| Route | Purpose |
|---|---|
| `/` | Landing page |
| `/workspace` | Upload and compare documents |
| `/compare` | Accepts comparison form submissions |
| `/report/<id>` | Displays a comparison report |
| `/report/<id>/download` | Downloads a report as plain text |

## Try an example

The `samples/` directory contains example document versions you can use to test the application.

Start the server and upload:

- `samples/v1_draft.txt` — label it `Draft`.
- `samples/v2_final.txt` — label it `Final`.

Run the comparison and inspect the report. The supplied example is intended to demonstrate an addition, a modification with word-level differences, and updated summary statistics.

## A few things to know

DocDiff currently stores reports in memory, so they may be lost when the application restarts. This is suitable for local experimentation, but persistent storage would be needed for a more permanent workflow.

Comparison quality also depends on how well text can be extracted from the original documents. Complex PDF layouts, scanned pages, tables, and other non-standard content may need additional processing.

For a production deployment, I'd also consider persistent report storage, stronger upload validation, automated tests, and support for larger documents.

## Possible improvements

Some things I'd like to explore as the project develops:

- Side-by-side comparison for easier reading.
- Better handling of tables and complex PDF layouts.
- OCR support for scanned documents.
- A history of previous comparisons.
- Additional export formats.
- More detailed tests for block matching and word-level changes.

These are ideas for future development, not features currently claimed as implemented.

## License

A license has not yet been specified. Add a `LICENSE` file once the licensing terms are decided.

---

**DocDiff is about making document revisions easier to follow, one change at a time.**
