"""Shared data model. Every source adapter returns a list of Job objects,
so filtering, diffing and alerting never care which portal a job came from."""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Job:
    company: str
    job_id: str
    title: str
    location: str
    url: str
    posted: str = ""  # ISO date or the portal's own text ("Posted 3 Days Ago")
    source: str = ""  # greenhouse | lever | ashby | workday

    @property
    def key(self) -> str:
        """Stable identity used to decide whether we've seen this job before."""
        return f"{self.company}::{self.job_id}"

    def to_dict(self) -> dict:
        return asdict(self)
