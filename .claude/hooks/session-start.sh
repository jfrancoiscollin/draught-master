#!/bin/bash
# SessionStart hook for draught-master — see backend/pedagogy/INTEROP.md
# for the dilf <-> draught-master contract this session is operating under.

set -euo pipefail

# Only run automatic setup in remote Claude Code on the web. Local
# sessions can opt-in by setting CLAUDE_CODE_REMOTE=true manually.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
    exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

DILF_PIN=$(grep -E "dilf" backend/requirements.txt 2>/dev/null || echo "(none)")

printf '\n'
printf '======================================================================\n'
printf ' draught-master — consumes jfrancoiscollin/dilf\n'
printf '======================================================================\n'
printf ' Contract:   backend/pedagogy/INTEROP.md\n'
printf ' dilf pin:   %s\n' "$DILF_PIN"
printf ' Smoke test: backend/tests/test_dilf_imports.py\n'
printf '======================================================================\n'

pip install -r backend/requirements.txt --quiet --disable-pip-version-check
pip install -r requirements-dev.txt --quiet --disable-pip-version-check

# One-line status of the dilf-imports smoke test. Non-blocking — the
# session still starts even if dilf:main has moved out from under us.
if (cd backend && pytest tests/test_dilf_imports.py -q --no-header --tb=no 2>/dev/null \
        | tail -1 | grep -qE "^[0-9]+ passed"); then
    printf ' [OK] dilf-imports smoke test green\n'
else
    printf ' [FAIL] dilf-imports smoke test FAILING — coordinate via INTEROP.md\n'
fi
printf '======================================================================\n\n'
