"""Title and location filtering.

Matching is case-insensitive on whole words, so "intern" does not match
"International" and "analyst" does match "Business Analyst - Strategy".
Multi-word phrases ("data analyst") must appear in that order.
"""

from __future__ import annotations

import re
from functools import lru_cache

from .models import Job


@lru_cache(maxsize=512)
def _pattern(term: str) -> re.Pattern:
    words = [re.escape(w) for w in term.lower().split()]
    return re.compile(r"\b" + r"\s+".join(words) + r"\b")


def _has_any(text: str, terms: list[str]) -> bool:
    text = text.lower()
    return any(_pattern(t).search(text) for t in terms)


def _title_ok(title: str, include: list[str], exclude: list[str]) -> bool:
    if include and not _has_any(title, include):
        return False
    if exclude and _has_any(title, exclude):
        return False
    return True


def matches(job: Job, rules: dict) -> bool:
    include = rules.get("include_keywords") or []
    exclude = rules.get("exclude_keywords") or []
    locations = rules.get("locations") or []

    # "Analyst/Senior Analyst (TMT)" is open at two levels: keep it if either
    # slash-separated level passes on its own.
    parts = [job.title] + [p for p in job.title.split("/") if p.strip()]
    if not any(_title_ok(p, include, exclude) for p in parts):
        return False
    # Jobs with no location text are kept rather than silently dropped.
    if locations and job.location and not _has_any(job.location, locations):
        return False
    return True


def rules_for(company_cfg: dict, global_rules: dict) -> dict:
    """Company-level filter keys override the global ones, key by key."""
    merged = dict(global_rules or {})
    merged.update(company_cfg.get("filters") or {})
    return merged
