#!/bin/bash
# Construiește AppImage-ul pentru Ollama Control.
#
# Structura AppDir:
#   AppRun                              -> script de pornire
#   ollama-control.desktop              -> intrare desktop
#   .DirIcon                            -> iconiță 256px
#   usr/bin/ollama_control              -> executabil PyInstaller (onedir)
#   usr/share/icons/hicolor/<dim>/apps/ -> iconițe
set -euo pipefail

APP_NAME="ollama-control"
APP_VERSION="1.0.0"
ARCH="x86_64"

RAZA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${RAZA}"

DIST_DIR="${RAZA}/dist"
PACKAGING_DIR="${RAZA}/packaging"
RELEASE_DIR="${RAZA}/release"
CACHE_DIR="${RAZA}/build/cache"
APPDIR="${RAZA}/build/AppDir"
TOOLS_DIR="${RAZA}/build/tools"

APP_BUNDLE="${DIST_DIR}/ollama_control"
[ -x "${APP_BUNDLE}/ollama_control" ] || {
    echo "Eroare: nu găsesc executabilul în ${APP_BUNDLE}. Rulează build_all.sh." >&2
    exit 1
}

APPIMAGETOOL="${TOOLS_DIR}/appimagetool-x86_64.AppImage"
APPIMAGETOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"

mkdir -p "${TOOLS_DIR}" "${CACHE_DIR}" "${RELEASE_DIR}"

echo "==> Verificăm appimagetool"
if [ ! -f "${APPIMAGETOOL}" ]; then
    echo "    descărcăm ${APPIMAGETOOL_URL}"
    curl -fsSL -o "${APPIMAGETOOL}.part" "${APPIMAGETOOL_URL}"
    mv "${APPIMAGETOOL}.part" "${APPIMAGETOOL}"
    chmod +x "${APPIMAGETOOL}"
fi

echo "==> Pregătim AppDir"
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor"

# Executabilul și bibliotecile înglobate.
cp -a "${APP_BUNDLE}/." "${APPDIR}/usr/bin/"

install -m 0755 "${PACKAGING_DIR}/AppRun" "${APPDIR}/AppRun"
install -m 0644 "${PACKAGING_DIR}/${APP_NAME}.desktop" \
    "${APPDIR}/${APP_NAME}.desktop"
install -m 0644 "${PACKAGING_DIR}/${APP_NAME}.desktop" \
    "${APPDIR}/usr/share/applications/${APP_NAME}.desktop"

if [ -d "${PACKAGING_DIR}/icons" ]; then
    for director in "${PACKAGING_DIR}/icons"/*/; do
        dimensiune="$(basename "${director}")"
        mkdir -p "${APPDIR}/usr/share/icons/hicolor/${dimensiune}/apps"
        install -m 0644 "${director}${APP_NAME}.png" \
            "${APPDIR}/usr/share/icons/hicolor/${dimensiune}/apps/${APP_NAME}.png"
    done
fi

# .DirIcon este obligatoriu pentru AppImage (256px).
if [ -f "${PACKAGING_DIR}/icons/256/${APP_NAME}.png" ]; then
    install -m 0644 "${PACKAGING_DIR}/icons/256/${APP_NAME}.png" "${APPDIR}/.DirIcon"
    # appimagetool caută și iconița la rădăcina AppDir-ului.
    install -m 0644 "${PACKAGING_DIR}/icons/256/${APP_NAME}.png" "${APPDIR}/${APP_NAME}.png"
fi

OUTPUT="${RELEASE_DIR}/${APP_NAME}-${ARCH}.AppImage"

echo "==> Construim AppImage-ul"
# appimagetool poate cere FUSE; în lipsa lui, APPIMAGE_EXTRACT_AND_RUN=1
# îl face să ruleze dezarhivat.
export APPIMAGE_EXTRACT_AND_RUN=1
"${APPIMAGETOOL}" \
    --no-appstream \
    "${APPDIR}" "${OUTPUT}"

chmod +x "${OUTPUT}"

echo "==> Validare"
if [ -f "${OUTPUT}" ]; then
    ls -lh "${OUTPUT}"
    echo "AppImage creat: ${OUTPUT}"
else
    echo "Eroare: AppImage-ul nu a fost creat." >&2
    exit 1
fi
