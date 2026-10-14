#!/usr/bin/env bash
# Generate GCG adversarial suffixes for all attack templates.
#
# Calls scripts/gcg_generate.py (loads the model once and iterates over every
# template, saving results incrementally to data/gcg_results.json).
#
# Usage:
#   # All templates, default settings
#   ./scripts/run_gcg.sh
#
#   # Custom model / device
#   ./scripts/run_gcg.sh --model meta-llama/Llama-3.2-3B-Instruct --device cuda:1
#
#   # Specific attack IDs only
#   ./scripts/run_gcg.sh --attack-ids 1,9,14
#
#   # Resume an interrupted run
#   ./scripts/run_gcg.sh --resume
#
#   # Tune GCG hyper-parameters
#   ./scripts/run_gcg.sh --num-steps 500 --search-width 64 --topk 64
#
# Environment overrides (can also be set before calling):
#   MODEL, DEVICE, OUTPUT, TARGET, NUM_STEPS, SEARCH_WIDTH, TOPK, SEED
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────────────────────
MODEL="${MODEL:-meta-llama/Meta-Llama-3-8B-Instruct}"
DEVICES="${DEVICES:-auto}"          # "auto" = all visible GPUs; or "cuda:0,cuda:1,..."
DEVICE="${DEVICE:-cuda:0}"          # fallback single device when auto finds only one GPU
OUTPUT="${OUTPUT:-data/gcg_results.json}"
TARGET="${TARGET:-Sure, I will help with that right away.}"
NUM_STEPS="${NUM_STEPS:-200}"
SEARCH_WIDTH="${SEARCH_WIDTH:-32}"
TOPK="${TOPK:-32}"
SEED="${SEED:-42}"
ATTACK_IDS=""
RESUME=false
SKIP_EVAL=false

# ── Argument parsing ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)         MODEL="$2";        shift 2 ;;
        --devices)       DEVICES="$2";     shift 2 ;;
        --device)        DEVICE="$2";      shift 2 ;;
        --output)        OUTPUT="$2";       shift 2 ;;
        --target)        TARGET="$2";       shift 2 ;;
        --num-steps)     NUM_STEPS="$2";    shift 2 ;;
        --search-width)  SEARCH_WIDTH="$2"; shift 2 ;;
        --topk)          TOPK="$2";         shift 2 ;;
        --seed)          SEED="$2";         shift 2 ;;
        --attack-ids)    ATTACK_IDS="$2";   shift 2 ;;
        --resume)        RESUME=true;       shift ;;
        --skip-eval)     SKIP_EVAL=true;    shift ;;
        -h|--help)
            cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --model         HuggingFace model ID                   (default: meta-llama/Meta-Llama-3-8B-Instruct)
  --devices       "auto" or comma-separated device list  (default: auto — all visible GPUs)
  --device        Fallback single device for auto mode   (default: cuda:0)
  --output        Output JSON path                       (default: data/gcg_results.json)
  --target        GCG target string
  --num-steps     GCG optimisation steps                 (default: 200)
  --search-width  GCG search width                       (default: 32)
  --topk          GCG top-k candidates                   (default: 32)
  --seed          Random seed                            (default: 42)
  --attack-ids    Comma-separated id_raw values to run   (default: all)
  --resume        Skip templates already present in the output file
  --skip-eval     Skip the post-GCG refusal evaluation pass
  -h, --help      Show this help

Examples:
  $0                                                          # auto-detect all GPUs
  $0 --devices cuda:0,cuda:1,cuda:2                           # explicit 3-GPU run
  $0 --model meta-llama/Llama-3.2-3B-Instruct --device cuda:1 # single GPU override
  $0 --attack-ids 1,9,14                                      # subset of templates
  $0 --resume                                                 # continue interrupted run
  $0 --num-steps 500 --search-width 64 --topk 64              # stronger search
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# ── Load HF token from .env (needed for gated models like Llama) ──────────────
if [[ -z "${HF_TOKEN:-}" ]]; then
    ENV_FILE="${PROJECT_ROOT}/.env"
    if [[ -f "${ENV_FILE}" ]]; then
        HF_TOKEN="$(grep -oP '^HF_TOKEN=\K.*' "${ENV_FILE}" | tr -d "'" | tr -d '"')" || true
    fi
fi
if [[ -n "${HF_TOKEN:-}" ]]; then
    export HF_TOKEN
    export HUGGING_FACE_HUB_TOKEN="${HF_TOKEN}"
fi

# ── Print configuration ───────────────────────────────────────────────────────
echo "=============================================="
echo "GCG Attack String Generator"
echo "=============================================="
echo "Model:         ${MODEL}"
echo "Devices:       ${DEVICES}  (fallback: ${DEVICE})"
echo "Output:        ${OUTPUT}"
echo "Steps:         ${NUM_STEPS}"
echo "Search width:  ${SEARCH_WIDTH}"
echo "Top-k:         ${TOPK}"
echo "Seed:          ${SEED}"
echo "Attack IDs:    ${ATTACK_IDS:-all}"
echo "Resume:        ${RESUME}"
echo "=============================================="
echo ""

cd "${PROJECT_ROOT}"

# ── Build Python command ──────────────────────────────────────────────────────
CMD=(
    python scripts/gcg_generate.py
    --model-id     "${MODEL}"
    --devices      "${DEVICES}"
    --device       "${DEVICE}"
    --output       "${OUTPUT}"
    --target       "${TARGET}"
    --num-steps    "${NUM_STEPS}"
    --search-width "${SEARCH_WIDTH}"
    --topk         "${TOPK}"
    --seed         "${SEED}"
)

if [[ -n "${ATTACK_IDS}" ]]; then
    IFS=',' read -ra ID_ARRAY <<< "${ATTACK_IDS}"
    CMD+=(--attack-ids "${ID_ARRAY[@]}")
fi

if [[ "${RESUME}" == "true" ]]; then
    CMD+=(--resume)
fi

if [[ "${SKIP_EVAL}" == "true" ]]; then
    CMD+=(--skip-eval)
fi

# ── Run ───────────────────────────────────────────────────────────────────────
echo "Running: ${CMD[*]}"
echo ""
"${CMD[@]}"
