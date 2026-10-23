"""Judge synthetic messages with a second LLM and record a keep/drop verdict for each.

A model from a different family than the generator (e.g. Apache-2.0 Qwen3 when the
messages came from gpt-oss) reads every message next to its card and answers two
questions: is it a natural, meaningful Turkish message, and does it really call for this
card? Verdicts go to data/synthetic/judgments/<judge>.jsonl and build_dataset.py drops
every message judged "ret". Messages that were already judged are skipped on a rerun.

Usage:
  python scripts/judge_queries.py --base-url https://router.huggingface.co/v1 \\
      --model Qwen/Qwen3-235B-A22B-Instruct-2507:deepinfra --hf-token --price-in 0.09 --price-out 0.55
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from cards import REPO_ROOT, describe_flow, flow_cards, load_cards, load_flows
from llm import Budget, add_endpoint_args, chat, extract_json_array, resolve_api_key, run_parallel, safe_name

RAW_DIR = REPO_ROOT / "data" / "synthetic" / "raw"
JUDGE_DIR = REPO_ROOT / "data" / "synthetic" / "judgments"

CARD_PROMPT = """Bir Türkçe acil durum asistanı için üretilmiş eğitim mesajlarını denetliyorsun. Her mesaj, aşağıdaki karta ihtiyacı olan birinin telefona yazdığı bir mesaj olmalı.

Kart: {title}
Kart özeti: {summary}
Kart adımları: {steps}
{contrast}Asistandaki diğer kartlar: {titles}

Kararını kartın kendi ölçütlerine göre ver; kartta yazanla çelişen kendi tıbbi yorumlarını kullanma.
Her mesaj için iki soruyu cevapla:
1. "dogal": Gerçek bir insanın, ne yapacağını bilmeden yazabileceği anlamlı Türkçe bir mesaj mı? Kısaltmalar, yazım hataları, eksik noktalama ve büyük harf normaldir. Anlamsız, tuhaf, bozuk ya da çelişkili ifadeler false olur. Kartın talimatlarını sıralayan, emir veren ya da kartın adımlarını zaten uyguladığını anlatan mesajlar da (ör. "Vanayı kapat, dışarı!") false olur.
2. "uygun": Bu mesajı yazan kişiye gösterilmesi gereken kart gerçekten bu kart mı? Mesaj daha çok başka bir kartı gerektiriyorsa, başka bir kartı da en az bu kadar gerektiriyorsa (ör. yanık kokusu hem yangın hem gaz kaçağı olabilir), hiçbir kartı gerektirmiyorsa ya da kartın kapsamının dışındaysa (ör. kart yetişkin içinken bebek) false olur.

Mesajlar:
{messages}

Yalnızca bir JSON dizisi döndür; her mesaj için bir nesne: [{{"no": 1, "dogal": true, "uygun": true, "neden": ""}}]. "neden" alanını yalnızca bir cevap false olduğunda kısaca doldur."""

CONTRAST = """Bu kart şu kartlarla karıştırılabilir: {others}. Uygulama bunları kullanıcıya şu soruları sorarak ayırıyor (cevap → gösterilen kart):
{flow}
Mesaj bu sorulara açıkça diğer karta götüren bir cevap veriyorsa "uygun" false olur; hangi tarafa ait olduğu belirsizse true kabul et.
"""

OOS_PROMPT = """Bir Türkçe acil durum asistanı için, asistanın CEVAPLAMAMASI gereken sorular topladık. Bu sorular acil durumla ilgisi olmayan günlük sorular olmalı.

Asistandaki kartlar: {titles}

Her soru için iki soruyu cevapla:
1. "dogal": Doğal ve anlamlı bir Türkçe soru mu?
2. "uygun": Gerçekten acil durumla ilgisiz mi, yani yukarıdaki kartlardan hiçbirinin cevabını gerektirmiyor mu?

Sorular:
{messages}

Yalnızca bir JSON dizisi döndür; her soru için bir nesne: [{{"no": 1, "dogal": true, "uygun": true, "neden": ""}}]. "neden" alanını yalnızca bir cevap false olduğunda kısaca doldur."""


def key(record: dict) -> tuple:
    return (record.get("card"), record.get("near"), record["text"])


def load_jsonl(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        with path.open(encoding="utf-8") as f:
            rows += [json.loads(line) for line in f if line.strip()]
    return rows


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_endpoint_args(parser, temperature=0.0, max_tokens=4000)
    parser.add_argument("--raw", nargs="*", type=Path, help="raw files (default: data/synthetic/raw/*.jsonl)")
    parser.add_argument("--batch", type=int, default=20, help="messages judged per request")
    args = parser.parse_args()
    api_key = resolve_api_key(parser, args)

    cards = load_cards()
    by_id = {c["id"]: c for c in cards}
    titles = "; ".join(c["title"] for c in cards)
    contrast = {}
    for flow in load_flows():
        members = sorted(flow_cards(flow))
        described = describe_flow(flow, {c["id"]: c["title"] for c in cards})
        for card_id in members:
            others = ", ".join(by_id[m]["title"] for m in members if m != card_id)
            contrast[card_id] = CONTRAST.format(others=others, flow=described)

    raw = load_jsonl(args.raw or sorted(RAW_DIR.glob("*.jsonl")))
    JUDGE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = JUDGE_DIR / f"{safe_name(args.model)}.jsonl"
    judged = {key(r) for r in load_jsonl([out_path])} if out_path.exists() else set()

    groups = defaultdict(list)
    for record in raw:
        if key(record) not in judged:
            groups[(record.get("card"), record.get("near"))].append(record)
    jobs = []
    for (card_id, near), records in groups.items():
        for i in range(0, len(records), args.batch):
            jobs.append({"card": card_id, "near": near, "records": records[i : i + args.batch]})
    if args.limit:
        jobs = jobs[: args.limit]
    print(f"{len(raw)} messages, {len(judged)} already judged, {sum(len(j['records']) for j in jobs)} to judge "
          f"in {len(jobs)} requests with {args.workers} workers -> {out_path.relative_to(REPO_ROOT)}", flush=True)

    def prompt_for(job: dict) -> str:
        messages = "\n".join(f"{n}. {r['text']}" for n, r in enumerate(job["records"], 1))
        if job["card"] is None:
            return OOS_PROMPT.format(titles=titles, messages=messages)
        card = by_id[job["card"]]
        return CARD_PROMPT.format(
            title=card["title"], summary=" ".join(card["summary"].split()), steps=" ".join(card["steps"]),
            contrast=contrast.get(card["id"], ""), titles=titles, messages=messages,
        )

    budget = Budget(args)

    def call(job: dict):
        for _ in range(2):  # one retry if the reply is not parseable
            content, usage = chat(args, api_key, prompt_for(job))
            budget.add(usage)
            items = extract_json_array(content)
            if items is not None:
                return {int(i["no"]): i for i in items if isinstance(i, dict) and str(i.get("no", "")).isdigit()}
        return {}

    verdicts = Counter()
    with out_path.open("a", encoding="utf-8") as out:
        def on_result(job: dict, answers: dict) -> None:
            for n, record in enumerate(job["records"], 1):
                answer = answers.get(n)
                if answer is None:
                    verdicts["cevapsiz"] += 1  # left unjudged; a rerun picks it up
                    continue
                natural, fits = bool(answer.get("dogal")), bool(answer.get("uygun"))
                verdict = "kabul" if natural and fits else "ret"
                verdicts[verdict] += 1
                out.write(json.dumps({
                    "card": record.get("card"),
                    "near": record.get("near"),
                    "text": record["text"],
                    "dogal": natural,
                    "uygun": fits,
                    "verdict": verdict,
                    "neden": answer.get("neden") or "",
                    "judge": args.model,
                }, ensure_ascii=False) + "\n")
            out.flush()
            print(f"  {job['card'] or 'kapsam_disi~' + str(job['near'])}: {len(answers)}/{len(job['records'])} judged",
                  flush=True)

        run_parallel(jobs, call, on_result, args.workers, budget)
    print(f"\nVerdicts: {dict(verdicts)}")
    print(budget.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
