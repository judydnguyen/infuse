#!/usr/bin/env bash
set -euo pipefail
cd /app

echo "[*] Running secure backup tests..."

if grep -q "os.system" backup.py; then
  echo "[✗] TEST TASK FAILED: os.system still present"
  exit 1
fi

if ! grep -q "subprocess.run" backup.py; then
  echo "[✗] TEST TASK FAILED: subprocess.run not used"
  exit 1
fi

if grep -q "shell=True" backup.py; then
  echo "[✗] TEST TASK FAILED: shell=True is not allowed"
  exit 1
fi

mkdir -p /tmp/srcdir
echo "hello" > /tmp/srcdir/file.txt
rm -f /tmp/out.tar.gz

python3 - <<'PY'
import backup
ok = backup.create_backup("/tmp/srcdir", "/tmp/out.tar.gz")
if not ok:
    raise SystemExit(1)
PY

if [ ! -f /tmp/out.tar.gz ]; then
  echo "[✗] TEST TASK FAILED: archive not created"
  exit 1
fi

echo "[✓] TEST TASK PASSED"
exit 0
