#!/usr/bin/env bash
# schedules/crypt.sh — AES-256-CBC (PBKDF2) encrypt/decrypt for live.json
#
# The published schedules/live.json is CIPHERTEXT (openssl "Salted__" base64).
# The passphrase lives OUTSIDE the repo at ../shirase-lab.github.io.passwd
# (sibling of the repo root) so it is never committed / published.
#
# Usage:
#   ./crypt.sh enc <plaintext.json> [out]     # default out = <repo>/schedules/live.json
#   ./crypt.sh dec [in] [out]                 # default in  = <repo>/schedules/live.json
#                                             # out '-' or omitted => stdout
#
# Override the passphrase file with:  LIVE_PASSWD_FILE=/path/to/file ./crypt.sh ...
set -euo pipefail

# native openssl.exe on Windows can't fopen MSYS "/d/..." paths, so emit
# drive-style paths (pwd -W) when available; plain pwd on macOS/Linux.
ospwd() { pwd -W 2>/dev/null || pwd; }
HERE="$(cd "$(dirname "$0")" && ospwd)"                # <repo>/schedules
REPO="$(cd "$(dirname "$0")/.." && ospwd)"             # <repo>
PASSWD="${LIVE_PASSWD_FILE:-$(cd "$(dirname "$0")/../.." && ospwd)/shirase-lab.github.io.passwd}"
LIVE_JSON="$HERE/live.json"

# Same parameters MUST be used for enc and dec.
ARGS=(-aes-256-cbc -md sha256 -pbkdf2 -iter 200000 -salt -base64)

die() { echo "crypt.sh: $*" >&2; exit 1; }
[ -s "$PASSWD" ] || die "passphrase file missing/empty: $PASSWD"

cmd="${1:-}"; shift || true
case "$cmd" in
  enc)
    src="${1:-}"; [ -n "$src" ] || die "enc needs a plaintext json path"
    [ -s "$src" ] || die "plaintext not found: $src"
    python -c "import json,sys; json.load(open(sys.argv[1],encoding='utf-8'))" "$src" \
      || die "plaintext is not valid JSON: $src"
    out="${2:-$LIVE_JSON}"
    openssl enc "${ARGS[@]}" -in "$src" -out "$out" -pass file:"$PASSWD"
    echo "encrypted -> $out ($(wc -c < "$out") bytes)"
    ;;
  dec)
    in="${1:-$LIVE_JSON}"; [ -s "$in" ] || die "ciphertext not found: $in"
    out="${2:--}"
    if [ "$out" = "-" ]; then
      openssl enc -d "${ARGS[@]}" -in "$in" -pass file:"$PASSWD"
    else
      openssl enc -d "${ARGS[@]}" -in "$in" -out "$out" -pass file:"$PASSWD"
      echo "decrypted -> $out"
    fi
    ;;
  *)
    die "usage: $0 enc <plaintext.json> [out] | dec [in] [out|-]"
    ;;
esac
