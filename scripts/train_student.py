"""Fine-tune Pusula's own retrieval model (the student) on the synthetic dataset.

Starts from multilingual-e5-small and trains it so that each user message lands closest
to its card. Every step scores the batch of messages against *all* cards (there are only
a few dozen), so the loss is a softmax over the whole card set: every other card is a
negative, the easily confused ones included, and a card is never mistaken for a negative
of its own message the way in-batch negatives can be when two messages share a card.

Uses the GPU when PyTorch sees one (ROCm or CUDA), otherwise the CPU. The best model by
dev MRR is saved in Sentence Transformers format outside the repo, so it can be measured
with `retrieval_baseline.py --student PATH` and tried with `ask.py --student PATH`.

Usage:
  python scripts/train_student.py
  python scripts/train_student.py --max-steps 20 --out some/dir     # quick check
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

# AMD's PyTorch notes report GPU resets on RX 9070 cards while fine-tuning unless hipBLASLt
# is turned off; it is a ROCm-only switch and has no effect elsewhere.
os.environ.setdefault("TORCH_BLAS_PREFER_HIPBLASLT", "0")

import numpy as np

from cards import DEFAULT_TEXT_FIELDS, REPO_ROOT, card_text, flow_groups, load_cards, load_flows

DEFAULT_OUT = Path.home() / ".cache" / "pusula" / "models" / "pusula-e5-small-v0"


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", default="intfloat/multilingual-e5-small")
    parser.add_argument("--query-prefix", default="query: ")
    parser.add_argument("--doc-prefix", default="passage: ")
    parser.add_argument("--train", type=Path, default=REPO_ROOT / "data" / "train.jsonl")
    parser.add_argument("--dev", type=Path, default=REPO_ROOT / "data" / "dev.jsonl")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--warmup", type=float, default=0.1, help="fraction of steps")
    parser.add_argument("--scale", type=float, default=20.0, help="inverse temperature for the card softmax")
    parser.add_argument("--query-max-len", type=int, default=64)
    parser.add_argument("--doc-max-len", type=int, default=256)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--max-steps", type=int, help="stop early (for a quick check)")
    parser.add_argument("--cpu", action="store_true", help="train on the CPU even if a GPU is available")
    # PyTorch 2.12 + ROCm 7.14 on Windows fails with hipErrorInvalidValue inside SDPA attention on
    # gfx1201 (RX 9070 XT); the plain "eager" attention works for both the forward and backward pass.
    parser.add_argument("--attn", default="eager", help="attention implementation passed to transformers")
    parser.add_argument("--online", action="store_true", help="allow downloading the base model")
    args = parser.parse_args()

    if not args.online:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch
    import torch.nn.functional as F
    from sentence_transformers import SentenceTransformer
    from transformers import get_linear_schedule_with_warmup

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    device_name = torch.cuda.get_device_name(0) if device.type == "cuda" else "CPU"
    print(f"Device: {device_name} (torch {torch.__version__})", flush=True)

    cards = load_cards()
    groups = flow_groups(load_flows())
    card_ids = [c["id"] for c in cards]
    index = {card_id: i for i, card_id in enumerate(card_ids)}
    docs = [args.doc_prefix + card_text(c, DEFAULT_TEXT_FIELDS) for c in cards]
    train = load_jsonl(args.train)
    dev = load_jsonl(args.dev)
    print(f"{len(cards)} cards, {len(train)} train and {len(dev)} dev examples", flush=True)

    model = SentenceTransformer(args.base, device=str(device), model_kwargs={"attn_implementation": args.attn})

    # Sentence Transformers 6 renamed tokenize() to preprocess() and may add non-tensor entries.
    preprocess = getattr(model, "preprocess", None) or model.tokenize

    def encode(texts: list[str], max_len: int) -> "torch.Tensor":
        model.max_seq_length = max_len
        features = {k: v.to(device) if hasattr(v, "to") else v for k, v in preprocess(texts).items()}
        return F.normalize(model(features)["sentence_embedding"], dim=-1)

    def evaluate(rows: list[dict]) -> dict:
        model.eval()
        with torch.no_grad():
            doc_emb = encode(docs, args.doc_max_len)
            scores = torch.cat([
                encode([args.query_prefix + r["query"] for r in rows[i : i + 256]], args.query_max_len) @ doc_emb.T
                for i in range(0, len(rows), 256)
            ]).cpu().numpy()
        model.train()
        card_hits, flow_hits, flow_top3, reciprocal = 0, 0, 0, 0.0
        for row, row_scores in zip(rows, scores):
            order = [card_ids[i] for i in np.argsort(-row_scores)]
            card_hits += order[0] == row["card"]
            # Cards of one decision flow collapse onto the flow, as in retrieval_baseline.py.
            ranked = list(dict.fromkeys(groups.get(c, c) for c in order))
            rank = ranked.index(groups.get(row["card"], row["card"])) + 1
            flow_hits += rank == 1
            flow_top3 += rank <= 3
            reciprocal += 1 / rank
        n = len(rows)
        return {"card_hit@1": card_hits / n, "hit@1": flow_hits / n, "hit@3": flow_top3 / n, "mrr": reciprocal / n}

    steps_per_epoch = math.ceil(len(train) / args.batch_size)
    total_steps = min(args.max_steps or 10**9, steps_per_epoch * args.epochs)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(args.warmup * total_steps), total_steps)

    history = [{"epoch": 0, "step": 0, **evaluate(dev)}]
    print(f"Before training, dev: {fmt(history[0])}", flush=True)
    best_mrr, step, start = -1.0, 0, time.perf_counter()
    rng = random.Random(args.seed)
    model.train()

    for epoch in range(1, args.epochs + 1):
        order = list(range(len(train)))
        rng.shuffle(order)
        running_loss, running_acc, seen = 0.0, 0.0, 0
        for first in range(0, len(order), args.batch_size):
            if step >= total_steps:
                break
            batch = [train[i] for i in order[first : first + args.batch_size]]
            labels = torch.tensor([index[r["card"]] for r in batch], device=device)
            queries = encode([args.query_prefix + r["query"] for r in batch], args.query_max_len)
            doc_emb = encode(docs, args.doc_max_len)  # all cards, with gradients
            logits = args.scale * queries @ doc_emb.T
            loss = F.cross_entropy(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            step += 1
            running_loss += loss.item() * len(batch)
            running_acc += (logits.argmax(dim=1) == labels).sum().item()
            seen += len(batch)
            if step % 20 == 0 or step == total_steps:
                print(f"  epoch {epoch} step {step}/{total_steps}: loss {running_loss / seen:.4f}, "
                      f"train acc {running_acc / seen:.3f} ({time.perf_counter() - start:.0f}s)", flush=True)
                running_loss, running_acc, seen = 0.0, 0.0, 0

        metrics = {"epoch": epoch, "step": step, **evaluate(dev)}
        history.append(metrics)
        print(f"Epoch {epoch}, dev: {fmt(metrics)}", flush=True)
        if metrics["mrr"] > best_mrr:
            best_mrr = metrics["mrr"]
            args.out.mkdir(parents=True, exist_ok=True)
            model.save(str(args.out))
            print(f"  saved best model to {args.out}", flush=True)
        if step >= total_steps:
            break

    log = {
        "base": args.base,
        "device": device_name,
        "torch": torch.__version__,
        "seconds": round(time.perf_counter() - start, 1),
        "args": {k: str(v) for k, v in vars(args).items()},
        "n_train": len(train),
        "n_dev": len(dev),
        "history": history,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "pusula_training_log.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(f"\nDone in {log['seconds']}s. Best dev MRR {best_mrr:.3f}. Model: {args.out}")
    return 0


def fmt(m: dict) -> str:
    return (f"hit@1 {m['hit@1']:.3f} (card-level {m['card_hit@1']:.3f}), hit@3 {m['hit@3']:.3f}, "
            f"MRR {m['mrr']:.3f}")


if __name__ == "__main__":
    sys.exit(main())
