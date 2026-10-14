#!/bin/bash
# Download the trajectory dataset that backs the paper's figures.
#
# The dataset is hosted as a Hugging Face dataset repo. While the repo is
# private, fetching requires a token with read access:
#
#   HF_TOKEN=hf_xxx bash scripts/download_artifacts.sh
#
# Once the repo is public, no token is needed.
#
# Reviewers without access can instead:
#   (a) re-run a small subset locally  →  `make reproduce`
#   (b) work off the curated sample committed in this repo  →  sample_trajectories/
#
# Override the source with ARTIFACT_URL / ARTIFACT_SHA256 to fetch a different
# build (e.g. the privacy-filtered release subset).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${REPO_ROOT}/results"
TARBALL="${REPO_ROOT}/raw_trajectories.tar.zst"

HF_REPO="${HF_REPO:-judynguyen16/infuse-bench-trajectories}"
ARTIFACT_URL="${ARTIFACT_URL:-https://huggingface.co/datasets/${HF_REPO}/resolve/main/raw_trajectories.tar.zst}"
ARTIFACT_SHA256="${ARTIFACT_SHA256:-31240bbcb9523ff6ba0c19d58e3019f5ce494879219ff03fc87d29d92c1569e4}"

# 38,866 trajectories, 2.62 GB uncompressed. Excludes 7 oversize runaway-generation
# files (see excluded_oversize.txt in the dataset repo); none appear in
# traj_records.csv, so no reported result depends on them.

for bin in curl tar zstd sha256sum; do
  command -v "$bin" >/dev/null 2>&1 || { echo "[artifact] ERROR: '$bin' not found in PATH" >&2; exit 1; }
done

AUTH=()
if [[ -n "${HF_TOKEN:-}" ]]; then
  AUTH=(-H "Authorization: Bearer ${HF_TOKEN}")
  echo "[artifact] using HF_TOKEN for authentication"
else
  echo "[artifact] no HF_TOKEN set — assuming the dataset repo is public"
fi

echo "[artifact] downloading $ARTIFACT_URL"
mkdir -p "$DEST"

if ! curl -fL --progress-bar "${AUTH[@]}" -o "$TARBALL" "$ARTIFACT_URL"; then
  echo "[artifact] ERROR: download failed." >&2
  echo "[artifact] If the dataset repo is still private, set HF_TOKEN to a token with read access:" >&2
  echo "[artifact]   HF_TOKEN=hf_xxx bash scripts/download_artifacts.sh" >&2
  rm -f "$TARBALL"
  exit 1
fi

echo "[artifact] verifying sha256"
if ! echo "${ARTIFACT_SHA256}  ${TARBALL}" | sha256sum -c -; then
  echo "[artifact] ERROR: checksum mismatch — refusing to extract." >&2
  echo "[artifact] Got: $(sha256sum "$TARBALL" | cut -d' ' -f1)" >&2
  rm -f "$TARBALL"
  exit 1
fi

echo "[artifact] extracting into $DEST"
# Archive members are rooted at results/, so extract at REPO_ROOT.
tar --zstd -xf "$TARBALL" -C "$REPO_ROOT"

echo "[artifact] cleanup"
rm -f "$TARBALL"

n=$(find "$DEST" -name '*.traj.json' | wc -l)
echo "[artifact] done. ${n} trajectories in $DEST"
