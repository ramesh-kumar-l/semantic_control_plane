"""Contradiction detection over normalized claims (`14-trust-model.md`).

Deterministic and explainable: claims are grouped by (subject, predicate) — both
compared case-insensitively — and every conflicting pair within a group is
reported. Two claims conflict when they assert different objects, or when one
asserts and the other negates the same object.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from .enums import ContradictionKind
from .models import Claim, Contradiction


def _key(claim: Claim) -> tuple[str, str]:
    return (claim.subject.strip().lower(), claim.predicate.strip().lower())


def _conflict(a: Claim, b: Claim) -> ContradictionKind | None:
    same_object = a.object.strip().lower() == b.object.strip().lower()
    if a.negated != b.negated and same_object:
        return ContradictionKind.POLARITY_CONFLICT
    if a.negated == b.negated and not a.negated and not same_object:
        return ContradictionKind.VALUE_MISMATCH
    return None


class ContradictionDetector:
    """Finds conflicting assertions among a set of claims."""

    def detect(self, claims: Sequence[Claim]) -> list[Contradiction]:
        """Return one `Contradiction` per conflicting pair (deterministic order)."""
        groups: dict[tuple[str, str], list[Claim]] = defaultdict(list)
        for claim in claims:
            groups[_key(claim)].append(claim)

        found: list[Contradiction] = []
        for members in groups.values():
            ordered = sorted(members, key=lambda c: c.id)
            for i in range(len(ordered)):
                for j in range(i + 1, len(ordered)):
                    a, b = ordered[i], ordered[j]
                    kind = _conflict(a, b)
                    if kind is None:
                        continue
                    found.append(
                        Contradiction(
                            kind=kind,
                            subject=a.subject,
                            predicate=a.predicate,
                            claim_ids=(a.id, b.id),
                            detail=(
                                f"'{a.object}'"
                                f"{' (negated)' if a.negated else ''} vs '{b.object}'"
                                f"{' (negated)' if b.negated else ''}"
                            ),
                        )
                    )
        found.sort(key=lambda c: c.claim_ids)
        return found
