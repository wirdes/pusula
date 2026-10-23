"""Generate synthetic Turkish user messages for every card with a teacher LLM.

Talks to any OpenAI-compatible chat endpoint (llama.cpp server, Ollama, LM Studio,
Hugging Face Inference Providers, ...). Only use a teacher whose licence allows
training other models on its outputs, such as Apache-2.0 Qwen3 or gpt-oss.

Each (card, style, round) request is appended to data/synthetic/raw/<model>.jsonl as
soon as it returns, so an interrupted run can simply be started again.

Usage:
  python scripts/generate_queries.py --dry-run
  python scripts/generate_queries.py --base-url http://127.0.0.1:8080/v1 --model gpt-oss-20b --limit 5
  python scripts/generate_queries.py --base-url https://router.huggingface.co/v1 \\
      --model openai/gpt-oss-120b:deepinfra --hf-token --price-in 0.04 --price-out 0.17 --limit 10
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time

from cards import REPO_ROOT, describe_flow, flow_cards, load_cards, load_flows
from llm import Budget, add_endpoint_args, chat, extract_json_array, resolve_api_key, run_parallel, safe_name

RAW_DIR = REPO_ROOT / "data" / "synthetic" / "raw"

# Diacritic-free and typo variants are added later by build_dataset.py, where they are
# controllable; the LLM is asked for the styles that need real language variety.
STYLES = {
    "resmi": "Düzgün, eksiksiz ve kurallı Türkçeyle yazılmış bir soru.",
    "gunluk": "Günlük konuşma dili; 'napıcam', 'geliyo', 'bi' gibi kısaltmalar ve özensiz noktalama olabilir.",
    "panik": "Panik halinde yazılmış çok kısa (1–5 kelime) ama anlamlı mesajlar; ne olduğunu ve kimin başına geldiğini söylesin; bazıları tamamen büyük harfle.",
    "dolayli": "Konunun adını ya da tıbbi terimleri hiç kullanmadan yalnızca görüleni, yaşananı anlatan mesaj.",
    "ses": "Telefona sesle söylenmiş ve yazıya çevrilmiş gibi; noktalama yok, küçük harf, 'şey', 'yani' gibi dolgu sözcükler olabilir.",
}
PERSONAS = [
    "kendisi için soran biri (durum kişinin kendi başına mesaj yazamayacağı bir durumsa, yanındaki biri için)",
    "annesi, babası, eşi ya da çocuğu için soran biri",
    "yanındaki tanımadığı biri için soran biri",
    "yaşlı ve teknolojiyle arası iyi olmayan biri",
    "genç biri",
    "sağlık ve afet konusunda hiçbir bilgisi olmayan biri",
]

CARD_PROMPT = """Pusula adında, internetsiz çalışan bir Türkçe acil durum asistanı için eğitim verisi hazırlıyoruz.
Aşağıdaki bilgi kartına ihtiyacı olan birinin telefona yazabileceği {n} farklı mesaj yaz.

Kart başlığı: {title}
Kart özeti: {summary}
{contrast}{others}
Yazım tarzı: {style}
Mesajı yazan kişi: {persona}

Kurallar:
- Her mesaj gerçek bir insanın yazacağı gibi doğal ve anlamlı olsun; anlamsız kelime dizileri ya da emir cümleleri yazma.
- Mesajı yazan kişi ne yapması gerektiğini bilmiyor. Mesajlar kartın önerdiği adımları sıralamasın ya da uygulamış gibi anlatmasın; yalnızca durumu anlatsın ya da ne yapacağını sorsun.
- Mesajlar birbirinden farklı olsun; farklı durumlar, yerler, kişiler ve kelimeler kullan. Aynı cümle kalıbını tekrar etme.
- Kart özetindeki belirtileri liste halinde tekrar etme. Her mesaj durumdan yalnızca bir iki ayrıntı versin ve mesajlar farklı ayrıntılar seçsin.
- Kart başlığını ve yukarıdaki soruları olduğu gibi kopyalama. Ama insanların bu durumda doğal olarak kullandığı kelimeleri (örneğin konunun gündelik adını) kullanabilirsin.
- Kartın kapsamının dışına çıkma; örneğin başlık yetişkin diyorsa bebek ya da küçük çocuk yazma.
- Mesajlarda kimseye hitap etme; "Anne," ya da "Doktor," gibi başlama.
- Mesajların cevabı bu kart olmalı, başka bir kart değil.
- Yalnızca Türkçe yaz.
- Yalnızca bir JSON dizisi döndür, örneğin: ["birinci mesaj", "ikinci mesaj"]"""

CONTRAST = """Bu kart şu kartlarla karıştırılabilir: {others}.
Uygulama bu kartları kullanıcıya şu soruları sorarak ayırıyor (cevap → gösterilen kart):
{flow}
Mesajlar bu sorulara bu karta götüren cevabı içersin, ama soruların ya da cevapların kendisini veya kelimelerini kopyalamasın; cevap, yazan kişinin kendi gözlemi olarak doğal bir şekilde geçsin.
"""

OTHERS = """Şu konuların ayrı kartları var; mesajlar bu konulara kaymasın: {others}.
"""

OOS_PROMPT = """Pusula adında bir Türkçe acil durum asistanı için, asistanın cevaplamaması gereken soruları topluyoruz.
Aşağıdaki acil durum konusuyla kelime olarak benzeşen ama acil durumla HİÇBİR ilgisi olmayan {n} farklı günlük soru yaz.

Acil durum konusu: {title}

Örneğin "ateş yakma" için "mangal için hangi kömür daha iyi", "arı sokması" için "arı balı neye iyi gelir" gibi.
Kurallar:
- Sorular doğal, günlük ve birbirinden farklı olsun.
- Hiçbiri bir tehlike, yaralanma ya da acil durum anlatmasın.
- Yalnızca Türkçe yaz.
- Yalnızca bir JSON dizisi döndür."""


def card_prompt(
    card: dict, style: str, persona: str, n: int, siblings: list[dict], related: list[dict], flow: str
) -> str:
    contrast = CONTRAST.format(others=", ".join(s["title"] for s in siblings), flow=flow) if siblings else ""
    sibling_ids = {s["id"] for s in siblings}
    neighbours = [r for r in related if r["id"] not in sibling_ids]
    others = OTHERS.format(others=", ".join(r["title"] for r in neighbours)) if neighbours else ""
    return CARD_PROMPT.format(
        n=n,
        title=card["title"],
        summary=" ".join(card["summary"].split()),
        contrast=contrast,
        others=others,
        style=STYLES[style],
        persona=persona,
    )


def parse_messages(content: str) -> list[str]:
    """Pull a list of messages out of a model reply, tolerating chatter around the JSON."""
    items = extract_json_array(content)
    if items is not None:
        return [str(i).strip() for i in items if str(i).strip()]
    lines = []
    for line in re.sub(r"<think>.*?</think>", "", content, flags=re.S).splitlines():
        line = re.sub(r'^\s*(?:[-*•]|\d+[.)])\s*', "", line).strip().strip('",').strip()
        if line and not line.startswith(("[", "]", "```")):
            lines.append(line)
    return lines


def plan_requests(
    cards: list[dict], all_cards: list[dict], flows: list[dict], styles: list[str], rounds: int, oos_per_card: int
) -> list[dict]:
    by_id = {c["id"]: c for c in all_cards}  # siblings may sit outside the selected cards
    siblings, described = {}, {}
    titles = {c["id"]: c["title"] for c in all_cards}
    for flow in flows:
        members = sorted(flow_cards(flow))
        for card_id in members:
            siblings[card_id] = [by_id[m] for m in members if m != card_id]
            described[card_id] = describe_flow(flow, titles)
    jobs = []
    for card in cards:
        for style in styles:
            for r in range(rounds):
                persona = PERSONAS[(len(jobs) + r) % len(PERSONAS)]
                jobs.append({"kind": "card", "card": card, "style": style, "round": r, "persona": persona,
                             "siblings": siblings.get(card["id"], []),
                             "flow": described.get(card["id"], ""),
                             "related": [by_id[r_id] for r_id in card.get("related") or [] if r_id in by_id]})
        if oos_per_card:
            jobs.append({"kind": "oos", "card": card, "style": "kapsam_disi", "round": 0, "persona": None,
                         "siblings": [], "flow": "", "related": []})
    return jobs


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_endpoint_args(parser, temperature=0.9, max_tokens=4000)
    parser.add_argument("--per-request", type=int, default=10, help="messages asked for per request")
    parser.add_argument("--rounds", type=int, default=2, help="requests per card and style (different personas)")
    parser.add_argument("--styles", default=",".join(STYLES), help="comma-separated subset of styles")
    parser.add_argument("--cards", help="comma-separated card ids (default: all)")
    parser.add_argument("--oos-per-card", type=int, default=5, help="unrelated look-alike questions per card; 0 to skip")
    parser.add_argument("--dry-run", action="store_true", help="print the first prompts and exit without calling a model")
    args = parser.parse_args()

    styles = [s.strip() for s in args.styles.split(",") if s.strip()]
    unknown = [s for s in styles if s not in STYLES]
    if unknown:
        parser.error(f"unknown style(s): {', '.join(unknown)}")
    all_cards = load_cards()
    cards = all_cards
    if args.cards:
        wanted = set(args.cards.split(","))
        missing = wanted - {c["id"] for c in all_cards}
        if missing:
            parser.error(f"unknown card(s): {', '.join(sorted(missing))}")
        cards = [c for c in all_cards if c["id"] in wanted]
    jobs = plan_requests(cards, all_cards, load_flows(), styles, args.rounds, args.oos_per_card)

    def prompt_for(job: dict) -> str:
        if job["kind"] == "oos":
            return OOS_PROMPT.format(n=args.oos_per_card, title=job["card"]["title"])
        return card_prompt(
            job["card"], job["style"], job["persona"], args.per_request, job["siblings"], job["related"], job["flow"]
        )

    if args.dry_run:
        print(f"{len(jobs)} requests planned. First prompts:\n")
        shown = [jobs[0]] + [j for j in jobs if j["siblings"]][:1] + [j for j in jobs if j["kind"] == "oos"][:1]
        for job in shown:
            print(f"--- {job['card']['id']} / {job['style']} ---\n{prompt_for(job)}\n")
        return 0

    api_key = resolve_api_key(parser, args)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{safe_name(args.model)}.jsonl"
    done = set()
    if out_path.exists():
        with out_path.open(encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                done.add((rec.get("card") or rec.get("near"), rec["style"], rec["round"]))

    remaining = [j for j in jobs if (j["card"]["id"], j["style"], j["round"]) not in done]
    todo = remaining[: args.limit] if args.limit else remaining
    print(f"{len(jobs)} requests planned, {len(jobs) - len(remaining)} already done, running {len(todo)} "
          f"with {args.workers} workers -> {out_path.relative_to(REPO_ROOT)}", flush=True)

    budget = Budget(args)
    counts = {"requests": 0, "messages": 0}

    def call(job: dict):
        start = time.perf_counter()
        content, usage = chat(args, api_key, prompt_for(job))
        budget.add(usage)
        return parse_messages(content), usage, time.perf_counter() - start

    with out_path.open("a", encoding="utf-8") as out:
        def on_result(job: dict, result) -> None:
            messages, usage, elapsed = result
            for text in messages:
                out.write(json.dumps({
                    "card": job["card"]["id"] if job["kind"] == "card" else None,
                    "near": job["card"]["id"] if job["kind"] == "oos" else None,
                    "style": job["style"],
                    "persona": job["persona"],
                    "round": job["round"],
                    "model": args.model,
                    "text": text,
                }, ensure_ascii=False) + "\n")
            out.flush()
            counts["requests"] += 1
            counts["messages"] += len(messages)
            print(f"[{counts['requests']}/{len(todo)}] {job['card']['id']} / {job['style']} / round {job['round']}: "
                  f"{len(messages)} messages, {usage.get('completion_tokens', '?')} output tokens ({elapsed:.0f}s)",
                  flush=True)

        run_parallel(todo, call, on_result, args.workers, budget)
    print(f"\nWrote {counts['messages']} messages to {out_path.relative_to(REPO_ROOT)}")
    print(budget.summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
