"""Try Pusula's retrieval by hand: type a question, see which card it finds.

Runs offline by default, using models already in the local Hugging Face cache.
When the best match belongs to a decision flow, the flow's question is asked
first and your answer picks the card, just as the app will do.

Usage:
  python scripts/ask.py                            # interactive
  python scripts/ask.py "enkaz altındayım"          # one question
  python scripts/ask.py --model e5-small           # compare another model
  python scripts/ask.py --online                   # allow downloading a missing model
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap

import numpy as np

from cards import DEFAULT_TEXT_FIELDS, card_text, flow_groups, flow_text, load_cards, load_flows
from retrieval_baseline import EMBEDDING_MODELS, LEXICAL_MODELS, Bm25Retriever, EmbeddingRetriever

DEFAULT_MODEL = "modernbert-tr-embed"

# (no_match, confident) score cut-offs, read off results/baseline.json (38 cards, 214 queries).
# At 0.50, 98% of in-scope questions still get an answer; at 0.58, 96% of out-of-scope ones are
# rejected. They are tuned on a small, self-written test set, so treat them as a starting point.
THRESHOLDS = {"modernbert-tr-embed": (0.50, 0.58)}

WRAP = textwrap.TextWrapper(width=88, initial_indent="    ", subsequent_indent="      ")


def show_card(card: dict, score: float | None = None) -> None:
    suffix = f", skor {score:.2f}" if score is not None else ""
    print(f"  {card['title']}  ({card['id']}{suffix})")
    print(WRAP.fill(" ".join(card["summary"].split())))
    for i, step in enumerate(card["steps"], 1):
        print(WRAP.fill(f"{i}. {step}"))
    for item in card.get("dont") or []:
        print(WRAP.fill(f"YAPMA: {item}"))


def run_flow(flow: dict, cards_by_id: dict[str, dict], score: float | None = None) -> None:
    suffix = f", skor {score:.2f}" if score is not None else ""
    print(f"  {flow['title']}  (akış: {flow['id']}{suffix})")
    node_id = flow["start"]
    while True:
        node = flow["nodes"][node_id]
        print(WRAP.fill(node["question"]))
        answers = node["answers"]
        for i, option in enumerate(answers, 1):
            print(f"      {i}) {option['label']}")
        choice = None
        while choice is None:
            try:
                raw = input("    Cevap numarası: ").strip()
            except EOFError:
                print("\n    (cevap verilmedi)")
                return
            if raw.isdigit() and 1 <= int(raw) <= len(answers):
                choice = answers[int(raw) - 1]
            else:
                print(f"    1 ile {len(answers)} arasında bir numara yaz.")
        print()
        if choice.get("note"):
            print(WRAP.fill(choice["note"]))
        if choice.get("card"):
            show_card(cards_by_id[choice["card"]])
            return
        if choice.get("message"):
            print(WRAP.fill(choice["message"]))
            return
        node_id = choice["next"]


def answer(question: str, retriever, targets: list[dict], groups: dict[str, str], by_id: dict, thresholds) -> None:
    scores = retriever.scores(question)
    # Cards that belong to a flow are shown through that flow, so collapse them onto it.
    best: dict[str, float] = {}
    for i in np.argsort(-scores):
        target_id = groups.get(targets[i]["id"], targets[i]["id"])
        best.setdefault(target_id, float(scores[i]))
    ranked = list(best.items())[:3]
    top_id, top = ranked[0]
    print()
    if thresholds and top < thresholds[0]:
        print("Bu konuda bir kartım yok. Hayati bir durumsa 112'yi ara.")
        nearest = ", ".join(f"{by_id[t]['title']} ({s:.2f})" for t, s in ranked)
        print(f"  (en yakınlar: {nearest})")
    elif thresholds and top < thresholds[1]:
        print("Emin değilim. Şunlardan biri olabilir:")
        for rank, (target_id, score) in enumerate(ranked, 1):
            print(f"  {rank}. {by_id[target_id]['title']}  ({target_id}, skor {score:.2f})")
    elif "nodes" in by_id[top_id]:
        run_flow(by_id[top_id], by_id, top)
    else:
        show_card(by_id[top_id], top)
        others = ", ".join(f"{by_id[t]['title']} ({s:.2f})" for t, s in ranked[1:])
        print(f"  Diğer olası kartlar: {others}")
    print()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question", nargs="*", help="question to ask; omit for interactive mode")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=[*LEXICAL_MODELS, *EMBEDDING_MODELS])
    parser.add_argument("--online", action="store_true", help="allow downloading a model that is not cached yet")
    parser.add_argument("--student", help="use a model trained by train_student.py, saved at this path")
    args = parser.parse_args()

    if args.student:
        EMBEDDING_MODELS["pusula-student"] = {"id": args.student, "query_prefix": "query: ", "doc_prefix": "passage: "}
        args.model = "pusula-student"

    if not args.online:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    cards = load_cards()
    flows = load_flows()
    targets = cards + flows
    docs = [card_text(c, DEFAULT_TEXT_FIELDS) for c in cards] + [flow_text(f) for f in flows]
    by_id = {t["id"]: t for t in targets}
    groups = flow_groups(flows)

    print(f"{len(cards)} kart, {len(flows)} karar akışı, model: {args.model}. Yükleniyor...", flush=True)
    if args.model in LEXICAL_MODELS:
        retriever = Bm25Retriever(docs, LEXICAL_MODELS[args.model])
    else:
        retriever = EmbeddingRetriever(EMBEDDING_MODELS[args.model], docs)
    thresholds = THRESHOLDS.get(args.model)
    print("UYARI: Kartlar taslaktır ve henüz bir sağlık profesyoneli tarafından onaylanmadı.")

    if args.question:
        answer(" ".join(args.question), retriever, targets, groups, by_id, thresholds)
        return 0

    while True:
        try:
            question = input("Soru (çıkmak için boş bırak): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            break
        answer(question, retriever, targets, groups, by_id, thresholds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
