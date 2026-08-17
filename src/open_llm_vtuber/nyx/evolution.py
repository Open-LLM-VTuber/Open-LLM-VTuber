from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import List

from .audit import AuditLog


@dataclass
class PatchCandidate:
    title: str
    summary: str
    diff: str = ""
    approved: bool = False


class SelfReview:
    """Minimal evolution layer: propose changes before applying them."""

    def __init__(self, audit: AuditLog | None = None) -> None:
        self.candidates: List[PatchCandidate] = []
        self.audit = audit or AuditLog()

    def propose(self, title: str, summary: str, diff: str) -> PatchCandidate:
        candidate = PatchCandidate(title=title, summary=summary, diff=diff)
        self.candidates.append(candidate)
        return candidate

    def approve(self, title: str) -> PatchCandidate | None:
        for candidate in self.candidates:
            if candidate.title == title:
                candidate.approved = True
                diff_hash = hashlib.sha256(candidate.diff.encode("utf-8")).hexdigest()
                self.audit.record(
                    "approve_candidate",
                    {"title": candidate.title, "diff_sha256": diff_hash, "approved": True},
                    allowed=True,
                )
                return candidate
        return None

    def pending(self) -> List[PatchCandidate]:
        return [item for item in self.candidates if not item.approved]
