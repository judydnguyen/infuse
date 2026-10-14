#!/usr/bin/env python3
"""
Compact ASR figure for the model panel.

One row per model, grouped by family. Bar = ASR-L (LLM judge, V2 rubric);
--with-asr-h overlays ASR-H (heuristic) as a dot. Reads summary_table_v2.csv.

USAGE
  python3 scripts/plot_model_panel_asr.py                       # -> figs/model_panel_asr.{pdf,png}
  python3 scripts/plot_model_panel_asr.py --paper-only          # drop the revision-added models (GPT-5, GPT-5.4)
  python3 scripts/plot_model_panel_asr.py --headline            # 10-model headline figure, ranked by ASR-L
  infuse figures --out-dir <paper>/figs
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

from infuse.paths import DATA_ROOT, REPO_ROOT
RESULTS_DIR = DATA_ROOT
FIGS_DIR = REPO_ROOT / "figs"

# Family blocks in table order (open-source first, then API vendors).
FAMILY_ORDER = ["Llama", "Gemma", "Qwen", "GPT", "Claude", "Gemini"]
FAMILY_LABEL = {"Llama": "Llama", "Gemma": "Gemma", "Qwen": "Qwen",
                "GPT": "OpenAI", "Claude": "Anthropic", "Gemini": "Gemini"}

# Models added in the revision (full 40x40 grid); --paper-only drops them.
NEW_MODELS = {"GPT-5", "GPT-5.4"}
# Headline subset: every family, the newest frontier models, and both ASR extremes.
HEADLINE_MODELS = [
    "Llama-3.1-8B-Instruct", "Gemma-3-27B-IT", "Qwen2.5-32B-Instruct",
    "GPT-4o-mini", "GPT-5", "GPT-5.4",
    "Claude-Haiku-4.5", "Claude-Sonnet-4.6",
    "Gemini-2.5-Flash", "Gemini-3.1-Flash-Lite-Preview",
]
# Rows that are not part of the attack panel (benign-only aliases, near-empty runs).
DROP = {"Gemini-3.1-Flash-Live-Preview", "Gemini-3.1-Lite-Preview",
        "Gemini-Flash-3.1-Lite-Preview", "Average"}

DISPLAY = {
    "Llama-3.2-3B-Instruct": "Llama-3.2-3B", "Llama-3.1-8B-Instruct": "Llama-3.1-8B",
    "Gemma-3-12B-IT": "Gemma-3-12B", "Gemma-3-27B-IT": "Gemma-3-27B",
    "Qwen3-4B-Instruct": "Qwen3-4B", "Qwen2.5-14B-Instruct": "Qwen2.5-14B",
    "Qwen2.5-32B-Instruct": "Qwen2.5-32B",
    "Gemini-3-Flash-Preview": "Gemini-3-Flash",
    "Gemini-3.1-Flash-Lite-Preview": "Gemini-3.1-Flash-Lite",
}

# Nord-based palette shared with the other paper figures (make_plots.py):
# ASR-L = coral, ASR-H = orange; ink and grid from the same scale.
import os
C_ASR_L = os.environ.get("ASR_L_COLOR", "#BF616A")   # Nord coral (ASR-L in taskwise fig)
C_ASR_H = os.environ.get("ASR_H_COLOR", "#2E3440")   # Nord polar night; #D08770 (taskwise orange) is too close to coral on one row
INK = "#2E3440"
INK2 = "#4C566A"
INK3 = "#7B8494"
GRID = "#E5E9F0"


def family_of(name: str) -> str:
    for f in FAMILY_ORDER:
        if name.lower().startswith(f.lower()):
            return f
    return "Other"


def load(results_dir: Path, paper_only: bool, models: list[str] | None = None,
         ranked: bool = False) -> pd.DataFrame:
    table = results_dir / "summary_table_v2.csv"
    if not table.exists():
        from infuse.analysis.summary import build
        build(results_dir)
    df = pd.read_csv(table)
    df = df.rename(columns={"LLM": "model", "ASR-L": "asr_l", "ASR-H": "asr_h"})
    df = df[~df["model"].isin(DROP)].dropna(subset=["asr_l", "asr_h"]).copy()
    if paper_only:
        df = df[~df["model"].isin(NEW_MODELS)]
    if models:
        missing = set(models) - set(df["model"])
        if missing:
            raise SystemExit(f"models not in summary table: {sorted(missing)}")
        df = df[df["model"].isin(models)]
    df["family"] = df["model"].map(family_of)
    df["label"] = df["model"].map(lambda m: DISPLAY.get(m, m))
    df["fam_rank"] = df["family"].map(FAMILY_ORDER.index)
    if ranked:  # single ranked list, most vulnerable at the top
        df = df.sort_values("asr_l", ascending=False).reset_index(drop=True)
    else:       # family blocks; within a block, most vulnerable at the top
        df = df.sort_values(["fam_rank", "asr_l"], ascending=[True, False]).reset_index(drop=True)
    return df


def style() -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Nimbus Roman", "STIXGeneral", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "legend.fontsize": 7, "axes.edgecolor": INK3, "axes.linewidth": 0.6,
        "xtick.color": INK2, "ytick.color": INK, "axes.labelcolor": INK,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def plot(df: pd.DataFrame, out_dir: Path, stem: str = "model_panel_asr",
         grouped: bool = True, mean_ref: float | None = None,
         show_h: bool = False, show_mean: bool = False) -> None:
    style()
    n = len(df)
    fams = list(dict.fromkeys(df["family"])) if grouped else []
    gap = 0.9 if grouped else 0.0  # space between family blocks (holds the header)

    # y position: rows top-to-bottom, with a gap after each family block.
    y = np.zeros(n)
    pos, prev = 0.0, None
    for i, f in enumerate(df["family"]):
        if grouped and prev is not None and f != prev:
            pos += gap
        y[i] = pos
        pos += 1.0
        prev = f
    y = -y  # top row at 0, descending

    fig_h = 0.165 * n + 0.15 * max(len(fams) - 1, 0) + 0.6
    fig, ax = plt.subplots(figsize=(3.4, fig_h))

    ax.barh(y, df["asr_l"], height=0.62, color=C_ASR_L, zorder=3, linewidth=0)
    if show_h:
        ax.scatter(df["asr_h"], y, s=22, color=C_ASR_H, edgecolor="white",
                   linewidth=0.9, zorder=4)

    # Reference line: the full-panel mean when a subset is shown, else the shown mean.
    mean_l = df["asr_l"].mean() if mean_ref is None else mean_ref
    mean_txt = f"mean {mean_l*100:.0f}%" if mean_ref is None else f"panel mean {mean_l*100:.0f}%"
    if show_mean:
        ax.axvline(mean_l, color=INK3, lw=0.7, ls=(0, (3, 2)), zorder=2)
        ax.text(mean_l + 0.006, y[0] + (1.05 if grouped else 0.62), mean_txt, fontsize=6.5,
            color=INK2, ha="left", va="bottom")

    # Family header sits in the gap above each block, flush with the tick labels.
    ax.set_yticks(y)
    ax.set_yticklabels(df["label"])
    ax.tick_params(axis="y", length=0, pad=2)
    ax.tick_params(axis="x", length=2, width=0.5)
    for f in fams:
        rows = np.where(df["family"] == f)[0]
        ax.text(-0.01, y[rows[0]] + 0.72, FAMILY_LABEL[f],
                transform=ax.get_yaxis_transform(), ha="right", va="center",
                fontsize=6.5, color=INK2, fontweight="bold", clip_on=False)

    xmax = max(df["asr_l"].max(), df["asr_h"].max() if show_h else 0)
    ax.set_xlim(0, xmax + 0.04)
    ax.set_xticks(np.arange(0, xmax + 0.04, 0.1))
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1.0, decimals=0))
    top_pad = (1.35 if grouped else 0.9) if show_mean else (1.1 if grouped else 0.6)
    ax.set_ylim(y[-1] - 0.7, y[0] + top_pad)
    ax.set_xlabel("Attack success rate (ASR-L, LLM judge, %)" if not show_h else "Attack success rate (%)")
    ax.grid(axis="x", color=GRID, lw=0.5, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)

    if show_h:  # single series needs no legend; the axis label names it
        handles = [
            Patch(facecolor=C_ASR_L, label="ASR-L (LLM judge)"),
            Line2D([], [], marker="o", ls="", color=C_ASR_H, markeredgecolor="white",
                   markersize=5, label="ASR-H (heuristic)"),
        ]
        ax.legend(handles=handles, loc="lower right", frameon=True, framealpha=0.95,
                  edgecolor="none", handlelength=1.2, handletextpad=0.5,
                  borderpad=0.4, labelspacing=0.3)

    fig.subplots_adjust(left=0.36, right=0.98, top=0.985, bottom=0.11)
    out_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out_dir / f"{stem}.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print(f"Saved -> {out_dir / stem}.pdf / .png  ({n} models, mean ASR-L {mean_l:.3f})")


def main(ns=None) -> int:
    argv = None
    if ns is not None:
        argv = []
        if getattr(ns, 'results_dir', None): argv += ['--results-dir', str(ns.results_dir)]
        if getattr(ns, 'out_dir', None): argv += ['--out-dir', str(ns.out_dir)]
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    p.add_argument("--out-dir", type=Path, default=FIGS_DIR)
    p.add_argument("--paper-only", action="store_true", help="drop GPT-5 / GPT-5.4 (added in the revision)")
    p.add_argument("--stem", default="model_panel_asr")
    p.add_argument("--with-asr-h", action="store_true", help="overlay ASR-H (heuristic) as a dot")
    p.add_argument("--with-mean", action="store_true", help="draw the panel-mean reference line")
    p.add_argument("--models", nargs="+", help="explicit subset of LLM names from the summary table")
    p.add_argument("--ranked", action="store_true", help="single list sorted by ASR-L instead of family blocks")
    p.add_argument("--headline", action="store_true",
                   help=f"10-model headline preset, ranked by ASR-L: {', '.join(HEADLINE_MODELS)}")
    a = p.parse_args(argv)
    models, ranked, stem = a.models, a.ranked, a.stem
    if a.headline:
        models, ranked = HEADLINE_MODELS, True
        if stem == "model_panel_asr":
            stem = "model_panel_asr_headline"
    full = load(a.results_dir, a.paper_only)
    mean_ref = full["asr_l"].mean() if models else None
    plot(load(a.results_dir, a.paper_only, models, ranked), a.out_dir, stem,
         grouped=not ranked, mean_ref=mean_ref, show_h=a.with_asr_h,
         show_mean=a.with_mean)

    return 0


if __name__ == "__main__":
    main()
