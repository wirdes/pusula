"""Turn raw synthetic messages into train/dev files for Pusula's own retrieval model.

Steps:
  0. judge          drop messages the second LLM rejected (data/synthetic/judgments/, from judge_queries.py)
  1. clean          drop empty, too short or too long and duplicate messages
  2. decontaminate  drop near-copies of the evaluation set (eval/queries.jsonl), which is
                    never used for training
  3. augment        add rule-based variants: no Turkish characters, typos, speech-like
  4. teacher        check every pair with the teacher model (ModernBERT-TR-Embed), drop
                    eval look-alikes it finds, set aside pairs it ranks far off, and mine
                    hard negatives
  5. split          dev = 10% of base messages per card; a message and its variants always
                    land in the same split

Usage:
  python scripts/build_dataset.py
  python scripts/build_dataset.py --raw data/synthetic/raw/gpt-oss-20b.jsonl --out-dir some/dir
  python scripts/build_dataset.py --no-teacher     # skip the model: no filtering, no hard negatives
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from cards import DEFAULT_TEXT_FIELDS, REPO_ROOT, card_text, flow_groups, load_cards, load_flows, load_queries, tokenize

RAW_DIR = REPO_ROOT / "data" / "synthetic" / "raw"
JUDGE_DIR = REPO_ROOT / "data" / "synthetic" / "judgments"
DATA_DIR = REPO_ROOT / "data"
TEACHER = "modernbert-tr-embed"
OUT_OF_SCOPE = "kapsam_disi"

_ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})


def key(text: str) -> str:
    return " ".join(tokenize(text))


def stems(text: str) -> set[str]:
    return set(tokenize(text, prefix_len=5))


def clean(text: str) -> str:
    text = re.sub(r"^\s*\d+[.)]\s+", "", text)
    return re.sub(r"\s+", " ", text).strip().strip("\"'“”‘’").strip()


def strip_diacritics(text: str) -> str:
    return text.translate(_ASCII)


def add_typos(text: str, rng: random.Random) -> str:
    words = text.split()
    candidates = [i for i, w in enumerate(words) if len(w) >= 4 and w.isalpha()]
    if not candidates:
        return text
    for _ in range(rng.choice([1, 1, 2])):
        i = rng.choice(candidates)
        w = words[i]
        if len(w) < 4:  # a previous edit may already have shortened this word
            continue
        j = rng.randrange(2, len(w) - 1)
        if rng.random() < 0.5:
            w = w[:j] + w[j + 1 :]  # drop a letter
        else:
            w = w[: j - 1] + w[j] + w[j - 1] + w[j + 1 :]  # swap two neighbouring letters
        words[i] = w
    return " ".join(words)


def speech_like(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text.translate(_TR_LOWER).lower())
    return re.sub(r"\s+", " ", text).strip()


class EvalGuard:
    """Rejects messages that are exact or near copies of an evaluation query."""

    def __init__(self, eval_queries: list[dict], jaccard: float):
        self.keys = {key(q["text"]) for q in eval_queries}
        self.stem_sets = [stems(q["text"]) for q in eval_queries]
        self.jaccard = jaccard

    def is_near(self, text: str) -> bool:
        if key(text) in self.keys:
            return True
        s = stems(text)
        if len(s) < 3:
            return False
        return any(len(e) >= 3 and len(s & e) / len(s | e) >= self.jaccard for e in self.stem_sets)


def load_raw(paths: list[Path]) -> list[dict]:
    records = []
    for path in paths:
        with path.open(encoding="utf-8") as f:
            records += [json.loads(line) for line in f if line.strip()]
    return records


def load_judgments(directory: Path) -> dict[tuple, str]:
    """(card, near, raw text) -> "kabul" | "ret"; a "ret" from any judge wins."""
    verdicts = {}
    for record in load_raw(sorted(directory.glob("*.jsonl"))) if directory.exists() else []:
        k = (record.get("card"), record.get("near"), record["text"])
        if verdicts.get(k) != "ret":
            verdicts[k] = record["verdict"]
    return verdicts


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", nargs="*", type=Path, help="raw files (default: data/synthetic/raw/*.jsonl)")
    parser.add_argument("--out-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--dev-fraction", type=float, default=0.1)
    parser.add_argument("--eval-jaccard", type=float, default=0.75, help="stem overlap above which a message counts as an eval copy")
    parser.add_argument("--eval-cosine", type=float, default=0.95, help="teacher similarity above which a message counts as an eval copy")
    parser.add_argument("--max-teacher-rank", type=int, default=5,
                        help="set aside pairs whose card the teacher ranks lower than this (cards of one decision flow count as one)")
    parser.add_argument("--no-teacher", action="store_true", help="skip the teacher model")
    parser.add_argument("--no-judgments", action="store_true", help="ignore the second LLM's verdicts")
    parser.add_argument("--online", action="store_true", help="allow downloading the teacher if it is not cached")
    args = parser.parse_args()

    raw_paths = args.raw or sorted(RAW_DIR.glob("*.jsonl"))
    if not raw_paths:
        parser.error(f"no raw files found in {RAW_DIR}; run scripts/generate_queries.py first")
    rng = random.Random(args.seed)
    cards = load_cards()
    card_ids = [c["id"] for c in cards]
    guard = EvalGuard(load_queries(), args.eval_jaccard)
    dropped = Counter()

    # 1-2. Clean, deduplicate and drop eval copies. Base messages are deduplicated ignoring
    # case and punctuation but not diacritics, so the diacritic-free variants added in step 3
    # are not mistaken for copies; variants themselves only need to differ in exact text.
    seen, seen_texts, bases, oos = set(), set(), [], []
    judgments = {} if args.no_judgments else load_judgments(JUDGE_DIR)
    unjudged = 0
    for rec in load_raw(raw_paths):
        verdict = judgments.get((rec.get("card"), rec.get("near"), rec.get("text")))
        if verdict == "ret":
            dropped["yargic_reddetti"] += 1
            continue
        unjudged += verdict is None
        text = clean(str(rec.get("text", "")))
        target = rec.get("card")
        if not 3 <= len(text) <= 220 or not tokenize(text):
            dropped["bos_ya_da_uzunluk"] += 1
            continue
        if target is not None and target not in card_ids:
            dropped["bilinmeyen_kart"] += 1
            continue
        if speech_like(text) in seen:
            dropped["tekrar"] += 1
            continue
        if guard.is_near(text):
            dropped["test_setine_benziyor"] += 1
            continue
        seen.add(speech_like(text))
        seen_texts.add(text)
        if target is None:
            oos.append({"query": text, "near": rec.get("near"), "model": rec.get("model")})
        else:
            bases.append({"query": text, "card": target, "style": rec.get("style"), "model": rec.get("model")})

    # 3. Rule-based variants of each base message.
    examples = []
    per_card = Counter()
    for base in bases:
        per_card[base["card"]] += 1
        base_id = f"{base['card']}:{per_card[base['card']]}"
        variants = [("temel", base["query"])]
        ascii_text = strip_diacritics(base["query"])
        if ascii_text != base["query"] and rng.random() < 0.5:
            variants.append(("diakritiksiz", ascii_text))
        if rng.random() < 0.35:
            variants.append(("yazim_hatasi", add_typos(base["query"], rng)))
        if base["style"] not in ("ses", "panik") and rng.random() < 0.25:
            variants.append(("ses", speech_like(base["query"])))
        for variant, text in variants:
            if variant != "temel":
                if text in seen_texts:
                    dropped["tekrar"] += 1
                    continue
                if guard.is_near(text):
                    dropped["test_setine_benziyor"] += 1
                    continue
                seen_texts.add(text)
            examples.append({**base, "query": text, "variant": variant, "base_id": base_id})

    # 4. Teacher check and hard negatives.
    rejected = []
    if not args.no_teacher:
        if not args.online:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from retrieval_baseline import EMBEDDING_MODELS, EmbeddingRetriever

        print(f"Loading teacher {TEACHER}...", flush=True)
        teacher = EmbeddingRetriever(EMBEDDING_MODELS[TEACHER], [card_text(c, DEFAULT_TEXT_FIELDS) for c in cards])
        eval_emb = teacher.encode_queries([q["text"] for q in load_queries()])
        print(f"Embedding {len(examples) + len(oos)} messages...", flush=True)
        emb = teacher.encode_queries([e["query"] for e in examples]) if examples else np.zeros((0, eval_emb.shape[1]))
        oos_emb = teacher.encode_queries([o["query"] for o in oos]) if oos else np.zeros((0, eval_emb.shape[1]))

        near_eval = (emb @ eval_emb.T).max(axis=1) if len(emb) else []
        card_scores = emb @ teacher.doc_emb.T if len(emb) else []
        groups = flow_groups(load_flows())
        scored = []
        for example, eval_sim, scores in zip(examples, near_eval, card_scores):
            if eval_sim >= args.eval_cosine:
                dropped["test_setine_benziyor"] += 1
                continue
            order = np.argsort(-scores)
            positive = card_ids.index(example["card"])
            example["teacher_rank"] = int(np.where(order == positive)[0][0]) + 1
            # Inside a decision flow the teacher mixes up the two sides (that is why the flow exists),
            # so it only judges whether the message is about the right situation; the side comes from
            # the generation prompt.
            grouped = list(dict.fromkeys(groups.get(card_ids[i], card_ids[i]) for i in order))
            example["teacher_group_rank"] = grouped.index(groups.get(example["card"], example["card"])) + 1
            example["teacher_top"] = [[card_ids[i], round(float(scores[i]), 4)] for i in order[:10]]
            example["hard_negatives"] = [card_ids[i] for i in order if i != positive][:3]
            scored.append(example)

        # Only the LLM-written base message is judged by the teacher. The teacher is weak on
        # exactly the noise the variants add (no diacritics, typos), so variants inherit their
        # base's verdict and hard negatives instead of being judged on their own.
        bases_ok = {e["base_id"]: e for e in scored if e["variant"] == "temel"}
        kept = []
        for example in scored:
            base = bases_ok.get(example["base_id"])
            if base is None:
                dropped["test_setine_benziyor"] += 1  # its base was an eval look-alike
                continue
            if base["teacher_group_rank"] > args.max_teacher_rank:
                reason = "ogretmen_uyumsuz" if example is base else "temeli_ayrildi"
                rejected.append({**example, "reason": reason})
                dropped[reason] += 1
                continue
            example["hard_negatives"] = base["hard_negatives"]
            kept.append(example)
        examples = kept

        kept_oos = []
        oos_near_eval = (oos_emb @ eval_emb.T).max(axis=1) if len(oos_emb) else []
        oos_scores = oos_emb @ teacher.doc_emb.T if len(oos_emb) else []
        for item, eval_sim, scores in zip(oos, oos_near_eval, oos_scores):
            if eval_sim >= args.eval_cosine:
                dropped["test_setine_benziyor"] += 1
                continue
            best = int(np.argmax(scores))
            item["teacher_top"] = [[card_ids[best], round(float(scores[best]), 4)]]
            kept_oos.append(item)
        oos = kept_oos
    else:
        for example in examples:
            example["hard_negatives"] = []

    # 5. Split by base message so variants never leak across train and dev.
    bases_by_card = defaultdict(list)
    for base_id in dict.fromkeys(e["base_id"] for e in examples):
        bases_by_card[base_id.split(":")[0]].append(base_id)
    dev_bases = set()
    for card_id, ids in bases_by_card.items():
        rng.shuffle(ids)
        if len(ids) >= 5:
            dev_bases.update(ids[: max(1, round(args.dev_fraction * len(ids)))])
    train = [e for e in examples if e["base_id"] not in dev_bases]
    dev = [e for e in examples if e["base_id"] in dev_bases]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("dev", dev), ("oos", oos), ("rejected", rejected)):
        with (args.out_dir / f"{name}.jsonl").open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    write_stats(args.out_dir / "stats.md", raw_paths, cards, train, dev, oos, rejected, dropped, not args.no_teacher,
                None if args.no_judgments else unjudged)
    print(f"train={len(train)} dev={len(dev)} oos={len(oos)} rejected={len(rejected)} dropped={dict(dropped)}")
    if not args.no_judgments and unjudged:
        print(f"Warning: {unjudged} raw messages have no verdict from the judge; run scripts/judge_queries.py")
    print(f"Wrote {args.out_dir}")
    return 0


def write_stats(path: Path, raw_paths, cards, train, dev, oos, rejected, dropped, used_teacher: bool,
                unjudged: int | None) -> None:
    by_card_train = Counter(e["card"] for e in train)
    by_card_dev = Counter(e["card"] for e in dev)
    by_variant = Counter(e["variant"] for e in train + dev)
    by_style = Counter(e["style"] for e in train + dev if e["variant"] == "temel")
    lines = [
        "# Sentetik eğitim verisi",
        "",
        f"- Ham dosyalar: {', '.join(p.name for p in raw_paths)}",
        f"- Eğitim: {len(train)}, geliştirme (dev): {len(dev)}, kapsam dışı: {len(oos)}, öğretmenin ayırdığı: {len(rejected)}",
        f"- Öğretmen kontrolü: {'ModernBERT-TR-Embed' if used_teacher else 'yapılmadı'}",
        f"- Yargıç: {'kullanılmadı' if unjudged is None else f'kullanıldı; kararı olmayan ham mesaj: {unjudged}'}",
        "",
        "## Atılanlar",
        "",
        "| Neden | Sayı |",
        "|---|---|",
        *[f"| {reason} | {count} |" for reason, count in sorted(dropped.items())],
        "",
        "## Varyantlar",
        "",
        "| Varyant | Sayı |",
        "|---|---|",
        *[f"| {v} | {n} |" for v, n in sorted(by_variant.items())],
        "",
        "## Temel mesajların yazım tarzı",
        "",
        "| Tarz | Sayı |",
        "|---|---|",
        *[f"| {s} | {n} |" for s, n in sorted(by_style.items(), key=lambda kv: str(kv[0]))],
        "",
        "## Kart başına örnek",
        "",
        "| Kart | Eğitim | Dev |",
        "|---|---|---|",
        *[f"| {c['id']} | {by_card_train[c['id']]} | {by_card_dev[c['id']]} |" for c in cards],
    ]
    thin = [c["id"] for c in cards if by_card_train[c["id"]] < 50]
    if thin:
        lines += ["", f"50'den az eğitim örneği olan kartlar: {', '.join(thin)}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
