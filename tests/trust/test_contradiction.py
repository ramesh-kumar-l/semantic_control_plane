"""Unit tests for contradiction detection over claims."""

from __future__ import annotations

from scp.trust import Claim, ContradictionDetector, ContradictionKind


def _claim(cid: str, obj: str, *, negated: bool = False) -> Claim:
    return Claim(id=cid, subject="paris", predicate="capital_of", object=obj, negated=negated)


def test_value_mismatch_is_detected() -> None:
    detector = ContradictionDetector()
    found = detector.detect([_claim("c1", "france"), _claim("c2", "italy")])
    assert len(found) == 1
    assert found[0].kind == ContradictionKind.VALUE_MISMATCH
    assert found[0].claim_ids == ("c1", "c2")


def test_polarity_conflict_is_detected() -> None:
    detector = ContradictionDetector()
    found = detector.detect([_claim("c1", "france"), _claim("c2", "france", negated=True)])
    assert len(found) == 1
    assert found[0].kind == ContradictionKind.POLARITY_CONFLICT


def test_agreeing_claims_do_not_conflict() -> None:
    detector = ContradictionDetector()
    assert detector.detect([_claim("c1", "france"), _claim("c2", "france")]) == []


def test_grouping_is_case_insensitive_and_separates_predicates() -> None:
    detector = ContradictionDetector()
    claims = [
        Claim(id="a", subject="Paris", predicate="Capital_Of", object="france"),
        Claim(id="b", subject="paris", predicate="capital_of", object="italy"),
        # Different predicate -> not compared with the above.
        Claim(id="c", subject="paris", predicate="population", object="2M"),
    ]
    found = detector.detect(claims)
    assert len(found) == 1
    assert found[0].claim_ids == ("a", "b")
