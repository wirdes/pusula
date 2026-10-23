"""Check every card and evaluation query; exit non-zero if anything is wrong.

Usage: python scripts/validate.py
"""

from __future__ import annotations

import sys
from collections import Counter

from cards import (
    flow_cards,
    keyword_overlaps,
    load_cards,
    load_flows,
    load_queries,
    validate_cards,
    validate_flows,
    validate_queries,
)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    cards = load_cards()
    flows = load_flows()
    queries = load_queries()
    card_ids = {c["id"] for c in cards if c.get("id")}

    errors = validate_cards(cards) + validate_flows(flows, card_ids) + validate_queries(queries, card_ids)

    per_card = Counter(cid for q in queries for cid in q.get("expected") or [])
    by_status = Counter((c.get("review") or {}).get("status") for c in cards)
    by_type = Counter(q.get("type") for q in queries)

    print(f"Cards: {len(cards)}  ({', '.join(f'{k}={v}' for k, v in sorted(by_status.items(), key=str))})")
    for flow in flows:
        print(f"Flow {flow.get('id')}: {', '.join(sorted(flow_cards(flow)))}")
    print(f"Queries: {len(queries)}  ({', '.join(f'{k}={v}' for k, v in sorted(by_type.items(), key=str))})")
    uncovered = sorted(cid for cid in card_ids if per_card[cid] < 3)
    if uncovered:
        print(f"Cards with fewer than 3 test queries: {', '.join(uncovered)}")

    overlaps = keyword_overlaps(cards, queries)
    if overlaps:
        leaked = len({qid for qid, _, _ in overlaps})
        print(
            f"Warning: {leaked} test queries overlap a keyword of their expected card, so scores that "
            "include keywords are optimistic. First few:"
        )
        for qid, card_id, keyword in overlaps[:5]:
            print(f"  - {qid} ~ {card_id}: '{keyword}'")

    if errors:
        print(f"\n{len(errors)} problem(s):")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("\nAll cards and queries are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
