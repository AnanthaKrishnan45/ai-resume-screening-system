
"""Lightweight, optional public GitHub enrichment."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def enrich_github(username: str | None, timeout: float = 3.0) -> dict:
    if not username:
        return {
            "status": "not_available",
            "summary": "No GitHub profile found in resume.",
            "score": 0,
        }

    username = username.strip()
    if not username or "/" in username or " " in username:
        return {
            "status": "failed",
            "summary": "Invalid GitHub username extracted from resume.",
            "score": 0,
        }

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Resume-Screening-Assignment",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = (
        "https://api.github.com/users/"
        + urllib.parse.quote(username, safe="")
        + "/repos?sort=updated&per_page=100"
    )

    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=timeout) as response:
            repos = json.loads(response.read().decode("utf-8"))

        if not isinstance(repos, list):
            raise ValueError("Unexpected GitHub API response")

        relevant_terms = (
            "python", "ai", "agent", "llm", "rag",
            "machine-learning", "deep-learning", "fastapi",
        )

        relevant = [
            repo for repo in repos
            if isinstance(repo, dict)
            and (
                any(
                    term in (
                        (repo.get("name") or "")
                        + " "
                        + (repo.get("description") or "")
                    ).lower()
                    for term in relevant_terms
                )
                or (repo.get("language") or "").lower() == "python"
            )
        ]

        now = datetime.now(timezone.utc)
        dates = [
            repo.get("pushed_at")
            for repo in repos
            if isinstance(repo, dict) and repo.get("pushed_at")
        ]

        recent_score = 0
        if dates:
            try:
                newest = datetime.fromisoformat(
                    max(dates).replace("Z", "+00:00")
                )
                days = max(0, (now - newest).days)
                recent_score = (
                    5 if days <= 30
                    else 4 if days <= 90
                    else 2 if days <= 365
                    else 1
                )
            except (ValueError, TypeError):
                recent_score = 0

        repo_score = min(5, len(relevant))
        score = min(10, recent_score + repo_score)

        return {
            "status": "success",
            "summary": (
                f"{len(repos)} public repositories; "
                f"{len(relevant)} Python/AI-relevant repositories; "
                f"recent activity signal {recent_score}/5."
            ),
            "score": score,
            "public_repositories": len(repos),
            "relevant_repositories": len(relevant),
        }

    except urllib.error.HTTPError as exc:
        if exc.code == 403 or exc.code == 429:
            reason = "GitHub API rate limit or access restriction"
        elif exc.code == 404:
            reason = "GitHub profile not found or unavailable"
        else:
            reason = f"GitHub API HTTP {exc.code}"

        return {
            "status": "failed",
            "summary": f"{reason}; screening continued without GitHub score.",
            "score": 0,
        }

    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "status": "failed",
            "summary": (
                f"GitHub network request failed ({type(exc).__name__}); "
                "screening continued without GitHub score."
            ),
            "score": 0,
        }

    except Exception as exc:
        return {
            "status": "failed",
            "summary": (
                f"GitHub enrichment failed ({type(exc).__name__}); "
                "screening continued without GitHub score."
            ),
            "score": 0,
        }
