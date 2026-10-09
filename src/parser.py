
"""Resume text extraction and structured field parsing."""
from pathlib import Path
import re


def extract_text(path: Path) -> str:
    """Extract text from PDF, DOCX, or TXT files."""
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        try:
            import pymupdf

            with pymupdf.open(path) as doc:
                return "\n".join(page.get_text("text") for page in doc)
        except Exception:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix == ".docx":
        from docx import Document

        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")

    raise ValueError(f"Unsupported file type: {suffix}")


def normalize_text(text: str) -> str:
    """Normalize whitespace."""
    return re.sub(r"\s+", " ", text or "").strip()



def extract_email(text: str):
    """Return the first email address found."""
    match = re.search(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        text or "",
        re.IGNORECASE,
    )
    return match.group(0) if match else None



def extract_github(text: str):
    """Extract a candidate's GitHub profile when identifiable."""
    text = text or ""

    # Prefer explicit GitHub profile URLs.
    url_pattern = re.compile(
        r"(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9-]{1,39})"
        r"(?![A-Za-z0-9-])",
        re.IGNORECASE,
    )

    ignored = {
        "features", "topics", "orgs", "settings", "login",
        "signup", "explore", "marketplace", "about", "collections",
        "sponsors", "enterprise", "security", "site",
    }

    for match in url_pattern.finditer(text):
        username = match.group(1)
        if username.lower() not in ignored:
            return username, f"https://github.com/{username}"

    # Support labels such as "GitHub: atulkumar2025" and "Github : raj-github".
    label_pattern = re.compile(
        r"\bgithub\s*:\s*([A-Za-z0-9-]{1,39})\b",
        re.IGNORECASE,
    )

    for match in label_pattern.finditer(text):
        username = match.group(1)
        if username.lower() not in ignored:
            return username, f"https://github.com/{username}"

    # A bare GitHub label without a username is not enough to identify a profile.
    return None, None


def extract_project_section(text: str) -> str:
    """Extract text under Projects until the next major section."""
    lines = (text or "").splitlines()

    project_heading = re.compile(
        r"^\s*(?:(?:selected|technical|academic)\s+)?projects"
        r"(?:\s+and\s+projects)?\s*:?\s*$",
        re.IGNORECASE,
    )

    section_heading = re.compile(
        r"^\s*(?:education|experience|work experience|internship experience|"
        r"skills|technical skills|certifications|certificates|"
        r"achievements|publications|leadership|volunteering|"
        r"summary|professional summary|contact|interests)\s*:?\s*$",
        re.IGNORECASE,
    )

    start = None
    for i, line in enumerate(lines):
        if project_heading.match(line.strip()):
            start = i + 1
            break

    if start is None:
        return ""

    collected = []
    for line in lines[start:]:
        if section_heading.match(line.strip()):
            break
        if line.strip():
            collected.append(line.strip())

    return normalize_text(" ".join(collected))

def extract_name(text: str, filename: str) -> str:
    """Extract a plausible name from the first lines of a resume."""
    lines = (text or "").splitlines()

    skip_terms = (
        "bengaluru", "bangalore", "karnataka", "india",
        "engineer", "developer", "linkedin", "github",
        "email", "phone", "mobile", "address", "resume",
        "student", "portfolio", "curriculum vitae",
    )

    for i, raw_line in enumerate(lines[:12]):
        line = re.sub(r"\s+", " ", raw_line).strip(" •|")

        candidate = re.split(
            r"\s{2,}|\||\+91\b|\bBengaluru\b|\bBangalore\b",
            line,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        candidate = re.sub(r"[^A-Za-z .'-]", "", candidate).strip()
        words = candidate.split()

        if not (1 <= len(words) <= 4 and len(candidate) <= 45):
            continue

        if any(term in candidate.lower() for term in skip_terms):
            continue

        # Handle names split across two lines.
        if len(words) == 1 and i + 1 < min(len(lines), 12):
            next_line = re.sub(r"\s+", " ", lines[i + 1]).strip()
            next_part = re.split(
                r"\s{2,}|\||\+91\b|\bBengaluru\b|\bBangalore\b",
                next_line,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip()

            next_part = re.sub(r"[^A-Za-z .'-]", "", next_part).strip()

            if (
                1 <= len(next_part.split()) <= 3
                and not any(term in next_part.lower() for term in skip_terms)
            ):
                return f"{candidate} {next_part}".strip()

        if len(words) >= 2:
            return candidate

    return Path(filename).stem.replace("_", " ").title()
