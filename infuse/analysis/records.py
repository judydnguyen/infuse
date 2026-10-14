"""
Trajectory analysis for INFUSE attack tasks.

Extracts per-trajectory metrics and metadata from raw JSON files:
  - ASR-L  : Attack Success Rate (LLM judge)
  - ASR-H  : Attack Success Rate (Heuristic / pattern-matching)
  - RR     : Refusal Rate (LLM judge)
  - Utility-L : Benign task completion (LLM judge)
  - Utility-H : Benign task completion (Heuristic / test script)

Plus token usage, cost, model, defense, and judge reasoning.

Usage
-----
  python data_analysis.py                          # use defaults
  python data_analysis.py --results-dir /path/to/attack_task
  python data_analysis.py --refresh-cache          # re-parse everything
  python data_analysis.py --no-cache               # skip cache entirely
  python data_analysis.py --output-dir /path/to/out
"""

import argparse
import json
import logging
import os
import pickle
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

from infuse.paths import DATA_ROOT
DEFAULT_RESULTS_DIR = DATA_ROOT / "attack_task"
DEFAULT_BENIGN_DIR = DATA_ROOT / "benign_task"
DEFAULT_CACHE_FILE = DATA_ROOT / ".analysis_cache" / "traj_records_cache.pkl"
DEFAULT_BENIGN_CACHE_FILE = DATA_ROOT / ".analysis_cache" / "benign_records_cache.pkl"
DEFAULT_OUTPUT_DIR = DATA_ROOT
DEFAULT_MAX_WORKERS = max(1, cpu_count() - 2)   # leave 2 cores for the OS
DEFAULT_MAX_TRAJ_SIZE_MB = 20                    # skip traj.json files larger than this
CACHE_SAVE_INTERVAL = 2000                       # save cache every N new records


# ---------------------------------------------------------------------------
# Path discovery
# ---------------------------------------------------------------------------

def find_trajectories(results_dir: Path) -> List[Dict[str, Any]]:
    """
    Walk results_dir for *.traj.json files and return a list of path-info dicts.

    Directory structure:
      results_dir/{attack_id}/{task_id}/{model}/[{defense}/]{filename}

    depth-from-root == 4  ->  no defense
    depth-from-root == 5  ->  defense = parts[3]
    """
    entries = []
    for traj_path in results_dir.rglob("*.traj.json"):
        try:
            parts = traj_path.relative_to(results_dir).parts
        except ValueError:
            continue

        if len(parts) == 4:
            attack_id, task_id, model, filename = parts
            defense = "none"
        elif len(parts) == 5:
            attack_id, task_id, model, defense, filename = parts
        else:
            continue  # unexpected depth

        traj_basename = filename.replace(".traj.json", "")
        entries.append(
            dict(
                traj_path=str(traj_path),
                attack_id=attack_id,
                task_id=task_id,
                model=model,
                defense=defense,
                traj_basename=traj_basename,
                filename=filename,
            )
        )
    return entries


def find_benign_trajectories(benign_dir: Path) -> List[Dict[str, Any]]:
    """
    Walk benign_dir for *.traj.json files (no attack injection).

    Directory structure:
      benign_dir/{model}/{task_id}/{filename}

    depth-from-root == 3 (model, task_id, filename)
    """
    entries = []
    for traj_path in benign_dir.rglob("*.traj.json"):
        try:
            parts = traj_path.relative_to(benign_dir).parts
        except ValueError:
            continue

        if len(parts) != 3:
            continue  # unexpected depth

        model, task_id, filename = parts
        traj_basename = filename.replace(".traj.json", "")
        entries.append(
            dict(
                traj_path=str(traj_path),
                task_id=task_id,
                model=model,
                traj_basename=traj_basename,
                filename=filename,
                # fixed fields for benign
                attack_id=None,
                defense="none",
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Token extraction helpers
# ---------------------------------------------------------------------------

def _sum_tokens(trajectory: List[Dict]) -> Dict[str, int]:
    """
    Sum token usage across all turns.

    total_tokens_billed     – sum(prompt + completion) per turn (API cost basis)
    total_completion_tokens – sum(completion) per turn (model output only)
    total_prompt_tokens     – sum(prompt) per turn
    max_context_tokens      – max(prompt_tokens) seen (peak context window)
    num_turns               – number of turns with usage data
    """
    billed = 0
    completion = 0
    prompt_sum = 0
    max_prompt = 0
    turns = 0

    for msg in trajectory:
        usage = (
            msg.get("extra", {})
            .get("response", {})
            .get("usage", None)
        )
        if usage is None:
            continue
        p = usage.get("prompt_tokens", 0) or 0
        c = usage.get("completion_tokens", 0) or 0
        billed += p + c
        completion += c
        prompt_sum += p
        max_prompt = max(max_prompt, p)
        turns += 1

    return dict(
        total_tokens_billed=billed,
        total_completion_tokens=completion,
        total_prompt_tokens=prompt_sum,
        max_context_tokens=max_prompt,
        num_turns=turns,
    )


# ---------------------------------------------------------------------------
# Per-trajectory extraction
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Optional[Dict]:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        log.debug("Cannot load %s: %s", path, e)
        return None


def _worker(args: Tuple[Dict[str, Any], float]) -> Optional[Dict[str, Any]]:
    """Process-pool worker: returns None if the file should be skipped."""
    entry, max_bytes = args
    try:
        size = os.path.getsize(entry["traj_path"])
    except OSError:
        return None
    if size > max_bytes:
        return None  # too large — skip
    return extract_record(entry)


def extract_record(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Build a flat record dict for one trajectory."""
    traj_path = Path(entry["traj_path"])
    stem = entry["traj_basename"]  # e.g. task_27_18017abc_attack1

    judge_path = traj_path.parent / f"{stem}.llm_judge.json"
    benign_path = traj_path.parent / f"{stem}.benign_llm_judge.json"

    rec: Dict[str, Any] = dict(
        traj_path=str(traj_path),
        traj_basename=stem,
        attack_id=entry["attack_id"],
        task_id=entry["task_id"],
        model=entry["model"],
        defense=entry["defense"],
        has_attack_judge=judge_path.exists(),
        has_benign_judge=benign_path.exists(),
        benign_task_id=None,
        exit_status=None,
        task_category=None,
        api_calls=None,
        instance_cost=None,
        total_tokens_billed=None,
        total_completion_tokens=None,
        total_prompt_tokens=None,
        max_context_tokens=None,
        num_turns=None,
        # attack metrics
        asr_l=None,
        asr_h=None,
        rr=None,
        attack_judge_score=None,
        attack_judge_conclusion=None,
        judge_model=None,
        attacker_goal=None,
        legitimate_objective=None,
        attack_judge_reasoning=None,
        # benign metrics
        utility_l=None,
        utility_h=None,
        benign_judge_score=None,
        benign_judge_progress=None,
        benign_judge_reasoning=None,
    )

    # ---- traj.json --------------------------------------------------------
    traj_data = _load_json(traj_path)
    if traj_data is not None:
        info = traj_data.get("info", {})

        rec["exit_status"] = info.get("exit_status")

        task_entry = info.get("task_entry", {})
        rec["benign_task_id"] = task_entry.get("task_id") or task_entry.get("id")
        rec["task_category"] = task_entry.get("task_category")

        model_stats = info.get("model_stats", {})
        rec["api_calls"] = model_stats.get("api_calls")
        rec["instance_cost"] = model_stats.get("instance_cost")

        trajectory = traj_data.get("trajectory", [])
        if trajectory:
            rec.update(_sum_tokens(trajectory))

    # ---- llm_judge.json ---------------------------------------------------
    judge_data = _load_json(judge_path) if rec["has_attack_judge"] else None
    if judge_data is not None:
        lj = judge_data.get("llm_judge", {})
        s = lj.get("success")
        rec["asr_l"] = bool(s) if s is not None else None
        r = lj.get("refused")
        rec["rr"] = bool(r) if r is not None else None
        rec["attack_judge_score"] = lj.get("score")
        rec["judge_model"] = lj.get("judge_model")

        meta = lj.get("metadata", {})
        rec["attack_judge_conclusion"] = meta.get("conclusion")
        rec["attack_judge_reasoning"] = meta.get("judge_response")

        ev = judge_data.get("existing_evaluation", {})
        es = ev.get("evaluation_success")
        rec["asr_h"] = bool(es) if es is not None else None

        ti = judge_data.get("trajectory_info", {})
        rec["attacker_goal"] = ti.get("attacker_goal")
        rec["legitimate_objective"] = ti.get("legitimate_objective")

    # ---- benign_llm_judge.json --------------------------------------------
    benign_data = _load_json(benign_path) if rec["has_benign_judge"] else None
    if benign_data is not None:
        blj = benign_data.get("benign_llm_judge", {})
        bs = blj.get("success")
        rec["utility_l"] = bool(bs) if bs is not None else None
        rec["benign_judge_score"] = blj.get("score")

        bmeta = blj.get("metadata", {})
        rec["benign_judge_progress"] = bmeta.get("progress")
        rec["benign_judge_reasoning"] = bmeta.get("judge_response")

        bev = benign_data.get("existing_evaluation", {})
        bes = bev.get("evaluation_score")
        if bes is None:
            bes = bev.get("evaluation_success")
        rec["utility_h"] = float(bes) if bes is not None else None

    # Fallback: info.evaluation.evaluation_score from traj.json when
    # benign_llm_judge had no existing_evaluation (common in benign-task runs)
    if rec["utility_h"] is None and traj_data is not None:
        ev_fb = traj_data.get("info", {}).get("evaluation", {})
        bes_fb = ev_fb.get("evaluation_score")
        if bes_fb is None:
            bes_fb = ev_fb.get("evaluation_success")
        if bes_fb is not None:
            rec["utility_h"] = float(bes_fb)

    return rec


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def load_cache(cache_file: Path) -> Dict[str, Tuple[float, Dict]]:
    if cache_file.exists():
        try:
            with open(cache_file, "rb") as f:
                cache = pickle.load(f)
            log.info("Loaded cache: %d entries from %s", len(cache), cache_file)
            return cache
        except Exception as e:
            log.warning("Could not read cache (%s); starting fresh", e)
    return {}


def save_cache(cache: Dict, cache_file: Path) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_file, "wb") as f:
        pickle.dump(cache, f, protocol=pickle.HIGHEST_PROTOCOL)
    log.info("Saved cache: %d entries to %s", len(cache), cache_file)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(
    results_dir: Path,
    cache_file: Path,
    output_dir: Path,
    no_cache: bool = False,
    refresh_cache: bool = False,
    max_workers: int = DEFAULT_MAX_WORKERS,
    max_traj_size_mb: float = DEFAULT_MAX_TRAJ_SIZE_MB,
) -> pd.DataFrame:

    log.info("Scanning for trajectories in %s", results_dir)
    entries = find_trajectories(results_dir)
    log.info("Found %d trajectory files", len(entries))

    cache: Dict[str, Tuple[float, Dict]] = {}
    if not no_cache and not refresh_cache:
        cache = load_cache(cache_file)

    max_bytes = max_traj_size_mb * 1024 * 1024

    # Split into cache hits vs entries that need parsing
    cached_records: List[Dict] = []
    to_parse: List[Tuple[Dict, float]] = []  # (entry, mtime)
    skipped_size = 0

    for entry in entries:
        traj_path_str = entry["traj_path"]
        try:
            mtime = os.path.getmtime(traj_path_str)
            size = os.path.getsize(traj_path_str)
        except OSError:
            continue

        if size > max_bytes:
            skipped_size += 1
            continue

        if not no_cache and traj_path_str in cache:
            cached_mtime, cached_rec = cache[traj_path_str]
            if cached_mtime == mtime:
                cached_records.append(cached_rec)
                continue

        to_parse.append((entry, mtime))

    log.info(
        "Cache hits: %d  |  To parse: %d  |  Skipped (>%.0f MB): %d",
        len(cached_records), len(to_parse), max_traj_size_mb, skipped_size,
    )

    # Parallel extraction of uncached entries
    new_records: List[Dict] = []
    new_or_updated = 0

    if to_parse:
        worker_args = [(entry, max_bytes) for entry, _ in to_parse]
        mtime_map = {entry["traj_path"]: mtime for entry, mtime in to_parse}

        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_worker, arg): arg[0] for arg in worker_args}
            with tqdm(total=len(futures), desc="Parsing trajectories", unit="traj") as pbar:
                for future in as_completed(futures):
                    entry = futures[future]
                    pbar.update(1)
                    try:
                        rec = future.result()
                    except Exception as exc:
                        log.debug("Worker failed for %s: %s", entry["traj_path"], exc)
                        rec = None
                    if rec is None:
                        continue

                    new_records.append(rec)
                    new_or_updated += 1
                    if not no_cache:
                        mtime = mtime_map[entry["traj_path"]]
                        cache[entry["traj_path"]] = (mtime, rec)
                        if new_or_updated % CACHE_SAVE_INTERVAL == 0:
                            save_cache(cache, cache_file)

    records = cached_records + new_records
    log.info(
        "Parsed %d new/updated; %d from cache (total %d)",
        new_or_updated,
        len(cached_records),
        len(records),
    )

    if not no_cache:
        save_cache(cache, cache_file)

    df = pd.DataFrame(records)

    for col in ["asr_l", "asr_h", "rr", "utility_l",
                "has_attack_judge", "has_benign_judge"]:
        if col in df.columns:
            df[col] = df[col].astype("boolean")

    # ---- Outputs ----------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)

    reasoning_cols = [
        "attack_judge_reasoning", "benign_judge_reasoning",
        "attacker_goal", "legitimate_objective",
    ]
    csv_cols = [c for c in df.columns if c not in reasoning_cols]

    csv_path = output_dir / "traj_records.csv"
    df[csv_cols].to_csv(csv_path, index=False)
    log.info("Wrote %s  (%d rows, %d cols)", csv_path, len(df), len(csv_cols))

    parquet_path = output_dir / "traj_records_with_reasoning.parquet"
    df.to_parquet(parquet_path, index=False)
    log.info("Wrote %s", parquet_path)

    _print_summary(df)
    return df


def run_benign(
    benign_dir: Path,
    cache_file: Path,
    output_dir: Path,
    no_cache: bool = False,
    refresh_cache: bool = False,
    max_workers: int = DEFAULT_MAX_WORKERS,
    max_traj_size_mb: float = DEFAULT_MAX_TRAJ_SIZE_MB,
) -> pd.DataFrame:
    """
    Analyse vanilla (no-attack) trajectories from benign_dir.
    Saves benign_records.csv and benign_records_with_reasoning.parquet.
    """
    log.info("Scanning for benign trajectories in %s", benign_dir)
    entries = find_benign_trajectories(benign_dir)
    log.info("Found %d benign trajectory files", len(entries))

    cache: Dict[str, Tuple[float, Dict]] = {}
    if not no_cache and not refresh_cache:
        cache = load_cache(cache_file)

    max_bytes = max_traj_size_mb * 1024 * 1024

    cached_records: List[Dict] = []
    to_parse: List[Tuple[Dict, float]] = []
    skipped_size = 0

    for entry in entries:
        traj_path_str = entry["traj_path"]
        try:
            mtime = os.path.getmtime(traj_path_str)
            size = os.path.getsize(traj_path_str)
        except OSError:
            continue

        if size > max_bytes:
            skipped_size += 1
            continue

        if not no_cache and traj_path_str in cache:
            cached_mtime, cached_rec = cache[traj_path_str]
            if cached_mtime == mtime:
                cached_records.append(cached_rec)
                continue

        to_parse.append((entry, mtime))

    log.info(
        "Cache hits: %d  |  To parse: %d  |  Skipped (>%.0f MB): %d",
        len(cached_records), len(to_parse), max_traj_size_mb, skipped_size,
    )

    new_records: List[Dict] = []
    new_or_updated = 0

    if to_parse:
        worker_args = [(entry, max_bytes) for entry, _ in to_parse]
        mtime_map = {entry["traj_path"]: mtime for entry, mtime in to_parse}

        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_worker, arg): arg[0] for arg in worker_args}
            with tqdm(total=len(futures), desc="Parsing benign trajectories", unit="traj") as pbar:
                for future in as_completed(futures):
                    entry = futures[future]
                    pbar.update(1)
                    try:
                        rec = future.result()
                    except Exception as exc:
                        log.debug("Worker failed for %s: %s", entry["traj_path"], exc)
                        rec = None
                    if rec is None:
                        continue

                    new_records.append(rec)
                    new_or_updated += 1
                    if not no_cache:
                        mtime = mtime_map[entry["traj_path"]]
                        cache[entry["traj_path"]] = (mtime, rec)
                        if new_or_updated % CACHE_SAVE_INTERVAL == 0:
                            save_cache(cache, cache_file)

    records = cached_records + new_records
    log.info(
        "Parsed %d new/updated; %d from cache (total %d)",
        new_or_updated, len(cached_records), len(records),
    )

    if not no_cache:
        save_cache(cache, cache_file)

    df = pd.DataFrame(records)

    for col in ["utility_l", "has_attack_judge", "has_benign_judge"]:
        if col in df.columns:
            df[col] = df[col].astype("boolean")

    # Drop attack-specific columns that are meaningless for benign runs
    drop_cols = ["asr_l", "asr_h", "rr", "attack_judge_score",
                 "attack_judge_conclusion", "attacker_goal"]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

    output_dir.mkdir(parents=True, exist_ok=True)

    reasoning_cols = ["benign_judge_reasoning", "legitimate_objective",
                      "attack_judge_reasoning"]
    csv_cols = [c for c in df.columns if c not in reasoning_cols]

    csv_path = output_dir / "benign_records.csv"
    df[csv_cols].to_csv(csv_path, index=False)
    log.info("Wrote %s  (%d rows, %d cols)", csv_path, len(df), len(csv_cols))

    parquet_path = output_dir / "benign_records_with_reasoning.parquet"
    df.to_parquet(parquet_path, index=False)
    log.info("Wrote %s", parquet_path)

    _print_benign_summary(df)
    return df


def _print_benign_summary(df: pd.DataFrame) -> None:
    total = len(df)
    print(f"\n{'='*60}")
    print("  BENIGN TRAJECTORY SUMMARY  (no attack)")
    print(f"{'='*60}")
    print(f"  Total trajectories  : {total:,}")

    print(f"\n  {'Metric':<22} {'Mean':>8}  {'N':>8}")
    print(f"  {'-'*40}")
    for label, col in [("Util-L (llm judge) ", "utility_l"),
                        ("Util-H (heuristic) ", "utility_h")]:
        if col in df.columns:
            valid = df[col].dropna()
            n = len(valid)
            mean = float(valid.mean()) if n > 0 else float("nan")
            print(f"  {label:<22} {mean:>8.3f}  {n:>8,}")

    print(f"\n  Per-model Utility-L (n >= 5):")
    print(f"  {'Model':<45} {'Util-L':>6}  {'Util-H':>6}  {'N':>6}")
    print(f"  {'-'*65}")
    grp = (
        df.groupby("model", observed=True)
        .agg(
            utility_l=("utility_l", lambda x: float(x.dropna().mean()) if len(x.dropna()) > 0 else float("nan")),
            utility_h=("utility_h", lambda x: float(x.dropna().mean()) if len(x.dropna()) > 0 else float("nan")),
            n=("traj_path", "count"),
        )
        .reset_index()
    )
    grp = grp[grp["n"] >= 5].sort_values("utility_l", ascending=False)
    for _, row in grp.iterrows():
        model_short = str(row["model"])[-45:]
        print(
            f"  {model_short:<45} "
            f"{row['utility_l']:>6.3f}  "
            f"{row['utility_h']:>6.3f}  "
            f"{int(row['n']):>6}"
        )
    print(f"{'='*60}\n")


def _print_summary(df: pd.DataFrame) -> None:
    total = len(df)
    with_attack = int(df["has_attack_judge"].sum())
    with_benign = int(df["has_benign_judge"].sum())

    print(f"\n{'='*60}")
    print("  TRAJECTORY ANALYSIS SUMMARY")
    print(f"{'='*60}")
    print(f"  Total trajectories  : {total:,}")
    print(f"  With attack judge   : {with_attack:,}")
    print(f"  With benign judge   : {with_benign:,}")

    print(f"\n  {'Metric':<22} {'Mean':>8}  {'N':>8}")
    print(f"  {'-'*40}")
    metric_map = [
        ("ASR-L  (llm judge)", "asr_l"),
        ("ASR-H  (heuristic) ", "asr_h"),
        ("RR     (refusal)   ", "rr"),
        ("Util-L (llm judge) ", "utility_l"),
        ("Util-H (heuristic) ", "utility_h"),
    ]
    for label, col in metric_map:
        if col in df.columns:
            valid = df[col].dropna()
            n = len(valid)
            mean = float(valid.mean()) if n > 0 else float("nan")
            print(f"  {label:<22} {mean:>8.3f}  {n:>8,}")

    # Per-model (models with >= 10 trajs)
    print(f"\n  Per-model breakdown (n >= 10), sorted by ASR-L desc:")
    print(f"  {'Model':<45} {'ASR-L':>6}  {'RR':>6}  {'Util-L':>6}  {'N':>6}")
    print(f"  {'-'*75}")
    grp = (
        df.groupby("model", observed=True)
        .agg(
            asr_l=("asr_l", lambda x: float(x.dropna().mean()) if x.dropna().any() else float("nan")),
            rr=("rr", lambda x: float(x.dropna().mean()) if x.dropna().any() else float("nan")),
            utility_l=("utility_l", lambda x: float(x.dropna().mean()) if x.dropna().any() else float("nan")),
            n=("traj_path", "count"),
        )
        .reset_index()
    )
    grp = grp[grp["n"] >= 10].sort_values("asr_l", ascending=False)
    for _, row in grp.iterrows():
        model_short = str(row["model"])[-45:]
        print(
            f"  {model_short:<45} "
            f"{row['asr_l']:>6.3f}  "
            f"{row['rr']:>6.3f}  "
            f"{row['utility_l']:>6.3f}  "
            f"{int(row['n']):>6}"
        )

    # Defense breakdown
    if df["defense"].nunique() > 1:
        print(f"\n  Per-defense breakdown:")
        print(f"  {'Defense':<30} {'ASR-L':>6}  {'RR':>6}  {'Util-L':>6}  {'N':>6}")
        print(f"  {'-'*58}")
        dgrp = (
            df.groupby("defense", observed=True)
            .agg(
                asr_l=("asr_l", lambda x: float(x.dropna().mean()) if x.dropna().any() else float("nan")),
                rr=("rr", lambda x: float(x.dropna().mean()) if x.dropna().any() else float("nan")),
                utility_l=("utility_l", lambda x: float(x.dropna().mean()) if x.dropna().any() else float("nan")),
                n=("traj_path", "count"),
            )
            .reset_index()
            .sort_values("asr_l", ascending=False)
        )
        for _, row in dgrp.iterrows():
            print(
                f"  {str(row['defense']):<30} "
                f"{row['asr_l']:>6.3f}  "
                f"{row['rr']:>6.3f}  "
                f"{row['utility_l']:>6.3f}  "
                f"{int(row['n']):>6}"
            )

    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Summarize from cache (no re-parse)
# ---------------------------------------------------------------------------

def summarize_from_cache(
    cache_file: Path,
    benign_cache_file: Path,
    attack_only: bool = False,
    benign_only: bool = False,
) -> None:
    """
    Load existing caches and print metric summaries, excluding:
      - GCG attack trajectories (attack_id contains 'gcg')
      - Any trajectory with a non-'none' defense
    """
    def _records_from_cache(path: Path) -> List[Dict]:
        if not path.exists():
            log.warning("Cache not found: %s", path)
            return []
        try:
            with open(path, "rb") as f:
                cache = pickle.load(f)
            log.info("Loaded %d entries from %s", len(cache), path)
            return [rec for _, rec in cache.values()]
        except Exception as e:
            log.error("Failed to load cache %s: %s", path, e)
            return []

    def _filter(df: pd.DataFrame) -> pd.DataFrame:
        mask = pd.Series(True, index=df.index)
        if "attack_id" in df.columns:
            mask &= ~df["attack_id"].astype(str).str.contains("gcg", case=False, na=False)
        if "defense" in df.columns:
            mask &= df["defense"].fillna("none") == "none"
        dropped = (~mask).sum()
        if dropped:
            log.info("Filtered out %d records (gcg or non-none defense)", dropped)
        return df[mask].copy()

    if not benign_only:
        records = _records_from_cache(cache_file)
        if records:
            df = pd.DataFrame(records)
            for col in ["asr_l", "asr_h", "rr", "utility_l",
                        "has_attack_judge", "has_benign_judge"]:
                if col in df.columns:
                    df[col] = df[col].astype("boolean")
            df = _filter(df)
            log.info("Attack records after filter: %d", len(df))
            _print_summary(df)

    if not attack_only:
        records = _records_from_cache(benign_cache_file)
        if records:
            df = pd.DataFrame(records)
            for col in ["utility_l", "has_attack_judge", "has_benign_judge"]:
                if col in df.columns:
                    df[col] = df[col].astype("boolean")
            df = _filter(df)
            log.info("Benign records after filter: %d", len(df))
            _print_benign_summary(df)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Analyze INFUSE attack and benign trajectories.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--results-dir", type=Path, default=DEFAULT_RESULTS_DIR,
        help="Root directory containing attack_task trajectories.",
    )
    p.add_argument(
        "--benign-dir", type=Path, default=DEFAULT_BENIGN_DIR,
        help="Root directory containing benign (no-attack) trajectories.",
    )
    p.add_argument(
        "--cache-file", type=Path, default=DEFAULT_CACHE_FILE,
        help="Cache file for attack trajectories.",
    )
    p.add_argument(
        "--benign-cache-file", type=Path, default=DEFAULT_BENIGN_CACHE_FILE,
        help="Cache file for benign trajectories.",
    )
    p.add_argument(
        "--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
        help="Directory to write all output CSV/parquet files.",
    )
    p.add_argument(
        "--no-cache", action="store_true",
        help="Skip cache entirely (read all files fresh, do not save cache).",
    )
    p.add_argument(
        "--refresh-cache", action="store_true",
        help="Ignore existing cache and rebuild from scratch.",
    )
    p.add_argument(
        "--max-workers", type=int, default=DEFAULT_MAX_WORKERS,
        help="Number of parallel worker processes for parsing.",
    )
    p.add_argument(
        "--max-traj-size-mb", type=float, default=DEFAULT_MAX_TRAJ_SIZE_MB,
        help="Skip traj.json files larger than this (MB). Set 0 to disable.",
    )
    p.add_argument(
        "--attack-only", action="store_true",
        help="Only process attack trajectories; skip benign.",
    )
    p.add_argument(
        "--benign-only", action="store_true",
        help="Only process benign trajectories; skip attack.",
    )
    p.add_argument(
        "--from-cache", action="store_true",
        help="Skip parsing; load existing caches and print summary (excludes gcg and defenses).",
    )
    p.add_argument(
        "--verbose", action="store_true",
        help="Enable DEBUG logging.",
    )
    return p.parse_args()


def main(ns=None) -> int:
    """Entry point for ``infuse records``; *ns* is the CLI namespace (results_dir, benign, workers, no_cache)."""
    from infuse.paths import results_dir as _rd
    base = _rd(getattr(ns, "results_dir", None))
    common = dict(output_dir=base, no_cache=bool(getattr(ns, "no_cache", False)), refresh_cache=False,
                  max_workers=getattr(ns, "workers", None) or DEFAULT_MAX_WORKERS, max_traj_size_mb=DEFAULT_MAX_TRAJ_SIZE_MB)
    if getattr(ns, "benign", False):
        run_benign(benign_dir=base / "benign_task", cache_file=base / ".analysis_cache" / "benign_records_cache.pkl", **common)
    else:
        run(results_dir=base / "attack_task", cache_file=base / ".analysis_cache" / "traj_records_cache.pkl", **common)
    return 0


if __name__ == "__main__":
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    common = dict(
        output_dir=args.output_dir,
        no_cache=args.no_cache,
        refresh_cache=args.refresh_cache,
        max_workers=args.max_workers,
        max_traj_size_mb=args.max_traj_size_mb,
    )

    if args.from_cache:
        summarize_from_cache(
            cache_file=args.cache_file,
            benign_cache_file=args.benign_cache_file,
            attack_only=args.attack_only,
            benign_only=args.benign_only,
        )
        sys.exit(0)

    if not args.benign_only:
        run(results_dir=args.results_dir, cache_file=args.cache_file, **common)

    if not args.attack_only:
        run_benign(benign_dir=args.benign_dir, cache_file=args.benign_cache_file, **common)
