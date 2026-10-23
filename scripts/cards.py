"""Load and validate Pusula info cards, decision flows and evaluation queries."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = REPO_ROOT / "cards"
FLOWS_DIR = REPO_ROOT / "flows"
QUERIES_PATH = REPO_ROOT / "eval" / "queries.jsonl"

CATEGORIES = {"deprem", "ilk-yardim", "tehlike", "hayatta-kalma", "iletisim", "hazirlik", "psikolojik"}
PRIORITIES = {"kritik", "yuksek", "normal"}
REVIEW_STATUSES = {"taslak", "inceleniyor", "onaylandi"}
QUERY_TYPES = {"resmi", "gunluk", "diakritiksiz", "yazim_hatasi", "panik", "dolayli", "ses", "kapsam_disi"}

REQUIRED_FIELDS = ("id", "title", "category", "priority", "summary", "steps", "sources", "review")
LIST_FIELDS = ("steps", "dont", "keywords")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Keywords are left out by default: they were written alongside the test queries and
# overlap them heavily, so including them would overstate retrieval quality.
DEFAULT_TEXT_FIELDS = ("title", "summary", "steps")

# Turkish-aware lowercasing ("I" -> "ı", "İ" -> "i"), then fold diacritics so that
# "cikamiyorum" and "çıkamıyorum" become the same token.
_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})
_FOLD = str.maketrans("çğıöşüâîû", "cgiosuaiu")


def tokenize(text: str, prefix_len: int | None = None) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.translate(_TR_LOWER).lower().translate(_FOLD))
    if prefix_len:
        # Keeping the first 5 letters is a cheap, well-known stemmer for Turkish.
        tokens = [t[:prefix_len] for t in tokens]
    return tokens


def _load_yaml_dir(directory: Path) -> list[dict]:
    items = []
    for path in sorted(directory.glob("*.yaml")):
        with path.open(encoding="utf-8") as f:
            item = yaml.safe_load(f)
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}: top level must be a mapping")
        item["_path"] = path
        items.append(item)
    return items


def load_cards(cards_dir: Path = CARDS_DIR) -> list[dict]:
    return _load_yaml_dir(cards_dir)


def load_flows(flows_dir: Path = FLOWS_DIR) -> list[dict]:
    return _load_yaml_dir(flows_dir) if flows_dir.exists() else []


def validate_cards(cards: list[dict]) -> list[str]:
    errors = []
    ids = [c.get("id") for c in cards]
    known = set(ids)

    for card in cards:
        name = card["_path"].name
        for field in REQUIRED_FIELDS:
            if card.get(field) in (None, "", []):
                errors.append(f"{name}: missing required field '{field}'")

        card_id = card.get("id")
        if card_id is not None:
            if not ID_RE.match(str(card_id)):
                errors.append(f"{name}: id '{card_id}' must be lowercase words joined by '-'")
            if card["_path"].stem != card_id:
                errors.append(f"{name}: file name must match id '{card_id}'")
            if ids.count(card_id) > 1:
                errors.append(f"{name}: duplicate id '{card_id}'")

        if card.get("category") not in CATEGORIES:
            errors.append(f"{name}: unknown category '{card.get('category')}'")
        if card.get("priority") not in PRIORITIES:
            errors.append(f"{name}: unknown priority '{card.get('priority')}'")

        for field in ("title", "summary", "seek_help"):
            if field in card and card[field] is not None and not isinstance(card[field], str):
                errors.append(f"{name}: '{field}' must be text")
        for field in LIST_FIELDS:
            value = card.get(field)
            if value is None:
                continue
            if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
                # A YAML item like "Kaynatma: ..." silently turns into a mapping; catch it here.
                errors.append(f"{name}: '{field}' must be a list of text items (quote items containing ': ')")

        for related in card.get("related") or []:
            if related not in known:
                errors.append(f"{name}: related card '{related}' does not exist")

        sources = card.get("sources") or []
        if not isinstance(sources, list) or not all(isinstance(s, dict) and s.get("name") for s in sources):
            errors.append(f"{name}: every source needs a 'name'")

        review = card.get("review")
        if not isinstance(review, dict) or review.get("status") not in REVIEW_STATUSES:
            errors.append(f"{name}: review.status must be one of {sorted(REVIEW_STATUSES)}")
        elif review["status"] == "onaylandi" and not (review.get("reviewer") and review.get("date")):
            errors.append(f"{name}: approved cards need review.reviewer and review.date")

    return errors


def flow_cards(flow: dict) -> set[str]:
    """Every card a flow can end on."""
    return {
        answer["card"]
        for node in (flow.get("nodes") or {}).values()
        if isinstance(node, dict)
        for answer in node.get("answers") or []
        if isinstance(answer, dict) and answer.get("card")
    }


def validate_flows(flows: list[dict], card_ids: set[str]) -> list[str]:
    errors = []
    ids = [f.get("id") for f in flows]
    owner: dict[str, str] = {}

    for flow in flows:
        name = flow["_path"].name
        flow_id = flow.get("id")
        for field in ("id", "title", "category", "priority", "summary", "start", "nodes", "sources", "review"):
            if flow.get(field) in (None, "", [], {}):
                errors.append(f"{name}: missing required field '{field}'")
        if flow_id is not None:
            if not ID_RE.match(str(flow_id)):
                errors.append(f"{name}: id '{flow_id}' must be lowercase words joined by '-'")
            if flow["_path"].stem != flow_id:
                errors.append(f"{name}: file name must match id '{flow_id}'")
            if ids.count(flow_id) > 1:
                errors.append(f"{name}: duplicate flow id '{flow_id}'")
            if flow_id in card_ids:
                errors.append(f"{name}: flow id '{flow_id}' clashes with a card id")
        if flow.get("category") not in CATEGORIES:
            errors.append(f"{name}: unknown category '{flow.get('category')}'")
        if flow.get("priority") not in PRIORITIES:
            errors.append(f"{name}: unknown priority '{flow.get('priority')}'")
        review = flow.get("review")
        if not isinstance(review, dict) or review.get("status") not in REVIEW_STATUSES:
            errors.append(f"{name}: review.status must be one of {sorted(REVIEW_STATUSES)}")

        nodes = flow.get("nodes")
        if not isinstance(nodes, dict):
            continue
        if flow.get("start") not in nodes:
            errors.append(f"{name}: start node '{flow.get('start')}' does not exist")
            continue

        for node_id, node in nodes.items():
            where = f"{name}: node '{node_id}'"
            if not isinstance(node, dict) or not isinstance(node.get("question"), str):
                errors.append(f"{where} needs a 'question'")
                continue
            answers = node.get("answers")
            if not isinstance(answers, list) or len(answers) < 2:
                errors.append(f"{where} needs at least two answers")
                continue
            for answer in answers:
                if not isinstance(answer, dict) or not isinstance(answer.get("label"), str):
                    errors.append(f"{where}: every answer needs a 'label'")
                    continue
                targets = [k for k in ("card", "next", "message") if answer.get(k)]
                if len(targets) != 1:
                    errors.append(f"{where}: answer '{answer['label']}' needs exactly one of card / next / message")
                elif targets[0] == "card" and answer["card"] not in card_ids:
                    errors.append(f"{where}: card '{answer['card']}' does not exist")
                elif targets[0] == "next" and answer["next"] not in nodes:
                    errors.append(f"{where}: next node '{answer['next']}' does not exist")

        # Every node must be reachable from the start, and following answers must always end.
        reached, on_path = set(), set()

        def walk(node_id: str) -> None:
            if node_id in on_path:
                errors.append(f"{name}: node '{node_id}' is part of a loop")
                return
            if node_id in reached or not isinstance(nodes.get(node_id), dict):
                return
            reached.add(node_id)
            on_path.add(node_id)
            for answer in nodes[node_id].get("answers") or []:
                if isinstance(answer, dict) and answer.get("next") in nodes:
                    walk(answer["next"])
            on_path.discard(node_id)

        walk(flow["start"])
        for node_id in sorted(set(nodes) - reached):
            errors.append(f"{name}: node '{node_id}' is never reached from the start")

        for card_id in flow_cards(flow):
            if card_id in owner and owner[card_id] != flow_id:
                errors.append(f"{name}: card '{card_id}' already belongs to flow '{owner[card_id]}'")
            owner[card_id] = flow_id
    return errors


def flow_groups(flows: list[dict]) -> dict[str, str]:
    """Map each flow id, and each card a flow leads to, onto that flow's id."""
    groups = {}
    for flow in flows:
        groups[flow["id"]] = flow["id"]
        for card_id in flow_cards(flow):
            groups[card_id] = flow["id"]
    return groups


def flow_text(flow: dict) -> str:
    return "\n".join([flow["title"], " ".join(str(flow["summary"]).split())])


def load_queries(path: Path = QUERIES_PATH) -> list[dict]:
    queries = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                query = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"{path.name}:{line_no}: invalid JSON ({e})") from e
            query["_line"] = line_no
            queries.append(query)
    return queries


def validate_queries(queries: list[dict], card_ids: set[str]) -> list[str]:
    errors = []
    seen = set()
    for query in queries:
        where = f"queries.jsonl:{query['_line']}"
        qid = query.get("id")
        if not qid:
            errors.append(f"{where}: missing id")
        elif qid in seen:
            errors.append(f"{where}: duplicate id '{qid}'")
        seen.add(qid)

        if not isinstance(query.get("text"), str) or not query["text"].strip():
            errors.append(f"{where}: missing text")
        if query.get("type") not in QUERY_TYPES:
            errors.append(f"{where}: unknown type '{query.get('type')}'")

        expected = query.get("expected")
        if not isinstance(expected, list):
            errors.append(f"{where}: 'expected' must be a list of card ids")
            continue
        if query.get("type") == "kapsam_disi" and expected:
            errors.append(f"{where}: out-of-scope queries must have an empty 'expected' list")
        if query.get("type") != "kapsam_disi" and not expected:
            errors.append(f"{where}: in-scope queries need at least one expected card")
        for card_id in expected:
            if card_id not in card_ids:
                errors.append(f"{where}: expected card '{card_id}' does not exist")
    return errors


def keyword_overlaps(cards: list[dict], queries: list[dict]) -> list[tuple[str, str, str]]:
    """Queries whose text contains (or is contained in) a keyword of their expected card."""
    by_id = {c.get("id"): c for c in cards}
    overlaps = []
    for query in queries:
        q = " ".join(tokenize(query.get("text", "")))
        for card_id in query.get("expected") or []:
            for keyword in (by_id.get(card_id) or {}).get("keywords") or []:
                k = " ".join(tokenize(keyword))
                if k == q or (len(k) > 8 and k in q) or (len(q) > 8 and q in k):
                    overlaps.append((query["id"], card_id, keyword))
    return overlaps


def card_text(card: dict, fields: tuple[str, ...] = DEFAULT_TEXT_FIELDS) -> str:
    """Flatten the chosen card fields into one passage for retrieval."""
    parts = []
    for field in fields:
        value = card.get(field)
        if not value:
            continue
        if isinstance(value, list):
            parts.append(" ".join(str(item) for item in value))
        else:
            parts.append(" ".join(str(value).split()))
    return "\n".join(parts)
