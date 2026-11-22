#!/bin/bash
# Construeste pachetele de distributie pentru Ollama Control:
#   - pachet Debian/Ubuntu (.deb)
#   - AppImage
#
# Rezultatele ajung in directorul `release/`.
set -euo pipefail

APP_NAME="ollama-control"
APP_VERSION="1.0.0"
ARCH="amd64"
PYTHON="${PYTHON:-python3}"

RAZA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${RAZA}"

VENV="${RAZA}/venv"
PY="${VENV}/bin/python"
[ -x "${PY}" ] || PY="${PYTHON}"

BUILD_DIR="${RAZA}/build"
DIST_DIR="${RAZA}/dist"
RELEASE_DIR="${RAZA}/release"
PACKAGING_DIR="${RAZA}/packaging"

echo "==> Curatam directoarele de build"
rm -rf "${BUILD_DIR}/ollama_control" "${DIST_DIR}/ollama_control" "${RELEASE_DIR}"
mkdir -p "${RELEASE_DIR}"

echo "==> Generam iconitele"
"${PACKAGING_DIR}/make_icons.sh"

echo "==> Construim executabilul (PyInstaller, onedir)"
"${PY}" -m PyInstaller "${RAZA}/ollama_control_ui.spec" \
    --noconfirm \
    --distpath "${DIST_DIR}" \
    --workpath "${BUILD_DIR}"

APP_DIR="${DIST_DIR}/ollama_control"
[ -x "${APP_DIR}/ollama_control" ] || {
    echo "Eroare: executabilul nu a fost construit." >&2
    exit 1
}

echo "==> Construim pachetul .deb"
"${PACKAGING_DIR}/build_deb.sh"

echo "==> Construim AppImage"
"${PACKAGING_DIR}/build_appimage.sh"

echo
echo "==> Gata. Artefacte in ${RELEASE_DIR}:"
ls -lh "${RELEASE_DIR}"
