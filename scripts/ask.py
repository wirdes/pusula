"""Try Pusula's retrieval by hand: type a question, see which card it finds.

Runs offline by default, using models already in the local Hugging Face cache.

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

from cards import DEFAULT_TEXT_FIELDS, card_text, load_cards
from retrieval_baseline import EMBEDDING_MODELS, LEXICAL_MODELS, Bm25Retriever, EmbeddingRetriever

DEFAULT_MODEL = "modernbert-tr-embed"

# (no_match, confident) score cut-offs, read off results/baseline.json (38 cards, 214 queries).
# At 0.50, 98% of in-scope questions still get an answer; at 0.58, 96% of out-of-scope ones are
# rejected. They are tuned on a small, self-written test set, so treat them as a starting point.
THRESHOLDS = {"modernbert-tr-embed": (0.50, 0.58)}

WRAP = textwrap.TextWrapper(width=88, initial_indent="    ", subsequent_indent="      ")


def show_card(card: dict, score: float) -> None:
    print(f"  {card['title']}  ({card['id']}, skor {score:.2f})")
    print(WRAP.fill(" ".join(card["summary"].split())))
    for i, step in enumerate(card["steps"], 1):
        print(WRAP.fill(f"{i}. {step}"))
    for item in card.get("dont") or []:
        print(WRAP.fill(f"YAPMA: {item}"))


def answer(question: str, retriever, cards: list[dict], thresholds: tuple[float, float] | None) -> None:
    scores = retriever.scores(question)
    order = np.argsort(-scores)[:3]
    top = float(scores[order[0]])
    print()
    if thresholds and top < thresholds[0]:
        print("Bu konuda bir kartım yok. Hayati bir durumsa 112'yi ara.")
        nearest = ", ".join(f"{cards[i]['title']} ({scores[i]:.2f})" for i in order)
        print(f"  (en yakınlar: {nearest})")
    elif thresholds and top < thresholds[1]:
        print("Emin değilim. Şunlardan biri olabilir:")
        for rank, i in enumerate(order, 1):
            print(f"  {rank}. {cards[i]['title']}  ({cards[i]['id']}, skor {scores[i]:.2f})")
    else:
        show_card(cards[order[0]], top)
        others = ", ".join(f"{cards[i]['title']} ({scores[i]:.2f})" for i in order[1:])
        print(f"  Diğer olası kartlar: {others}")
    print()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question", nargs="*", help="question to ask; omit for interactive mode")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=[*LEXICAL_MODELS, *EMBEDDING_MODELS])
    parser.add_argument("--online", action="store_true", help="allow downloading a model that is not cached yet")
    args = parser.parse_args()

    if not args.online:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    cards = load_cards()
    docs = [card_text(c, DEFAULT_TEXT_FIELDS) for c in cards]
    print(f"{len(cards)} kart, model: {args.model}. Yükleniyor...", flush=True)
    if args.model in LEXICAL_MODELS:
        retriever = Bm25Retriever(docs, LEXICAL_MODELS[args.model])
    else:
        retriever = EmbeddingRetriever(EMBEDDING_MODELS[args.model], docs)
    thresholds = THRESHOLDS.get(args.model)
    print("UYARI: Kartlar taslaktır ve henüz bir sağlık profesyoneli tarafından onaylanmadı.")

    if args.question:
        answer(" ".join(args.question), retriever, cards, thresholds)
        return 0

    while True:
        try:
            question = input("Soru (çıkmak için boş bırak): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            break
        answer(question, retriever, cards, thresholds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
