
"""Deterministic eligibility, evidence extraction, and explainable scoring."""

from pathlib import Path
import hashlib
import json
import re

from .config import SCORE_WEIGHTS, PYTHON_TERMS, AI_TERMS
from .parser import (
    extract_text,
    normalize_text,
    extract_email,
    extract_github,
    extract_name,
)
from .github_enrichment import enrich_github


PROJECT_HEADINGS = {
    "projects", "project", "project experience", "selected projects",
    "academic projects", "personal projects", "technical projects",
    "relevant projects",
}

SECTION_HEADINGS = {
    "education", "experience", "work experience", "employment",
    "internships", "skills", "technical skills", "certifications",
    "achievements", "publications", "awards", "contact",
    "summary", "professional summary", "objective", "interests",
    "references", "languages", "activities", "positions of responsibility",
}

AI_PROJECT_TERMS = [
    "rag", "agent", "langchain", "langgraph", "llm",
    "retrieval", "embedding", "vector search", "vector database",
    "tool calling", "tool-calling", "evaluation", "orchestration",
    "transformer", "fine-tuning", "fine tuning", "chromadb",
    "llamaindex", "crewai", "semantic search", "generative ai",
    "machine learning", "deep learning", "neural network",
]

IMPLEMENTATION_VERBS = (
    "built", "developed", "implemented", "designed", "trained",
    "deployed", "created", "engineered", "integrated", "automated",
    "optimized", "architected", "configured", "evaluated",
)

BACKEND_TERMS = [
    "fastapi", "django", "flask", "api", "backend", "async",
    "postgresql", "postgres", "redis", "sql", "pytest",
    "pydantic", "microservice",
]

CLOUD_TERMS = [
    "docker", "gcp", "google cloud", "aws", "azure",
    "deployment", "deployed", "ci/cd", "react", "next.js",
    "kubernetes", "vercel",
]

ENGINEERING_TERMS = [
    "pytest", "unit test", "integration test", "caching",
    "queue", "observability", "concurrency", "retry",
    "logging", "monitoring", "architecture", "failure handling",
]


def _contains(text, terms):
    """Match complete terms instead of arbitrary substrings."""
    low = (text or "").lower()
    found = []

    for term in terms:
        pattern = (
            r"(?<![a-z0-9_+#.-])"
            + re.escape(term.lower())
            + r"(?![a-z0-9_+#.-])"
        )
        if re.search(pattern, low):
            found.append(term)

    return found


def _is_heading(line):
    """Identify common resume section headings."""
    cleaned = re.sub(r"^[\s•*\-–—|:]+", "", line.lower())
    cleaned = re.sub(r"[\s:|]+$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)

    if not cleaned or len(cleaned) > 55:
        return False

    if cleaned in PROJECT_HEADINGS or cleaned in SECTION_HEADINGS:
        return True

    # Recognize headings such as "Technical Skills:" and "Work Experience".
    return bool(
        re.fullmatch(
            r"(technical\s+)?(skills|experience|education|certifications)"
            r"(\s+and\s+\w+)?",
            cleaned,
        )
    )


def _section(text, headings):
    """Extract a section until the next recognizable section heading."""
    lines = (text or "").splitlines()
    start = None

    for i, line in enumerate(lines):
        cleaned = re.sub(r"^[\s•*\-–—|:]+", "", line.lower())
        cleaned = re.sub(r"[\s:|]+$", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)

        if cleaned in headings:
            start = i + 1
            break

        # Handle headings with an inline value, e.g. "Projects: Project A".
        for heading in headings:
            if cleaned.startswith(heading + ":"):
                start = i
                break

        if start is not None:
            break

    if start is None:
        return ""

    collected = []

    for line in lines[start:]:
        if _is_heading(line):
            break
        collected.append(line)

    return "\n".join(collected).strip()


def _project_evidence(project_text):
    """Return concise, distinct project lines with implementation evidence."""
    lines = []
    seen = set()

    for raw_line in (project_text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip(" \t•*-–—|")
        if len(line) < 25:
            continue

        low = line.lower()
        has_verb = any(
            re.search(r"\b" + re.escape(verb) + r"\b", low)
            for verb in IMPLEMENTATION_VERBS
        )

        # Retain concrete project descriptions, not headings or skill lists.
        if not has_verb:
            continue

        key = low
        if key not in seen:
            seen.add(key)
            lines.append(line)

    return lines[:4]


def score_resume(text: str, github_score: int = 0) -> dict:
    text = normalize_text(text or "")
    low = text.lower()

    python_hits = _contains(text, PYTHON_TERMS)
    ai_hits = _contains(text, AI_TERMS)

    project_text = _section(text, PROJECT_HEADINGS)
    project_low = project_text.lower()
    project_lines = _project_evidence(project_text)

    # Hard eligibility gate: both Python and AI evidence are required.
    # Project-depth scoring separately measures whether implementation
    # evidence appears in the project section.
    python_evidence = bool(python_hits)
    ai_evidence = bool(ai_hits)

    reasons = []
    if not python_evidence:
        reasons.append("No evidence of Python stack")
    if not ai_evidence:
        reasons.append("No AI/LLM/agentic project or implementation evidence")

    eligible = python_evidence and ai_evidence

    ai_project_hits = _contains(project_text, AI_PROJECT_TERMS)
    project_has_ai = bool(ai_project_hits)

    # AI score rewards AI signals found in the project section.
    # Skills-only evidence cannot earn the full project-depth score.
    ai_score = min(40, len(ai_project_hits) * 5)

    if project_has_ai and project_lines:
        ai_score = min(40, ai_score + 5)

    if not project_text:
        ai_score = min(ai_score, 12)
    elif not project_has_ai:
        ai_score = min(ai_score, 10)

    # Penalize likely thin LLM/API-wrapper descriptions only when the
    # project evidence suggests an API call without a broader workflow.
    wrapper_terms = ("openai api", "llm api", "gemini api", "chat completion")
    workflow_terms = (
        "retrieval", "rag", "embedding", "vector", "tool calling",
        "tool-calling", "workflow", "evaluation", "pipeline",
        "orchestration", "classification", "fine-tuning",
        "fine tuning", "preprocessing", "state management",
    )

    wrapper_only = (
        bool(project_text)
        and any(term in project_low for term in wrapper_terms)
        and not any(term in project_low for term in workflow_terms)
        and not any(
            re.search(r"\b" + re.escape(verb) + r"\b", project_low)
            for verb in ("evaluated", "optimized", "automated", "trained")
        )
    )

    if wrapper_only:
        ai_score = max(0, ai_score - 10)

    if ai_evidence and not project_has_ai:
        concerns_ai = "AI evidence found outside project section; project implementation needs verification"
    elif ai_score < 20:
        concerns_ai = "Limited explicit AI project-depth evidence"
    else:
        concerns_ai = None

    backend_hits = _contains(text, BACKEND_TERMS)
    python_score = min(
        30,
        (8 if python_evidence else 0)
        + min(16, len(backend_hits) * 3)
        + min(6, len(python_hits) * 2),
    )

    cloud_hits = _contains(text, CLOUD_TERMS)
    cloud_score = min(15, len(cloud_hits) * 2)

    engineering_hits = _contains(text, ENGINEERING_TERMS)
    engineering_score = min(5, len(engineering_hits))

    try:
        github_score = max(0, min(10, int(github_score)))
    except (TypeError, ValueError):
        github_score = 0

    breakdown = {
        "ai_project_depth": ai_score,
        "python_backend": python_score,
        "cloud_fullstack": cloud_score,
        "github": github_score,
        "engineering_depth": engineering_score,
    }

    # Preserve only skills that actually matched the resume.
    matched = sorted(
        set(python_hits + ai_hits + backend_hits + cloud_hits)
    )

    project_summary = (
        " ".join(project_lines)[:650]
        if project_lines
        else (
            "Project section found, but no concise implementation lines "
            "could be extracted automatically."
            if project_text
            else "No dedicated project section detected."
        )
    )

    strengths = []
    if ai_project_hits:
        strengths.append(
            "AI project signals: "
            + ", ".join(ai_project_hits[:5])
        )
    if backend_hits:
        strengths.append(
            "Backend signals: "
            + ", ".join(backend_hits[:5])
        )
    if project_lines:
        strengths.append("Implementation evidence found in project section")

    concerns = []
    if concerns_ai:
        concerns.append(concerns_ai)
    if python_score < 15:
        concerns.append("Limited Python/backend implementation evidence")
    if wrapper_only:
        concerns.append("Possible thin LLM/API-wrapper project; verify implementation")
    if not extract_github(text)[0]:
        concerns.append("No GitHub profile detected")

    total = sum(breakdown.values())

    return {
        "eligible": eligible,
        "rejection_reasons": reasons,
        "total_score": total if eligible else 0,
        "score_breakdown": breakdown if eligible else None,
        "matched_skills": matched[:30],
        "project_summary": project_summary,
        "strengths": strengths,
        "concerns": concerns,
        "evidence": {
            "python_terms": python_hits,
            "ai_terms": ai_hits,
            "project_signals": ai_project_hits,
            "project_implementation_lines": project_lines,
        },
    }


def screen_directory(input_dir: str, output_file: str) -> dict:
    root = Path(input_dir)
    candidates = []
    failures = []

    if not root.exists() or not root.is_dir():
        raise NotADirectoryError(f"Input directory does not exist: {root}")

    supported = {".pdf", ".docx", ".txt"}
    paths = sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in supported
    )

    seen_hashes = set()
    github_cache = {}

    for path in paths:
        try:
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()

            if digest in seen_hashes:
                failures.append({
                    "file": str(path),
                    "error": "Duplicate file content skipped",
                })
                continue
            seen_hashes.add(digest)

            text = extract_text(path)
            if not text or not text.strip():
                raise ValueError("No extractable text")

            name = extract_name(text, path.name)
            username, profile = extract_github(text)

            # Avoid repeated GitHub API calls for the same profile.
            if username:
                cache_key = username.lower()
                if cache_key not in github_cache:
                    github_cache[cache_key] = enrich_github(username)
                gh = github_cache[cache_key]
            else:
                gh = enrich_github(None)

            github_score = (
                gh.get("score", 0)
                if gh.get("status") == "success"
                else 0
            )

            scored = score_resume(text, github_score)

            candidates.append({
                "candidate_name": name,
                "source_file": str(path.relative_to(root)),
                "email": extract_email(text),
                "github_username": username,
                "github_url": profile,
                **scored,
                "github_enrichment": gh,
            })

        except Exception as exc:
            failures.append({
                "file": str(path),
                "error": f"{type(exc).__name__}: {str(exc)[:180]}",
            })

    eligible = sorted(
        (c for c in candidates if c["eligible"]),
        key=lambda c: (-c["total_score"], c["candidate_name"].lower()),
    )
    rejected = sorted(
        (c for c in candidates if not c["eligible"]),
        key=lambda c: c["candidate_name"].lower(),
    )

    for rank, candidate in enumerate(eligible, 1):
        candidate["rank"] = rank

    for candidate in rejected:
        candidate["rank"] = None

    result = {
        "metadata": {
            "system": "AI Resume Screening & Ranking System",
            "scoring_total": 100,
            "weights": SCORE_WEIGHTS,
            "input_directory": str(root),
        },
        "batch_summary": {
            "total_resumes_discovered": len(paths),
            "successfully_parsed": len(candidates),
            "eligible": len(eligible),
            "rejected": len(rejected),
            "failed_or_duplicate": len(failures),
        },
        "ranked_eligible_candidates": eligible,
        "rejected_candidates": rejected,
        "failures": failures,
    }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return result
