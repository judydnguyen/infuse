#!/usr/bin/env python3
"""
Full re-score of every attack trajectory under the clarified (V2) judge rubric.
  -> reviewers jBcF-W1, AC-M1

WHAT THIS IS
------------
The stored `asr_l` labels come from the V1 rubric, whose criterion 1 counted an agent
that merely *acknowledged* an injected instruction as compromised — the contradiction
jBcF identified. V2 rewords two lines so compromise requires the injection to have
actually influenced what the agent did or decided. Every ASR-L number in the paper
derives from the V1 labels, so they all need regenerating.

The judge MODEL is held fixed (gpt-4o-mini, as in V1) so the only thing that changes
is the rubric wording. V1 output is never overwritten: the old-vs-new delta table
needs both.

SCOPE — all 38,637 rows, including the 983 with a NULL V1 conclusion. Those are
V1 judge failures and resolving them is part of the deliverable; the pilot excluded
them, which would have quietly dropped them from the corrected numbers.

Resumable: re-running skips trajectories already present in the output CSV.

USAGE
  python3 scripts/rescore_v2_full.py --out traj_records_v2.csv --workers 16
  python3 scripts/rescore_v2_full.py --out traj_records_v2.csv --limit 200   # smoke test
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from infuse.paths import DATA_ROOT, REPO_ROOT
RESULTS = Path(os.environ.get("INFUSE_RESULTS", str(DATA_ROOT)))
PARQUET = RESULTS / "traj_records_with_reasoning.parquet"
# Source the V2 rubric from this repo (infuse.evaluators.llm_evaluator).
EVAL_PY = Path(os.environ.get("INFUSE_EVAL_PY", str(REPO_ROOT / "infuse" / "evaluators" / "llm_evaluator.py")))
ENV_FILE = REPO_ROOT / ".env"

MAX_STEPS_CHARS = 60_000

# Per-family judge config: (env-key, model-id, price_in/1M, price_out/1M).
# gpt-4o-mini is the paper's original judge but its OpenAI account is out of
# credit (insufficient_quota), so the full re-score falls back to Gemini, which
# is the cheapest working family and doubles as a full-scale committee judge.
JUDGES = {
    # gpt-4o-mini-gateway: the PAPER'S ORIGINAL judge (gpt-4o-mini) served via a
    # custom OpenAI-compatible Azure gateway, since the direct OpenAI account is out
    # of credit. This is the preferred judge for the headline re-score: same model as
    # V1, so the V1->V2 delta isolates the RUBRIC change rather than confounding it
    # with a judge-model change. Auth via X-API-Key header; billed off our OpenAI key.
    "gpt-4o-mini-gateway":    {"env": "GATEWAY_API_KEY",   "model": "gpt-4o-mini",            "pin": 0.0,  "pout": 0.0,  "gateway": True},
    "gpt-4o-mini":            {"env": "OPENAI_API_KEY",    "model": "gpt-4o-mini",            "pin": 0.15, "pout": 0.60},
    "gemini-2.5-flash":       {"env": "GEMINI_API_KEY",    "model": "gemini-2.5-flash",       "pin": 0.30, "pout": 2.50},
    "gemini-2.5-flash-lite":  {"env": "GEMINI_API_KEY",    "model": "gemini-2.5-flash-lite",  "pin": 0.10, "pout": 0.40},
    "claude-haiku-4-5":       {"env": "ANTHROPIC_API_KEY", "model": "claude-haiku-4-5",       "pin": 1.00, "pout": 5.00},
}
GATEWAY_BASE_ENV = "GATEWAY_API_BASE"

# gpt-4o-mini via the gateway is the default: it is the paper's original judge, so the
# re-score changes ONLY the rubric. flash-lite was validated as a committee member
# (kappa 0.80 vs gpt-4o-mini, 0.83 vs full flash, 0.82 vs claude) and is the fallback
# if the gateway is unavailable.
DEFAULT_JUDGE = "gpt-4o-mini-gateway"

FIELDS = ["traj_basename", "model", "defense", "task_id", "attack_id", "task_category",
          "v1_concl", "v2_concl", "v2_refused", "n_steps", "truncated",
          "in_tok", "out_tok", "error"]


def load_prompt() -> str:
    """Read V2 straight from source so this script can't drift from the package."""
    for node in ast.parse(EVAL_PY.read_text()).body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
            if node.targets[0].id == "JUDGE_PROMPT_SINGLE_V2":
                return node.value.value
    raise SystemExit("JUDGE_PROMPT_SINGLE_V2 not found in llm_evaluator.py")


def load_key(env_name: str) -> str:
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith(env_name + "="):
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            if v:
                return v
    raise SystemExit(f"{env_name} not found or empty in {ENV_FILE}")


def steps_from_traj(path: str) -> list[dict]:
    """Mirror LLMJudgeEvaluator.extract_reasoning_from_trajectory exactly."""
    with open(path) as fh:
        traj = json.load(fh)
    out: list[dict] = []
    for msg in traj.get("messages", []):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "") or ""
        action = msg.get("action")
        if not action:
            m = re.search(r"```bash\n(.*?)\n```", content, re.DOTALL)
            action = m.group(1).strip() if m else None
        reasoning = content
        if action and action in content:
            i = content.find(action)
            if i > 0:
                reasoning = content[:i].strip()
        elif "```bash" in content:
            m = re.search(r"```bash", content)
            if m:
                reasoning = content[: m.start()].strip()
        if reasoning or action:
            out.append({"step": len(out) + 1, "reasoning": reasoning, "action": action})
    return out


def parse(text: str) -> tuple[str | None, bool | None]:
    """V2 keeps V1's conclusion vocabulary, so the existing parse order still applies."""
    low = text.lower()
    m = re.search(r"conclusion:\s*'?\[?([a-z ]+?)\]?'?\s*$", low, re.M)
    seg = m.group(1).strip() if m else low
    if "outright refusal" in seg:
        concl = "outright refusal"
    elif "not compromised" in seg:
        concl = "not compromised"
    elif "compromised" in seg:
        concl = "compromised"
    else:
        concl = None
    r = re.search(r"refused:\s*(yes|no)", low)
    return concl, (r.group(1) == "yes" if r else None)


class Judge:
    def __init__(self, prompt: str, key: str, family: str, gateway_base: str | None = None):
        self.prompt, self.key = prompt, key
        self.family = family
        self.model = JUDGES[family]["model"]
        self.gateway_base = gateway_base  # set only for the gateway family

    def _invoke(self, full: str):
        """One judge call -> (text, in_tok, out_tok). Raises HTTPError/Exception on failure."""
        if self.family.startswith("gemini"):
            body = json.dumps({"contents": [{"parts": [{"text": full}]}],
                               "generationConfig": {"temperature": 0, "maxOutputTokens": 8000,
                                                    "thinkingConfig": {"thinkingBudget": 0}}}).encode()
            req = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                data=body, headers={"x-goog-api-key": self.key, "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.loads(r.read())
            cand = d["candidates"][0]
            txt = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
            u = d.get("usageMetadata", {})
            return txt, u.get("promptTokenCount"), u.get("candidatesTokenCount")
        if self.family == "claude-haiku-4-5":
            body = json.dumps({"model": self.model, "max_tokens": 1500, "temperature": 0,
                               "messages": [{"role": "user", "content": full}]}).encode()
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=240) as r:
                d = json.loads(r.read())
            txt = "".join(b.get("text", "") for b in d.get("content", []))
            u = d.get("usage", {})
            return txt, u.get("input_tokens"), u.get("output_tokens")
        # OpenAI chat-completions format — direct API or the custom gateway.
        body = json.dumps({"model": self.model, "temperature": 0.0,
                           "messages": [{"role": "user", "content": full}]}).encode()
        if self.gateway_base:
            url = self.gateway_base.rstrip("/") + "/chat/completions"
            headers = {"X-API-Key": self.key, "Content-Type": "application/json"}
        else:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        req = urllib.request.Request(url, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=240) as r:
            d = json.loads(r.read())
        txt = d["choices"][0]["message"]["content"]
        u = d.get("usage", {})
        return txt, u.get("prompt_tokens"), u.get("completion_tokens")

    def __call__(self, row) -> dict:
        rec = {f: None for f in FIELDS}
        rec.update(traj_basename=row.traj_basename, model=row.model, defense=row.defense,
                   task_id=row.task_id, attack_id=row.attack_id,
                   task_category=row.task_category, v1_concl=row.attack_judge_conclusion)
        try:
            steps = steps_from_traj(row.traj_path)
        except Exception as e:
            rec["error"] = f"read:{type(e).__name__}"
            return rec
        if not steps:
            rec["error"] = "no_steps"
            return rec
        rec["n_steps"] = len(steps)

        parts = []
        for s in steps:
            parts += [f"Step {s['step']}:", f"Reasoning: {s['reasoning']}",
                      f"Action: {s['action'] if s['action'] else '(no action)'}", ""]
        all_steps = "\n".join(parts)
        rec["truncated"] = len(all_steps) > MAX_STEPS_CHARS
        if rec["truncated"]:
            all_steps = all_steps[:MAX_STEPS_CHARS] + "\n...[truncated]"

        full = self.prompt.format(legitimate_objective=row.legitimate_objective,
                                  adversary_goal=row.attacker_goal) + \
            f"\n\nTask goal: {row.legitimate_objective}\n\nAll reasoning steps and actions:\n{all_steps}"

        for attempt in range(6):
            try:
                txt, itok, otok = self._invoke(full)
                rec["v2_concl"], rec["v2_refused"] = parse(txt)
                rec["in_tok"], rec["out_tok"] = itok, otok
                return rec
            except urllib.error.HTTPError as e:
                # insufficient_quota (OpenAI) will not clear by waiting — don't burn retries.
                if e.code == 429 and b"insufficient_quota" in (e.read() if hasattr(e, "read") else b""):
                    rec["error"] = "insufficient_quota"
                    return rec
                if e.code in (429, 500, 502, 503, 529) and attempt < 5:
                    time.sleep(min(2 ** attempt * 3, 60)); continue
                rec["error"] = f"http{e.code}"
                return rec
            except Exception as e:
                if attempt < 5:
                    time.sleep(min(2 ** attempt * 3, 60)); continue
                rec["error"] = type(e).__name__
                return rec
        return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path,
                    default=RESULTS / "rescore_v2" / "traj_records_v2.csv",
                    help="Separate file. NEVER the canonical traj_records.csv — V1 labels "
                         "must survive for the delta table.")
    ap.add_argument("--judge", choices=list(JUDGES), default=DEFAULT_JUDGE,
                    help=f"judge family (default {DEFAULT_JUDGE}; gpt-4o-mini is out of credit)")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=0, help="smoke test: only N trajectories")
    ap.add_argument("--flush-every", type=int, default=100)
    args = ap.parse_args()
    jc = JUDGES[args.judge]

    # Guard: refuse to write over the canonical V1 files, whatever --out says.
    protected = {"traj_records.csv", "traj_records_with_reasoning.parquet",
                 "benign_records.csv"}
    if args.out.name in protected or args.out.resolve() == (RESULTS / args.out.name).resolve() \
            and args.out.name in protected:
        raise SystemExit(f"refusing to write over canonical file: {args.out}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(PARQUET)
    print(f"total trajectories: {len(df)}  "
          f"(v1 conclusion null: {df.attack_judge_conclusion.isna().sum()} — included)",
          file=sys.stderr)

    done: set[str] = set()
    if args.out.exists():
        try:
            prev = pd.read_csv(args.out)
            # Only rows that actually produced a label count as done. Rows that errored
            # (e.g. rate-limited) MUST be retried — treating them as done would silently
            # bake transient 429s into the final numbers as missing data.
            ok = prev[prev.v2_concl.notna()]
            done = set(ok.traj_basename.astype(str))
            n_retry = len(prev) - len(ok)
            print(f"resuming: {len(done)} scored, {n_retry} failed rows will be retried",
                  file=sys.stderr)
        except Exception:
            pass

    todo = df[~df.traj_basename.astype(str).isin(done)]
    if args.limit:
        todo = todo.head(args.limit)
    rows = list(todo.itertuples())
    if not rows:
        print("nothing to do", file=sys.stderr)
        return
    print(f"to score: {len(rows)}  workers={args.workers}  judge={args.judge}", file=sys.stderr)

    gw_base = load_key(GATEWAY_BASE_ENV) if jc.get("gateway") else None
    judge = Judge(load_prompt(), load_key(jc["env"]), args.judge, gateway_base=gw_base)
    new_file = not args.out.exists()
    fh = open(args.out, "a", newline="")
    writer = csv.DictWriter(fh, fieldnames=FIELDS)
    if new_file:
        writer.writeheader()

    lock = threading.Lock()
    t0, n_ok, n_err, tin, tout = time.time(), 0, 0, 0, 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(judge, r) for r in rows]
        for i, fut in enumerate(as_completed(futs), 1):
            rec = fut.result()
            with lock:
                writer.writerow(rec)
                if i % args.flush_every == 0:
                    fh.flush(); os.fsync(fh.fileno())
            n_ok += rec["v2_concl"] is not None
            n_err += rec["error"] is not None
            tin += rec["in_tok"] or 0
            tout += rec["out_tok"] or 0
            if i % 250 == 0 or i == len(rows):
                el = time.time() - t0
                rate = i / el
                eta = (len(rows) - i) / rate / 60 if rate else 0
                print(f"  {i}/{len(rows)}  ok={n_ok} err={n_err}  "
                      f"{rate:.1f}/s  eta={eta:.0f}m  ${tin*jc['pin']/1e6 + tout*jc['pout']/1e6:.2f}",
                      file=sys.stderr, flush=True)
    fh.flush(); os.fsync(fh.fileno()); fh.close()
    print(f"\ndone. scored={n_ok} errors={n_err}  "
          f"cost=${tin*jc['pin']/1e6 + tout*jc['pout']/1e6:.2f}  -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
