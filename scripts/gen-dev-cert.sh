#!/usr/bin/env bash
# gen-dev-cert.sh
#
# Generate a self-signed certificate + key for LOCAL DEVELOPMENT ONLY.
#
# Use case: enabling HTTPS on the backend so the iOS Expo client (which
# requires a trusted certificate to use the device microphone over the
# network) can talk to the dev server.
#
# Output: backend/.local-certs/{key.pem, cert.pem, cert.der}
# These paths are gitignored — never commit them.
#
# Rotation: run this script again at any time to mint a fresh key + cert.
# Old key/cert are simply overwritten.

set -euo pipefail

# --- locate repo root -------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${REPO_ROOT}/backend/.local-certs"

# --- detect LAN IP (override with LAN_IP env var) ---------------------------
if [[ -z "${LAN_IP:-}" ]]; then
  if command -v ipconfig >/dev/null 2>&1; then
    # macOS
    LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
  fi
  if [[ -z "${LAN_IP:-}" ]] && command -v hostname >/dev/null 2>&1; then
    # Linux fallback
    LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  fi
fi

if [[ -z "${LAN_IP:-}" ]]; then
  echo "❌ Could not detect a LAN IP automatically." >&2
  echo "   Re-run with: LAN_IP=192.168.x.y $0" >&2
  exit 1
fi

VALID_DAYS="${VALID_DAYS:-365}"

# --- check openssl ----------------------------------------------------------
if ! command -v openssl >/dev/null 2>&1; then
  echo "❌ openssl is required but not installed." >&2
  exit 1
fi

# --- generate ---------------------------------------------------------------
mkdir -p "${OUT_DIR}"
chmod 700 "${OUT_DIR}"

echo "🔐 Generating self-signed dev cert"
echo "   LAN IP    : ${LAN_IP}"
echo "   Validity  : ${VALID_DAYS} days"
echo "   Output dir: ${OUT_DIR}"
echo

openssl req \
  -x509 \
  -newkey rsa:2048 \
  -nodes \
  -keyout "${OUT_DIR}/key.pem" \
  -out    "${OUT_DIR}/cert.pem" \
  -days   "${VALID_DAYS}" \
  -subj   "/CN=${LAN_IP}" \
  -addext "subjectAltName=IP:${LAN_IP},IP:127.0.0.1,DNS:localhost" \
  2>/dev/null

# DER copy for iOS profile install
openssl x509 \
  -in     "${OUT_DIR}/cert.pem" \
  -outform der \
  -out    "${OUT_DIR}/cert.der"

chmod 600 "${OUT_DIR}/key.pem"
chmod 644 "${OUT_DIR}/cert.pem" "${OUT_DIR}/cert.der"

echo "✅ Done."
echo
echo "Files written:"
ls -la "${OUT_DIR}"
echo
echo "Next steps:"
echo "  • Backend HTTPS:"
echo "      uvicorn app.main:app --reload --port 8000 \\"
echo "          --ssl-keyfile  ${OUT_DIR}/key.pem \\"
echo "          --ssl-certfile ${OUT_DIR}/cert.pem"
echo
echo "  • Trust on iOS (Expo dev):"
echo "      1. AirDrop ${OUT_DIR}/cert.der to your device"
echo "      2. Settings → Profile Downloaded → Install"
echo "      3. Settings → General → About → Certificate Trust Settings → enable"
echo
echo "  ⚠️  These files are gitignored. Never commit them."
