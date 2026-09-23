"""Package-stance marks. Official TypeSafe Jev when configured, else the prior.

Clear structural decisions never call Jev. Unresolved cards call
``TypeSafeClient.system_one`` only when ``TYPESAFE_API_KEY`` is a key the
official client accepts. Otherwise the same function returns the prior and a
notice. Probabilities are copied from the official response or omitted.
"""

from __future__ import print_function

import os

NOTICE_NOT_CONFIGURED = (
    "notice: Jev is not configured. Marking uses the structural prior."
)
OFFICIAL_SOURCE = "official-jev"
_STANCES = (
    "feature",
    "shared_method",
    "independent_system",
    "framework_mechanism",
    "other",
)
_STANCE_CRITERIA = {
    "feature": "One product ability with its own entries",
    "shared_method": "Generic helper used by many abilities, no product entry",
    "independent_system": "A whole subsystem with its own surface, not a helper",
    "framework_mechanism": "Contracts, hosts, or schedulers that many surfaces sit on",
    "other": "The evidence is not enough to choose",
}
_SHARED_LEAVES = frozenset(("common", "shared", "util", "utils"))
_SCORE_CRITERIA = [
    "No shared contract or host",
    "Mixed",
    "Only a mechanism; surfaces live elsewhere",
]


class OfficialConfig(object):
    """Key stays on the object. ``public`` and ``repr`` never include it."""

    def __init__(self, api_key, model, base_url):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    def public(self):
        return {
            "configured": True,
            "model": self.model,
            "base_url": self.base_url,
        }

    def __repr__(self):
        return "OfficialConfig(configured=True, model={0}, base_url={1})".format(
            self.model, self.base_url,
        )


def _key_acceptable(raw):
    """Mirror the official client: strip ends, then reject empty or unsafe keys."""
    if raw is None:
        return None
    key = str(raw).strip()
    if not key:
        return None
    if any(ch.isspace() for ch in key):
        return None
    for ch in key:
        code = ord(ch)
        if code < 32 or code == 127 or code > 127:
            return None
    return key


def module_dir(project_root):
    """Installed Jev module in a project. Absent means the cold-start box was off."""
    if not project_root:
        return ""
    path = os.path.join(project_root, ".castflow-runtime", "jev")
    if os.path.isfile(os.path.join(path, "mark.py")):
        return path
    return ""


def key_path(project_root):
    """Gitignored env file shared by every optional key. Never config.json."""
    from manager.envfile import env_path
    return env_path(project_root)


def read_project_key(project_root):
    from manager.envfile import get
    return _key_acceptable(get(project_root, "TYPESAFE_API_KEY"))


def write_project_key(project_root, raw):
    """Write TYPESAFE_API_KEY into the shared env file. Other keys stay."""
    from manager.envfile import set_key
    key = _key_acceptable(raw)
    if not key or not project_root:
        return False
    return bool(set_key(project_root, "TYPESAFE_API_KEY", key))


def official_config(environ=None, project_root=None):
    """Return OfficialConfig or None. Does not print the key.

    A project uses Jev only after the module directory was synced. The key is
    `TYPESAFE_API_KEY` in the gitignored file `.castflow-runtime/secrets.env`.
    The process environment is the fallback when that file has no key, and
    the only source when `project_root` is omitted (tests and one-off calls).
    """
    env = os.environ if environ is None else environ
    if project_root is not None and not module_dir(project_root):
        return None
    key = None
    if project_root is not None:
        key = read_project_key(project_root)
    if not key:
        key = _key_acceptable(env.get("TYPESAFE_API_KEY"))
    if not key:
        return None
    model = (env.get("TYPESAFE_DEFAULT_MODEL") or "").strip() or "jev-latest"
    base = (env.get("TYPESAFE_BASE_URL") or "").strip() or "https://api.typesafe.ai"
    return OfficialConfig(key, model, base.rstrip("/"))


def _leaf_name(atom):
    paths = atom.get("paths") or []
    if not paths:
        return atom.get("id") or ""
    parts = [part for part in paths[0].split("/") if part and part != "."]
    if parts and "." in parts[-1]:
        parts = parts[:-1]
    if not parts:
        return atom.get("id") or ""
    return parts[-1]


def build_evidence_cards(atoms, edges):
    """One card per package. ``edges`` is accepted so callers share the graph."""
    del edges
    features = set()
    for atom in atoms:
        if atom.get("kind") == "feature-dir" and atom.get("role") == "feature":
            features.add(atom["id"])
    cards = []
    for atom in atoms:
        inbound = set(atom.get("inbound") or ())
        outbound = set(atom.get("outbound") or ())
        consumers = sorted(item for item in inbound if item in features)
        leaf = _leaf_name(atom)
        leaf_key = leaf.replace("_", "-").lower()
        sibling = ""
        if atom["id"] not in features and leaf_key in features:
            sibling = leaf_key
        decls = list(atom.get("decls") or [])[:8]
        cards.append({
            "id": atom["id"],
            "parent_id": "",
            "leaf_name": leaf,
            "sibling_feature_id": sibling,
            "fan_in": len(inbound),
            "fan_out": len(outbound),
            "entry_count": int(atom.get("entries") or 0),
            "consumer_ids": consumers,
            "decl_sample": decls,
            "child_ids": [],
            "role": atom.get("role") or "",
            "kind": atom.get("kind") or "",
        })
    cards.sort(key=lambda card: card["id"])
    return cards


def _base_mark(card, action, role, source, evidence):
    return {
        "id": card["id"],
        "action": action,
        "target_id": card["sibling_feature_id"] or card["id"],
        "role": role,
        "source": source,
        "evidence": evidence,
    }


def prior_mark(card):
    """A clear structural decision, or None when Jev may be asked.

    The returned mark has no probability, noul, score, or confidence.
    """
    leaf = (card.get("leaf_name") or "").lower()
    consumers = card.get("consumer_ids") or []
    if leaf in _SHARED_LEAVES:
        return _base_mark(
            card, "keep", "tool", "prior",
            "shared leaf {0}; not attached to a feature".format(leaf),
        )
    if card.get("sibling_feature_id") and len(consumers) <= 1:
        mark = _base_mark(
            card, "attach", "feature", "prior",
            "leaf matches {0}; consumers={1}".format(
                card["sibling_feature_id"], len(consumers),
            ),
        )
        mark["target_id"] = card["sibling_feature_id"]
        return mark
    if card.get("role") == "adapter":
        return _base_mark(
            card, "keep", "adapter", "prior",
            "adapter package; fan-in {0}".format(card.get("fan_in") or 0),
        )
    if card.get("kind") == "feature-dir" and card.get("role") == "feature":
        return _base_mark(
            card, "keep", "feature", "prior",
            "feature package; entries {0}".format(card.get("entry_count") or 0),
        )
    if len(consumers) >= 2 and not card.get("entry_count"):
        return _base_mark(
            card, "keep", "tool", "prior",
            "referenced by {0} features and has no entry".format(len(consumers)),
        )
    if (
        card.get("role") == "engine"
        and not card.get("entry_count")
        and (card.get("fan_in") or 0) >= 8
        and (card.get("fan_out") or 0) <= 3
    ):
        return _base_mark(
            card, "split", "engine", "prior",
            "fan-in {0} and no entry; mechanism stays separate".format(card.get("fan_in")),
        )
    return None


def review_mark(card):
    """Degraded unresolved mark. No Jev source and no invented probability."""
    mark = _base_mark(
        card, "review", card.get("role") or "feature", "review",
        "structural prior did not decide",
    )
    mark["target_id"] = card["id"]
    return mark


def _question_id(prefix, card_id):
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in card_id)
    return "{0}__{1}".format(prefix, safe)


def questions_for_cards(cards):
    """Shared state plus one choice, one noul, and one score per card."""
    state = {
        "cards": [
            {
                "id": card["id"],
                "leaf_name": card.get("leaf_name") or "",
                "fan_in": card.get("fan_in") or 0,
                "fan_out": card.get("fan_out") or 0,
                "entry_count": card.get("entry_count") or 0,
                "consumer_ids": list(card.get("consumer_ids") or []),
                "decl_sample": list(card.get("decl_sample") or []),
                "sibling_feature_id": card.get("sibling_feature_id") or "",
            }
            for card in cards
        ],
    }
    questions = {}
    for card in cards:
        questions[_question_id("stance", card["id"])] = {
            "type": "choice",
            "instructions": (
                "Which engineering stance fits the card whose id is {0}? "
                "Use other when the evidence is not enough."
            ).format(card["id"]),
            "criteria": dict(_STANCE_CRITERIA),
        }
        questions[_question_id("serves_one", card["id"])] = {
            "type": "noul",
            "instructions": (
                "Does the card whose id is {0} serve only one product ability?"
            ).format(card["id"]),
        }
        questions[_question_id("mechanism", card["id"])] = {
            "type": "score",
            "instructions": (
                "How strongly is the card whose id is {0} a framework mechanism?"
            ).format(card["id"]),
            "criteria": list(_SCORE_CRITERIA),
        }
    return state, questions


def _answer_dict(answer):
    if answer is None:
        return {}
    if isinstance(answer, dict):
        return dict(answer)
    view = {}
    for field in ("type", "choice", "noul", "score", "confidence"):
        if hasattr(answer, field):
            value = getattr(answer, field)
            if value is not None:
                view[field] = value
    probs = getattr(answer, "probabilities", None)
    if probs:
        view["probabilities"] = dict(probs)
    return view


def _answers_map(response):
    if isinstance(response, dict):
        raw = response.get("answers") or {}
    else:
        raw = getattr(response, "answers", None) or {}
    mapped = {}
    for name, answer in raw.items():
        mapped[name] = _answer_dict(answer)
    return mapped


def apply_official_answer(card, answers):
    """Copy choice, noul, and score from the official answer map. Never invent them."""
    stance = _answer_dict(answers.get(_question_id("stance", card["id"])))
    serves = _answer_dict(answers.get(_question_id("serves_one", card["id"])))
    mechanism = _answer_dict(answers.get(_question_id("mechanism", card["id"])))
    choice = stance.get("choice")
    if choice not in _STANCES:
        mark = review_mark(card)
        mark["evidence"] = "official response had no usable stance choice"
        return mark
    noul = serves.get("noul") if "noul" in serves else None
    score = mechanism.get("score") if "score" in mechanism else None
    if choice == "framework_mechanism":
        action, role = "split", "engine"
        target = card["id"]
    elif choice == "shared_method":
        action, role = "keep", "tool"
        target = card["id"]
    elif choice == "independent_system":
        action, role = "keep", "feature"
        target = card["id"]
    elif choice == "feature":
        role = "feature"
        if card.get("sibling_feature_id") and (noul is None or noul >= 0.5):
            action = "attach"
            target = card["sibling_feature_id"]
        elif len(card.get("consumer_ids") or []) == 1 and noul is not None and noul >= 0.5:
            action = "attach"
            target = card["consumer_ids"][0]
        else:
            action = "keep"
            target = card["id"]
    else:
        mark = review_mark(card)
        mark["evidence"] = "official stance was other"
        return mark
    mark = _base_mark(
        card, action, role, OFFICIAL_SOURCE,
        "official system_one choice={0}".format(choice),
    )
    mark["target_id"] = target
    mark["choice"] = choice
    if noul is not None:
        mark["noul"] = noul
    if score is not None:
        mark["score"] = score
    if stance.get("probabilities"):
        mark["weights"] = dict(stance["probabilities"])
    if stance.get("confidence") is not None:
        mark["confidence"] = stance["confidence"]
    return mark


def call_official_system_one(config, state, questions):
    """POST /v1/systemone through the official client. Raises if the SDK is missing."""
    try:
        from typesafe_sdk import Choice, Noul, Score, TypeSafeClient
    except ImportError as exc:
        raise RuntimeError(
            "typesafe-sdk is required for the official Jev path"
        ) from exc
    sdk_questions = {}
    for name, spec in questions.items():
        kind = spec.get("type")
        if kind == "choice":
            sdk_questions[name] = Choice(
                instructions=spec.get("instructions"),
                criteria=spec.get("criteria") or {},
            )
        elif kind == "noul":
            sdk_questions[name] = Noul(instructions=spec.get("instructions"))
        elif kind == "score":
            sdk_questions[name] = Score(
                instructions=spec.get("instructions"),
                criteria=list(spec.get("criteria") or []),
            )
        else:
            raise RuntimeError("unsupported question type")
    with TypeSafeClient(
        api_key=config.api_key,
        model=config.model,
        base_url=config.base_url,
    ) as client:
        return client.system_one(state=state, questions=sdk_questions, model=config.model)


def mark_atoms(atoms, edges, environ=None, client=None, project_root=None):
    """Return ``(marks, notice)``.

    ``client``, when passed, is ``callable(config, state, questions)`` and is
    used only after an official config is present. The CLI passes no client.
    """
    cards = build_evidence_cards(atoms or [], edges or {})
    marks = []
    unresolved = []
    for card in cards:
        decided = prior_mark(card)
        if decided is None:
            unresolved.append(card)
        else:
            marks.append(decided)
    config = official_config(environ, project_root=project_root)
    if config is None:
        for card in unresolved:
            marks.append(review_mark(card))
        marks.sort(key=lambda mark: mark["id"])
        return marks, NOTICE_NOT_CONFIGURED
    if not unresolved:
        marks.sort(key=lambda mark: mark["id"])
        return marks, None
    state, questions = questions_for_cards(unresolved)
    caller = client or call_official_system_one
    response = caller(config, state, questions)
    answers = _answers_map(response)
    for card in unresolved:
        marks.append(apply_official_answer(card, answers))
    marks.sort(key=lambda mark: mark["id"])
    return marks, None


def format_marks(marks):
    """Stable mark lines. Degraded rows never say official-jev."""
    lines = ["marks: {}".format(len(marks or []))]
    for mark in marks or []:
        choice = mark.get("choice")
        noul = mark.get("noul")
        score = mark.get("score")
        lines.append("{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}".format(
            "mark",
            mark.get("id") or "",
            mark.get("action") or "",
            mark.get("source") or "",
            mark.get("role") or "",
            choice if choice is not None else "-",
            noul if noul is not None else (score if score is not None else "-"),
        ))
    return "\n".join(lines) + "\n"
