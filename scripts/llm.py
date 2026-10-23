"""Shared helpers for talking to an OpenAI-compatible chat endpoint.

Used by generate_queries.py and judge_queries.py: request with retries, JSON
extraction from replies, a spend estimate that stops a run at a budget, and a
small thread pool so hundreds of requests do not run one at a time.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable


def add_endpoint_args(parser: argparse.ArgumentParser, temperature: float, max_tokens: int) -> None:
    parser.add_argument("--base-url", help="OpenAI-compatible endpoint, e.g. http://127.0.0.1:8080/v1")
    parser.add_argument("--model", help="model name as the endpoint knows it")
    parser.add_argument("--api-key-env", help="environment variable holding the API key, if the endpoint needs one")
    parser.add_argument("--hf-token", action="store_true", help="use the token saved by `hf auth login` (Hugging Face Inference Providers)")
    parser.add_argument("--temperature", type=float, default=temperature)
    parser.add_argument("--max-tokens", type=int, default=max_tokens, help="reasoning models spend part of this on thinking")
    parser.add_argument("--reasoning-effort", choices=["low", "medium", "high"], help="for reasoning models such as gpt-oss")
    parser.add_argument("--workers", type=int, default=8, help="requests in flight at once")
    parser.add_argument("--limit", type=int, help="stop after this many requests (for a pilot run)")
    parser.add_argument("--max-dollars", type=float, default=1.0, help="stop once the estimated spend reaches this")
    parser.add_argument("--price-in", type=float, default=0.15, help="$ per 1M input tokens, for the spend estimate")
    parser.add_argument("--price-out", type=float, default=0.75, help="$ per 1M output tokens, for the spend estimate")


def resolve_api_key(parser: argparse.ArgumentParser, args: argparse.Namespace) -> str | None:
    if not (args.base_url and args.model):
        parser.error("--base-url and --model are required")
    if args.hf_token:
        from huggingface_hub import get_token

        token = get_token()
        if not token:
            parser.error("no saved Hugging Face token; run `hf auth login` first")
        return token
    if args.api_key_env:
        key = os.environ.get(args.api_key_env)
        if not key:
            parser.error(f"environment variable {args.api_key_env} is not set")
        return key
    return None


def safe_name(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model)


def chat(args: argparse.Namespace, api_key: str | None, prompt: str) -> tuple[str, dict]:
    """Return the reply text and the token usage the endpoint reports."""
    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": args.temperature,
        "top_p": 0.95,
        "max_tokens": args.max_tokens,
    }
    if args.reasoning_effort:
        payload["reasoning_effort"] = args.reasoning_effort
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        f"{args.base_url.rstrip('/')}/chat/completions", data=json.dumps(payload).encode("utf-8"), headers=headers
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                reply = json.loads(response.read().decode("utf-8"))
            return reply["choices"][0]["message"].get("content") or "", reply.get("usage") or {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:500]
            # Auth, billing and bad-request errors will not fix themselves; only retry rate limits and server errors.
            if e.code != 429 and e.code < 500:
                raise RuntimeError(f"HTTP {e.code}: {detail}") from e
            error = f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError) as e:
            error = str(e)
        if attempt == 3:
            raise RuntimeError(f"giving up after 4 attempts: {error}")
        wait = 2 ** attempt * 5
        print(f"    request failed ({error}); retrying in {wait}s", flush=True)
        time.sleep(wait)
    return "", {}


def extract_json_array(content: str) -> list | None:
    """The first JSON array in a reply, tolerating chatter, code fences and <think> blocks."""
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
    start, end = content.find("["), content.rfind("]")
    if start == -1 or end <= start:
        return None
    try:
        items = json.loads(content[start : end + 1])
    except json.JSONDecodeError:
        return None
    return items if isinstance(items, list) else None


class Budget:
    def __init__(self, args: argparse.Namespace):
        self.price_in, self.price_out, self.limit = args.price_in, args.price_out, args.max_dollars
        self.tokens_in = self.tokens_out = 0
        self._lock = threading.Lock()

    def add(self, usage: dict) -> None:
        with self._lock:
            self.tokens_in += usage.get("prompt_tokens", 0)
            self.tokens_out += usage.get("completion_tokens", 0)

    def spent(self) -> float:
        return self.tokens_in / 1e6 * self.price_in + self.tokens_out / 1e6 * self.price_out

    def exceeded(self) -> bool:
        return self.spent() >= self.limit

    def summary(self) -> str:
        return (f"Tokens: {self.tokens_in} in, {self.tokens_out} out; estimated spend ${self.spent():.4f} "
                f"(at ${self.price_in}/M in, ${self.price_out}/M out)")


def run_parallel(jobs: Iterable, call: Callable, on_result: Callable, workers: int, budget: Budget) -> None:
    """Run call(job) for every job on a thread pool and hand results to on_result in the main thread.

    Stops submitting work once the budget is reached; a fatal request error cancels the rest.
    """
    def guarded(job):
        if budget.exceeded():
            return job, None
        return job, call(job)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(guarded, job) for job in jobs]
        try:
            for future in as_completed(futures):
                job, result = future.result()
                if result is not None:
                    on_result(job, result)
        except RuntimeError:
            for f in futures:
                f.cancel()
            raise
    if budget.exceeded():
        print(f"\nStopped at the budget: estimated spend ${budget.spent():.3f} >= --max-dollars {budget.limit}")
