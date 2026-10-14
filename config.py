"""Application configuration for DocDiff."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB
MAX_VERSIONS = 5
DEFAULT_PORT = 3000

# Block pairing: fraction of characters that must match to count as a modification.
MODIFICATION_SIMILARITY_THRESHOLD = float(
    os.environ.get("DIFF_SIMILARITY_THRESHOLD", "0.35")
)

# Optional Gemini AI summaries (set GEMINI_API_KEY in environment).
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

SECRET_KEY = os.environ.get("SECRET_KEY", "docdiff-dev-secret-key")
