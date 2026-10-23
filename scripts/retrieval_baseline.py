"""Offline retrieval baseline: how well do off-the-shelf models find the right card?

Embeds every card once and each test query on its own (as the app would), then
reports hit@1, hit@3 and MRR per model and per query type. Out-of-scope queries
are scored by how well the top similarity separates them from in-scope ones
(AUROC), which tells us whether a "no matching card" threshold is workable.

Decision flows are searched alongside cards. A hit on a flow, or on any card a
flow leads to, counts as reaching that flow: the app then asks the flow's
question, and an honest answer leads to the expected card.

Usage:
  python scripts/retrieval_baseline.py                  # all models; downloads on first run
  python scripts/retrieval_baseline.py --offline        # never touch the network
  python scripts/retrieval_baseline.py --models bm25,e5-small
  python scripts/retrieval_baseline.py --no-flows       # cards only, for comparison
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import date

import numpy as np

from cards import (
    DEFAULT_TEXT_FIELDS,
    REPO_ROOT,
    card_text,
    flow_groups,
    flow_text,
    load_cards,
    load_flows,
    load_queries,
    tokenize,
)

RESULTS_DIR = REPO_ROOT / "results"

# Encoders small enough to consider for a phone, plus bge-m3 as an upper bound.
EMBEDDING_MODELS = {
    "static-mrl-multilingual": {"id": "sentence-transformers/static-similarity-mrl-multilingual-v1"},
    "minilm-l12-multilingual": {"id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"},
    "e5-small": {"id": "intfloat/multilingual-e5-small", "query_prefix": "query: ", "doc_prefix": "passage: "},
    "bert-turkish-nli-stsb": {"id": "emrecan/bert-base-turkish-cased-mean-nli-stsb-tr"},
    "modernbert-tr-embed": {"id": "ytu-ce-cosmos/modernbert-tr-embed", "query_prompt": "query"},
    "bge-m3": {"id": "BAAI/bge-m3"},
}
LEXICAL_MODELS = {"bm25": None, "bm25-f5": 5}

IN_SCOPE_TYPES = ("resmi", "gunluk", "diakritiksiz", "yazim_hatasi", "panik", "dolayli", "ses")
OUT_OF_SCOPE = "kapsam_disi"


class Bm25Retriever:
    def __init__(self, docs: list[str], prefix_len: int | None):
        from rank_bm25 import BM25Okapi

        self.prefix_len = prefix_len
        self.bm25 = BM25Okapi([tokenize(d, prefix_len) for d in docs])
        self.params = None

    def scores(self, query: str) -> np.ndarray:
        return np.asarray(self.bm25.get_scores(tokenize(query, self.prefix_len)))


class EmbeddingRetriever:
    def __init__(self, spec: dict, docs: list[str]):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(spec["id"], device="cpu")
        self.query_prefix = spec.get("query_prefix", "")
        self.query_kwargs = {}
        prompt = spec.get("query_prompt")
        if prompt:
            if prompt not in (self.model.prompts or {}):
                raise ValueError(f"model has no '{prompt}' prompt; available: {sorted(self.model.prompts or {})}")
            self.query_kwargs["prompt_name"] = prompt
        doc_prefix = spec.get("doc_prefix", "")
        self.doc_emb = self._encode([doc_prefix + d for d in docs])
        self.params = sum(p.numel() for p in self.model.parameters())

    def _encode(self, texts: list[str], **kwargs) -> np.ndarray:
        return self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False, **kwargs)

    def scores(self, query: str) -> np.ndarray:
        return self.doc_emb @ self._encode([self.query_prefix + query], **self.query_kwargs)[0]


def run_queries(
    retriever, queries: list[dict], target_ids: list[str], groups: dict[str, str], flow_ids: set[str]
) -> tuple[list[dict], list[float]]:
    retriever.scores(queries[0]["text"])  # warm-up so the first timing is not a cold start
    rows, latencies = [], []
    for query in queries:
        start = time.perf_counter()
        scores = retriever.scores(query["text"])
        latencies.append(time.perf_counter() - start)
        order = np.argsort(-scores)
        raw = [target_ids[i] for i in order]
        # Cards inside a flow collapse onto the flow, so the flow shows up once in the ranking.
        ranked = list(dict.fromkeys(groups.get(t, t) for t in raw))
        expected = {groups.get(e, e) for e in query["expected"]}
        rank = next((r for r, target in enumerate(ranked[:10], 1) if target in expected), None)
        first_card = next(t for t in raw if t not in flow_ids)
        rows.append({
            "id": query["id"],
            "text": query["text"],
            "type": query["type"],
            "expected": query["expected"],
            "rank": rank,
            "top3": ranked[:3],
            "first_card": first_card,
            "asks_question": ranked[0] in flow_ids,
            # Ranking cards alone would have shown a wrong card, but the flow's question leads to the right one.
            "saved_by_flow": rank == 1 and first_card not in query["expected"],
            "top_score": float(scores[order[0]]),
        })
    return rows, latencies


def rank_stats(rows: list[dict]) -> dict:
    n = len(rows)
    if not n:
        return {"n": 0, "hit@1": None, "hit@3": None, "mrr": None}
    return {
        "n": n,
        "hit@1": sum(r["rank"] == 1 for r in rows) / n,
        "hit@3": sum(r["rank"] is not None and r["rank"] <= 3 for r in rows) / n,
        "mrr": sum(1 / r["rank"] for r in rows if r["rank"]) / n,
    }


def auroc(positives: list[float], negatives: list[float]) -> float | None:
    """Probability that an in-scope query scores higher than an out-of-scope one."""
    if not positives or not negatives:
        return None
    wins = sum(1.0 if p > q else 0.5 if p == q else 0.0 for p in positives for q in negatives)
    return wins / (len(positives) * len(negatives))


def summarize(rows: list[dict]) -> dict:
    in_scope = [r for r in rows if r["type"] != OUT_OF_SCOPE]
    out_scope = [r for r in rows if r["type"] == OUT_OF_SCOPE]
    return {
        "overall": rank_stats(in_scope),
        "by_type": {t: rank_stats([r for r in in_scope if r["type"] == t]) for t in IN_SCOPE_TYPES},
        "oos_auroc": auroc([r["top_score"] for r in in_scope], [r["top_score"] for r in out_scope]),
        "asks_question_rate": sum(r["asks_question"] for r in in_scope) / len(in_scope) if in_scope else None,
        "saved_by_flow": sum(r["saved_by_flow"] for r in in_scope),
        "misses": [r for r in in_scope if r["rank"] != 1],
    }


def pct(value: float | None) -> str:
    return "–" if value is None else f"{100 * value:.0f}"


def write_markdown(report: dict, path) -> None:
    models = {k: v for k, v in report["models"].items() if "error" not in v}
    lines = [
        "# Çevrimdışı arama ölçümü",
        "",
        f"- Tarih: {report['date']}",
        f"- Kart sayısı: {report['n_cards']} (hepsi taslak), soru sayısı: {report['n_queries']} "
        f"({report['n_out_of_scope']} kapsam dışı)",
        f"- Karar akışları: {report['n_flows']}" if report["use_flows"] else "- Karar akışları: kullanılmadı (yalnızca kartlar)",
        f"- Kart metni: {', '.join(report['fields'])}",
        "- Donanım: PC işlemcisi (CPU), sorgular tek tek kodlandı. Süreler telefonda farklı olur, yalnızca modelleri kıyaslamak içindir.",
        "",
        "## Genel sonuç",
        "",
        "| Model | Parametre (M) | hit@1 | hit@3 | MRR | Kapsam dışı AUROC | Soru sorulan (%) | Akışla düzelen | Sorgu süresi (ms) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    ordered = sorted(models.items(), key=lambda kv: -kv[1]["overall"]["mrr"])
    for name, m in ordered:
        params = "–" if m["params_m"] is None else f"{m['params_m']:.0f}"
        auc = "–" if m["oos_auroc"] is None else f"{m['oos_auroc']:.2f}"
        lines.append(
            f"| {name} | {params} | {pct(m['overall']['hit@1'])} | {pct(m['overall']['hit@3'])} | "
            f"{pct(m['overall']['mrr'])} | {auc} | {pct(m['asks_question_rate'])} | {m['saved_by_flow']} | "
            f"{m['median_query_ms']:.1f} |"
        )
    lines += [
        "",
        "hit@1: doğru kart ya da doğru karta götüren akış ilk sırada (%). hit@3: ilk üçte (%). MRR: ortalama ters sıra (%). "
        "AUROC: kapsam dışı soruları en yüksek benzerlik skoruna bakarak ayırabilme (0,5 rastgele, 1,0 kusursuz). "
        "Soru sorulan: kapsam içi soruların kaçında kullanıcıya akış sorusu soruluyor. "
        "Akışla düzelen: yalnızca kartlara bakılsaydı yanlış kart çıkacakken akışın sorusuyla doğru karta ulaşılan soru sayısı.",
        "",
        "## Soru tipine göre hit@1 (%)",
        "",
        "| Model | " + " | ".join(IN_SCOPE_TYPES) + " |",
        "|---|" + "---|" * len(IN_SCOPE_TYPES),
    ]
    for name, m in ordered:
        lines.append(f"| {name} | " + " | ".join(pct(m["by_type"][t]["hit@1"]) for t in IN_SCOPE_TYPES) + " |")

    if ordered:
        best_name, best = ordered[0]
        lines += ["", f"## En iyi modelin ({best_name}) ilk sırada bulamadığı sorular", ""]
        lines += ["| Soru | Tip | Beklenen | Bulunan ilk kart ya da akış |", "|---|---|---|---|"]
        for miss in best["misses"]:
            lines.append(f"| {miss['text']} | {miss['type']} | {', '.join(miss['expected'])} | {miss['top3'][0]} |")

    failed = {k: v["error"] for k, v in report["models"].items() if "error" in v}
    if failed:
        lines += ["", "## Çalışmayan modeller", ""]
        lines += [f"- {name}: {error}" for name, error in failed.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", help="comma-separated subset of: " + ", ".join([*LEXICAL_MODELS, *EMBEDDING_MODELS]))
    parser.add_argument("--fields", default=",".join(DEFAULT_TEXT_FIELDS), help="card fields used as the passage")
    parser.add_argument("--offline", action="store_true", help="use only models already in the local cache")
    parser.add_argument("--out", default="baseline", help="output file name (without extension) under results/")
    parser.add_argument("--no-flows", action="store_true", help="search cards only, ignoring decision flows")
    args = parser.parse_args()

    if args.offline:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    names = args.models.split(",") if args.models else [*LEXICAL_MODELS, *EMBEDDING_MODELS]
    unknown = [n for n in names if n not in LEXICAL_MODELS and n not in EMBEDDING_MODELS]
    if unknown:
        parser.error(f"unknown model(s): {', '.join(unknown)}")
    fields = tuple(f.strip() for f in args.fields.split(",") if f.strip())

    cards = load_cards()
    flows = [] if args.no_flows else load_flows()
    queries = load_queries()
    target_ids = [c["id"] for c in cards] + [f["id"] for f in flows]
    docs = [card_text(c, fields) for c in cards] + [flow_text(f) for f in flows]
    groups = flow_groups(flows)
    flow_ids = {f["id"] for f in flows}

    report = {
        "date": date.today().isoformat(),
        "fields": list(fields),
        "n_cards": len(cards),
        "n_flows": len(flows),
        "use_flows": not args.no_flows,
        "n_queries": len(queries),
        "n_out_of_scope": sum(q["type"] == OUT_OF_SCOPE for q in queries),
        "offline": args.offline,
        "models": {},
    }

    for name in names:
        print(f"[{name}] loading...", flush=True)
        start = time.perf_counter()
        try:
            if name in LEXICAL_MODELS:
                retriever = Bm25Retriever(docs, LEXICAL_MODELS[name])
                model_id = None
            else:
                retriever = EmbeddingRetriever(EMBEDDING_MODELS[name], docs)
                model_id = EMBEDDING_MODELS[name]["id"]
            load_s = time.perf_counter() - start
            rows, latencies = run_queries(retriever, queries, target_ids, groups, flow_ids)
        except Exception as e:  # keep going so one broken model does not hide the others
            print(f"[{name}] FAILED: {e}", flush=True)
            report["models"][name] = {"error": f"{type(e).__name__}: {e}"}
            continue

        summary = summarize(rows)
        report["models"][name] = {
            "id": model_id,
            "params_m": None if retriever.params is None else retriever.params / 1e6,
            "load_s": round(load_s, 2),
            "median_query_ms": statistics.median(latencies) * 1000,
            **summary,
            "rows": rows,
        }
        o = summary["overall"]
        auc = "-" if summary["oos_auroc"] is None else f"{summary['oos_auroc']:.2f}"
        print(f"[{name}] hit@1={pct(o['hit@1'])} hit@3={pct(o['hit@3'])} mrr={pct(o['mrr'])} oos_auroc={auc}", flush=True)

    RESULTS_DIR.mkdir(exist_ok=True)
    json_path = RESULTS_DIR / f"{args.out}.json"
    md_path = RESULTS_DIR / f"{args.out}.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(report, md_path)
    print(f"\nWrote {json_path.relative_to(REPO_ROOT)} and {md_path.relative_to(REPO_ROOT)}")
    return 0 if all("error" not in m for m in report["models"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
