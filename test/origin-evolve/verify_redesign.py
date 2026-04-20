"""Brute-force verification of the redesigned origin-evolve spec.

Location: CastFlow/_eval/ (outside .castflow/, NOT shipped by bootstrap.py).

Verifies the deterministic claims in:
- core/skills/origin-evolve/SKILL.md       (Step 1 diagnostics, attribution)
- core/skills/origin-evolve/SKILL_MEMORY.md (Rule 2, Rule 3, thresholds)

Run: python verify_redesign.py
"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Set, Tuple

# ----------------------------------------------------------------------------
# Spec defaults (mirrored from SKILL_MEMORY.md Rule 3)
# ----------------------------------------------------------------------------
JACCARD_THRESHOLD = 0.5
CAPACITY_WORDS = 2000

# Generic anchors that Rule 2 says must be excluded from anchor-evidence
# attribution overrides.
GENERIC_ANCHORS: Set[str] = {
    "OnDestroy", "Subscribe", "Unsubscribe", "AddTimer", "RemoveTimer",
    "LoadAsset", "Release",
}


# ----------------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------------
@dataclass
class Rule:
    skill: str
    rule_id: str
    anchors: Set[str]
    word_count: int = 100
    retired: bool = False


@dataclass
class Proposal:
    modules: List[str]
    anchors: Set[str]
    word_count: int = 100


@dataclass
class SkillIndex:
    """Module-to-skill ownership; mirrors what AI infers from project layout."""
    module_to_skill: Dict[str, str] = field(default_factory=dict)
    parent_to_skill: Dict[str, str] = field(default_factory=dict)


# ----------------------------------------------------------------------------
# Spec functions (deterministic implementations of SKILL.md / SKILL_MEMORY.md)
# ----------------------------------------------------------------------------
def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def diagnostic_counts(rules: List[Rule]) -> Dict[str, int]:
    """SKILL.md Step 1: three diagnostic counts."""
    active = [r for r in rules if not r.retired]
    by_skill: Dict[str, List[Rule]] = {}
    for r in active:
        by_skill.setdefault(r.skill, []).append(r)

    within_drift = 0
    for _skill, items in by_skill.items():
        for a, b in combinations(items, 2):
            if jaccard(a.anchors, b.anchors) >= JACCARD_THRESHOLD:
                within_drift += 1

    cross_identical = 0
    cross_overlap = 0
    skills = list(by_skill.keys())
    for s1, s2 in combinations(skills, 2):
        for r1 in by_skill[s1]:
            for r2 in by_skill[s2]:
                if r1.anchors and r1.anchors == r2.anchors:
                    cross_identical += 1
                if jaccard(r1.anchors, r2.anchors) >= JACCARD_THRESHOLD:
                    cross_overlap += 1

    return {
        "within_skill_drift_pairs": within_drift,
        "cross_skill_identical_sets": cross_identical,
        "cross_skill_overlap_pairs": cross_overlap,
    }


def common_parent(modules: List[str]) -> Optional[str]:
    """Two or more modules sharing a common parent path component."""
    if len(modules) < 2:
        return None
    parents = [m.rsplit("/", 1)[0] if "/" in m else None for m in modules]
    if all(p == parents[0] and p is not None for p in parents):
        return parents[0]
    return None


def attribute(
    proposal: Proposal,
    index: SkillIndex,
    skill_anchor_owners: Dict[str, Set[str]],
) -> Dict[str, object]:
    """SKILL_MEMORY.md Rule 2: attribution decision tree.

    Returns dict with `target` and optional `alt_candidate` (when anchor
    evidence disagrees with the module-list result).
    """
    # Step 1: module-list resolution
    if len(proposal.modules) == 1:
        m = proposal.modules[0]
        target_by_module = index.module_to_skill.get(m, ".claude/rules/")
    else:
        parent = common_parent(proposal.modules)
        if parent and parent in index.parent_to_skill:
            target_by_module = index.parent_to_skill[parent]
        else:
            target_by_module = ".claude/rules/"

    # Step 2: anchor-evidence cross-check (excluding generic anchors)
    significant = proposal.anchors - GENERIC_ANCHORS
    target_by_anchor: Optional[str] = None
    if significant:
        # Find skill that owns the most significant anchors
        best_skill: Optional[str] = None
        best_overlap = 0
        for skill, owned in skill_anchor_owners.items():
            ovl = len(significant & owned)
            if ovl > best_overlap:
                best_overlap = ovl
                best_skill = skill
        # Only override if anchor ownership is unambiguous (>= 2 significant anchors owned)
        if best_skill and best_overlap >= 2:
            target_by_anchor = best_skill

    if target_by_anchor and target_by_anchor != target_by_module:
        return {
            "target": target_by_module,
            "alt_candidate": target_by_anchor,
            "needs_user_choice": True,
        }
    return {"target": target_by_module, "alt_candidate": None, "needs_user_choice": False}


def choose_op(
    proposal: Proposal,
    existing_rules_in_target: List[Rule],
    file_word_count: int,
    grep_zero_anchors: Set[str],
) -> Dict[str, object]:
    """SKILL_MEMORY.md Rule 3: Append / Merge / Retire."""
    # Retire candidates: any active rule whose anchors are 100% absent
    retire_candidates = [
        r for r in existing_rules_in_target
        if not r.retired and r.anchors and r.anchors.issubset(grep_zero_anchors)
    ]

    # Merge candidate: any active rule with Jaccard >= 0.5 against proposal
    merge_candidates = [
        r for r in existing_rules_in_target
        if not r.retired and jaccard(r.anchors, proposal.anchors) >= JACCARD_THRESHOLD
    ]

    if merge_candidates:
        # Pick the highest Jaccard
        merge_candidates.sort(
            key=lambda r: jaccard(r.anchors, proposal.anchors), reverse=True
        )
        return {"op": "Merge", "target_rule": merge_candidates[0].rule_id}

    # Append, but check capacity
    projected = file_word_count + proposal.word_count
    if projected > CAPACITY_WORDS:
        if retire_candidates:
            return {
                "op": "RetireThenAppend",
                "retire": retire_candidates[0].rule_id,
                "then": "Append",
            }
        return {"op": "Blocked", "reason": "capacity_full_no_retire_candidate"}

    return {"op": "Append"}


# ----------------------------------------------------------------------------
# Workload generators
# ----------------------------------------------------------------------------
SYMBOL_POOL = [f"Sym{i:03d}" for i in range(200)]
SHARED_SYMBOLS = list(GENERIC_ANCHORS) + ["NavMesh", "Awake", "Update"]


def gen_skill_set(rng: random.Random, n_skills: int) -> SkillIndex:
    idx = SkillIndex()
    for i in range(n_skills):
        skill = f"programmer-mod{i:02d}-skill"
        # 1-3 modules per skill
        for j in range(rng.randint(1, 3)):
            idx.module_to_skill[f"parent{i:02d}/mod{i:02d}_{j}"] = skill
        idx.parent_to_skill[f"parent{i:02d}"] = skill
    return idx


def gen_rule_corpus(
    rng: random.Random, index: SkillIndex, rules_per_skill: int
) -> Tuple[List[Rule], Dict[str, Set[str]]]:
    rules: List[Rule] = []
    anchor_owners: Dict[str, Set[str]] = {}
    skills = sorted(set(index.module_to_skill.values()))
    for skill in skills:
        owned: Set[str] = set()
        for k in range(rules_per_skill):
            # 3-7 anchors, mostly skill-specific + occasional shared
            n = rng.randint(3, 7)
            picks: Set[str] = set()
            # Skill-specific symbols (deterministic per-skill slice)
            base_idx = (hash(skill) % 50) * 3
            local_pool = SYMBOL_POOL[base_idx:base_idx + 20]
            picks.update(rng.sample(local_pool, k=min(n, len(local_pool))))
            # 30% chance to add a shared symbol (drives cross-skill overlap)
            if rng.random() < 0.3:
                picks.add(rng.choice(SHARED_SYMBOLS))
            owned.update(picks - GENERIC_ANCHORS)
            rules.append(Rule(skill=skill, rule_id=f"{skill}#R{k}", anchors=picks))
        anchor_owners[skill] = owned
    return rules, anchor_owners


# ----------------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------------
class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = 0
        self.failed = 0
        self.notes: List[str] = []

    def assert_(self, cond: bool, msg: str = "") -> None:
        if cond:
            self.passed += 1
        else:
            self.failed += 1
            if msg and len(self.notes) < 5:
                self.notes.append(msg)

    @property
    def ok(self) -> bool:
        return self.failed == 0


def test_diagnostic_determinism(rng: random.Random) -> TestResult:
    """Claim A: same input -> same diagnostic counts."""
    res = TestResult("A. Diagnostic counts are deterministic")
    for trial in range(50):
        idx = gen_skill_set(rng, n_skills=rng.randint(3, 8))
        rules, _ = gen_rule_corpus(rng, idx, rules_per_skill=rng.randint(3, 6))
        c1 = diagnostic_counts(rules)
        c2 = diagnostic_counts(list(reversed(rules)))
        res.assert_(c1 == c2, f"trial {trial}: order-dependent {c1} vs {c2}")
    return res


def test_diagnostic_monotonic(rng: random.Random) -> TestResult:
    """Claim A: increasing overlap -> non-decreasing pair counts."""
    res = TestResult("A. Diagnostic counts are monotonic in overlap")
    for trial in range(50):
        # Two skills, each starting with disjoint anchors
        a = Rule("S1", "S1#R0", {"X1", "X2", "X3", "X4"})
        b = Rule("S2", "S2#R0", {"Y1", "Y2", "Y3", "Y4"})
        prev = diagnostic_counts([a, b])["cross_skill_overlap_pairs"]
        # Gradually share more anchors
        for shared in range(1, 5):
            b2 = Rule("S2", "S2#R0", {f"X{i}" for i in range(1, shared + 1)} | {"Y4"})
            cur = diagnostic_counts([a, b2])["cross_skill_overlap_pairs"]
            res.assert_(cur >= prev,
                        f"trial {trial} shared={shared}: {cur} < {prev}")
            prev = cur
    return res


def test_diagnostic_catches_known_signals(rng: random.Random) -> TestResult:
    """Claim A: Step 1 diagnostics MUST detect each of the three signals
    when they are deliberately planted (proves the counter is not dead code).
    """
    res = TestResult("A. Diagnostics catch all three signal types when planted")

    # Signal 1: within-skill drift (two rules in same skill, Jaccard >= 0.5)
    rules1 = [
        Rule("S1", "S1#R0", {"X1", "X2", "X3"}),
        Rule("S1", "S1#R1", {"X1", "X2", "Y4"}),  # Jaccard 0.5
    ]
    c1 = diagnostic_counts(rules1)
    res.assert_(c1["within_skill_drift_pairs"] == 1,
                f"planted within-drift not caught: {c1}")

    # Signal 2: cross-skill identical anchor sets
    shared = {"NavMesh", "PathSolver", "AStar"}
    rules2 = [
        Rule("S1", "S1#R0", set(shared)),
        Rule("S2", "S2#R0", set(shared)),
        Rule("S3", "S3#R0", set(shared)),
    ]
    c2 = diagnostic_counts(rules2)
    # 3 skills with identical sets -> C(3,2) = 3 pairs
    res.assert_(c2["cross_skill_identical_sets"] == 3,
                f"planted identical sets not caught: {c2}")

    # Signal 3: cross-skill high overlap (different sets, Jaccard >= 0.5)
    rules3 = [
        Rule("S1", "S1#R0", {"A1", "A2", "A3"}),
        Rule("S2", "S2#R0", {"A1", "A2", "B4"}),  # Jaccard 0.5 with S1
    ]
    c3 = diagnostic_counts(rules3)
    res.assert_(c3["cross_skill_overlap_pairs"] == 1,
                f"planted cross-overlap not caught: {c3}")
    res.assert_(c3["cross_skill_identical_sets"] == 0,
                f"distinct sets falsely flagged identical: {c3}")

    # Retired rules MUST be excluded
    rules4 = [
        Rule("S1", "S1#R0", {"X1", "X2", "X3"}, retired=True),
        Rule("S1", "S1#R1", {"X1", "X2", "Y4"}),
    ]
    c4 = diagnostic_counts(rules4)
    res.assert_(c4["within_skill_drift_pairs"] == 0,
                f"retired rule still counted: {c4}")

    return res


def test_attribution_total(rng: random.Random) -> TestResult:
    """Claim B: every proposal yields exactly one target (decision tree is total)."""
    res = TestResult("B. Attribution decision tree is total")
    for _ in range(2000):
        idx = gen_skill_set(rng, n_skills=5)
        _, owners = gen_rule_corpus(rng, idx, rules_per_skill=3)
        modules_pool = list(idx.module_to_skill.keys()) + ["unknown/m1", "unknown/m2"]
        n_mod = rng.randint(1, 3)
        modules = rng.sample(modules_pool, k=min(n_mod, len(modules_pool)))
        anchors = set(rng.sample(SYMBOL_POOL, k=rng.randint(2, 6)))
        if rng.random() < 0.3:
            anchors.update(rng.sample(SHARED_SYMBOLS, k=2))
        prop = Proposal(modules=modules, anchors=anchors)
        out = attribute(prop, idx, owners)
        res.assert_(out["target"] is not None, "no target produced")
        res.assert_(isinstance(out["target"], str), "target not str")
    return res


def test_attribution_surfaces_disagreement(rng: random.Random) -> TestResult:
    """Claim B: when anchors point to a different skill than modules, both surface."""
    res = TestResult("B. Disagreement surfaces both candidates")
    # Construct adversarial: module says skill-A, but anchors are owned by skill-B
    for trial in range(200):
        idx = SkillIndex(
            module_to_skill={"city/build": "skill-A", "world/npc": "skill-B"},
            parent_to_skill={"city": "skill-A", "world": "skill-B"},
        )
        skill_b_anchors = {"NpcMove", "NavPath", "PathSolver", "AStar"}
        owners = {
            "skill-A": {"BuildingFunc", "UpgradeQueue"},
            "skill-B": skill_b_anchors,
        }
        prop = Proposal(
            modules=["city/build"],
            anchors=set(rng.sample(list(skill_b_anchors), 3)) | {"OnDestroy"},
        )
        out = attribute(prop, idx, owners)
        res.assert_(out["needs_user_choice"],
                    f"trial {trial}: failed to surface alt {out}")
        res.assert_(out["alt_candidate"] == "skill-B",
                    f"trial {trial}: wrong alt {out}")
    return res


def test_attribution_ignores_generic_anchors(rng: random.Random) -> TestResult:
    """Claim B: generic anchors must NOT trigger anchor-override."""
    res = TestResult("B. Generic-only anchors do not override module attribution")
    for _ in range(200):
        idx = SkillIndex(
            module_to_skill={"city/build": "skill-A"},
            parent_to_skill={"city": "skill-A"},
        )
        owners = {
            "skill-A": {"BuildingFunc"},
            "skill-B": set(GENERIC_ANCHORS),  # bogus: skill-B "owns" only generics
        }
        prop = Proposal(
            modules=["city/build"],
            anchors=set(rng.sample(list(GENERIC_ANCHORS), 3)),
        )
        out = attribute(prop, idx, owners)
        res.assert_(not out["needs_user_choice"],
                    f"generic anchors triggered override: {out}")
    return res


def test_choose_op_exclusive(rng: random.Random) -> TestResult:
    """Claim C: Append / Merge / Retire branches are exclusive and exhaustive."""
    res = TestResult("C. choose_op produces exactly one operation")
    valid_ops = {"Append", "Merge", "RetireThenAppend", "Blocked"}
    for _ in range(2000):
        anchors = set(rng.sample(SYMBOL_POOL, k=rng.randint(2, 6)))
        n_existing = rng.randint(0, 8)
        existing = []
        for k in range(n_existing):
            ea = set(rng.sample(SYMBOL_POOL, k=rng.randint(2, 6)))
            if rng.random() < 0.2:
                # Force overlap
                ea = anchors | set(rng.sample(SYMBOL_POOL, k=2))
            existing.append(Rule("S", f"S#R{k}", ea))
        file_words = rng.randint(0, 2500)
        proposal = Proposal(modules=["m"], anchors=anchors, word_count=rng.randint(50, 300))
        grep_zero = set(rng.sample(SYMBOL_POOL, k=rng.randint(0, 50)))
        out = choose_op(proposal, existing, file_words, grep_zero)
        res.assert_(out["op"] in valid_ops, f"unknown op: {out}")
    return res


def test_jaccard_boundary(rng: random.Random) -> TestResult:
    """Claim D: Jaccard 0.5 is the inclusive boundary for Merge."""
    res = TestResult("D. Jaccard 0.5 boundary is honored (inclusive)")
    # Exactly 0.5: |A∩B|=2, |A∪B|=4
    a_anchors = {"X1", "X2", "X3"}
    b_anchors = {"X1", "X2", "Y4"}
    rule = Rule("S", "S#R0", a_anchors)
    prop = Proposal(modules=["m"], anchors=b_anchors)
    out = choose_op(prop, [rule], file_word_count=100, grep_zero_anchors=set())
    res.assert_(out["op"] == "Merge",
                f"exact 0.5 should Merge, got {out} jaccard={jaccard(a_anchors, b_anchors)}")

    # Just below threshold: |A∩B|=1, |A∪B|=3 -> ~0.33
    b2 = {"X1", "Y2", "Y4"}
    out2 = choose_op(Proposal(["m"], b2), [rule], 100, set())
    res.assert_(out2["op"] == "Append",
                f"0.33 should Append, got {out2} jaccard={jaccard(a_anchors, b2)}")

    # Just above threshold: |A∩B|=3, |A∪B|=4 -> 0.75
    b3 = {"X1", "X2", "X3", "Y4"}
    out3 = choose_op(Proposal(["m"], b3), [rule], 100, set())
    res.assert_(out3["op"] == "Merge",
                f"0.75 should Merge, got {out3} jaccard={jaccard(a_anchors, b3)}")
    return res


def test_capacity_overflow_triggers_retire(rng: random.Random) -> TestResult:
    """Claim E: file over 2000 words -> Retire candidate first."""
    res = TestResult("E. Capacity overflow triggers Retire-then-Append")
    for _ in range(200):
        prop_anchors = set(rng.sample(SYMBOL_POOL, k=4))
        # No merge candidate
        existing_anchors = set(rng.sample(SYMBOL_POOL[100:], k=4))
        existing = [Rule("S", "S#R0", existing_anchors)]
        # All existing anchors are "grep zero"
        out = choose_op(
            Proposal(modules=["m"], anchors=prop_anchors, word_count=200),
            existing,
            file_word_count=1900,
            grep_zero_anchors=existing_anchors,
        )
        res.assert_(out["op"] == "RetireThenAppend",
                    f"expected RetireThenAppend, got {out}")
    return res


def test_capacity_overflow_blocked_when_no_retire(rng: random.Random) -> TestResult:
    """Claim E: capacity full + no retire candidate -> Blocked, surfaced to user."""
    res = TestResult("E. Capacity full + no retire -> Blocked")
    prop_anchors = {"A1", "A2", "A3"}
    existing_anchors = {"B1", "B2", "B3"}
    existing = [Rule("S", "S#R0", existing_anchors)]
    out = choose_op(
        Proposal(modules=["m"], anchors=prop_anchors, word_count=200),
        existing,
        file_word_count=1900,
        grep_zero_anchors=set(),  # nothing is missing -> no retire candidate
    )
    res.assert_(out["op"] == "Blocked",
                f"expected Blocked, got {out}")
    return res


# ----------------------------------------------------------------------------
# Risk-surface measurement (informational, not pass/fail)
# ----------------------------------------------------------------------------
def measure_risk_surface(rng: random.Random) -> Dict[str, float]:
    """Quantify how often the 'expected risk surfaces' fire under random load.

    These are NOT failures — they confirm Step 1 diagnostics will surface them
    so the AI can act in Step 2. Numbers should be > 0 (otherwise the
    diagnostic is dead code).
    """
    n_runs = 100
    accum = {"within": 0, "cross_id": 0, "cross_ovl": 0, "total_pairs": 0}
    for _ in range(n_runs):
        idx = gen_skill_set(rng, n_skills=rng.randint(4, 8))
        rules, _ = gen_rule_corpus(rng, idx, rules_per_skill=rng.randint(4, 8))
        c = diagnostic_counts(rules)
        accum["within"] += c["within_skill_drift_pairs"]
        accum["cross_id"] += c["cross_skill_identical_sets"]
        accum["cross_ovl"] += c["cross_skill_overlap_pairs"]
        # total active pairs for normalization
        active = [r for r in rules if not r.retired]
        accum["total_pairs"] += len(active) * (len(active) - 1) // 2
    return {
        "runs": n_runs,
        "avg_within_drift": accum["within"] / n_runs,
        "avg_cross_identical": accum["cross_id"] / n_runs,
        "avg_cross_overlap": accum["cross_ovl"] / n_runs,
        "avg_total_pairs": accum["total_pairs"] / n_runs,
    }


# ----------------------------------------------------------------------------
# Driver
# ----------------------------------------------------------------------------
def main() -> int:
    rng = random.Random(20260420)
    tests = [
        test_diagnostic_determinism,
        test_diagnostic_monotonic,
        test_diagnostic_catches_known_signals,
        test_attribution_total,
        test_attribution_surfaces_disagreement,
        test_attribution_ignores_generic_anchors,
        test_choose_op_exclusive,
        test_jaccard_boundary,
        test_capacity_overflow_triggers_retire,
        test_capacity_overflow_blocked_when_no_retire,
    ]

    print("=" * 72)
    print("origin-evolve redesign — brute-force verification")
    print("=" * 72)

    all_ok = True
    for fn in tests:
        result = fn(rng)
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.name}")
        print(f"        passed={result.passed}  failed={result.failed}")
        for note in result.notes:
            print(f"        - {note}")
        if not result.ok:
            all_ok = False

    print()
    print("-" * 72)
    print("Risk-surface measurement (Step 1 diagnostic counts under random load)")
    print("-" * 72)
    risk = measure_risk_surface(rng)
    for k, v in risk.items():
        print(f"  {k:30s} = {v}")
    print()
    print("Interpretation:")
    print("  - Non-zero `avg_within_drift` confirms drift overlap exists and")
    print("    Step 1 will surface it for AI to merge in Step 2.")
    print("  - Non-zero cross-skill counts confirm shared-symbol risk exists")
    print("    and Step 1 will flag it for the AI to route to .claude/rules/.")
    print("  - These are *signals for the AI*, not bugs in the spec.")

    print()
    print("=" * 72)
    print("OVERALL:", "ALL TESTS PASSED" if all_ok else "FAILURES PRESENT")
    print("=" * 72)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
