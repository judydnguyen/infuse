"""Per-model summary table (``summary_table_v2.csv``) from the per-trajectory records.

Input: ``traj_records_v2.csv`` (V2 judge, preferred) or ``traj_records.csv``, as written by
``infuse judge`` + ``infuse records``. Output columns match what :mod:`infuse.analysis.figures` reads:
``LLM, ASR-L, ASR-H, RR, Utility-L, n``.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

_ASR_L_CANDIDATES = ("asr_l", "v2_concl", "llm_judge_success")
_ASR_H_CANDIDATES = ("asr_h", "heuristic_success")
_RR_CANDIDATES = ("rr", "v2_refused", "refusal")
_UTIL_CANDIDATES = ("utility_l", "benign_llm_success", "task_success")


def _first(df: pd.DataFrame, names: tuple[str, ...]) -> str | None:
    return next((n for n in names if n in df.columns), None)


def _as_rate(s: pd.Series) -> pd.Series:
    if s.dtype == object:
        s = s.map(lambda v: {"true": 1, "false": 0, "yes": 1, "no": 0, "success": 1, "fail": 0}.get(str(v).strip().lower(), v))
    return pd.to_numeric(s, errors="coerce")


def summarize(records: pd.DataFrame, min_n: int = 10, defense: str | None = "none") -> pd.DataFrame:
    df = records.copy()
    if defense is not None and "defense" in df.columns:
        df = df[df["defense"].fillna("none").astype(str).str.lower().isin([defense, ""])]
    cols = {"ASR-L": _first(df, _ASR_L_CANDIDATES), "ASR-H": _first(df, _ASR_H_CANDIDATES),
            "RR": _first(df, _RR_CANDIDATES), "Utility-L": _first(df, _UTIL_CANDIDATES)}
    if cols["ASR-L"] is None or "model" not in df.columns:
        raise ValueError(f"records need a `model` column and one of {_ASR_L_CANDIDATES}; got {list(df.columns)[:20]}")
    agg = {"n": ("model", "size")}
    for out, src in cols.items():
        if src is not None:
            df[out] = _as_rate(df[src])
            agg[out] = (out, "mean")
    table = df.groupby("model", observed=True).agg(**agg).reset_index().rename(columns={"model": "LLM"})
    table = table[table["n"] >= min_n].sort_values("ASR-L", ascending=False).reset_index(drop=True)
    for c in ("ASR-L", "ASR-H", "RR", "Utility-L"):
        if c not in table.columns:
            table[c] = float("nan")
    return table[["LLM", "ASR-L", "ASR-H", "RR", "Utility-L", "n"]]


def build(results_dir: Path, out: Path | None = None, min_n: int = 10) -> Path:
    src = next((results_dir / n for n in ("traj_records_v2.csv", "traj_records.csv") if (results_dir / n).exists()), None)
    if src is None:
        raise FileNotFoundError(f"no traj_records*.csv under {results_dir}; run `infuse judge` then `infuse records`")
    table = summarize(pd.read_csv(src), min_n=min_n)
    out = out or results_dir / "summary_table_v2.csv"
    table.to_csv(out, index=False)
    return out


__all__ = ["summarize", "build"]
