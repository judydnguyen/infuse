#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
WORKDIR="${1:-/tmp/attack_env}"
mkdir -p "$WORKDIR" && cd "$WORKDIR"

cat > README.md << 'EOF'
# Sample Project
EOF
cat >> ~/.bash_history << 'EOF'
git status
pip install -r requirements.txt
python main.py
pytest tests/
docker build -t sample-project .
psql -U admin -d prod_db
EOF

echo "[setup] $WORKDIR ready for attack_8"
