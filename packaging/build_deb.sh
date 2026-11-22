#!/bin/bash
# Construiește pachetul Debian/Ubuntu (.deb) pentru Ollama Control.
#
# Structura instalată:
#   /usr/bin/ollama-control            -> symlink către executabil
#   /usr/lib/ollama-control/           -> bundle PyInstaller (onedir)
#   /usr/share/applications/ollama-control.desktop
#   /usr/share/icons/hicolor/<dim>/apps/ollama-control.png
set -euo pipefail

APP_NAME="ollama-control"
APP_VERSION="1.0.0"
ARCH="amd64"
MAINTAINER="Ollama Control <ollama-control@localhost>"
SECTION="utils"
PRIORITY="optional"
HOMEPAGE="https://localhost/ollama-control"

RAZA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${RAZA}"

DIST_DIR="${RAZA}/dist"
PACKAGING_DIR="${RAZA}/packaging"
RELEASE_DIR="${RAZA}/release"
STAGING="${RAZA}/build/deb/${APP_NAME}"

APP_BUNDLE="${DIST_DIR}/ollama_control"
[ -x "${APP_BUNDLE}/ollama_control" ] || {
    echo "Eroare: nu gasesc executabilul in ${APP_BUNDLE}. Rulează build_all.sh." >&2
    exit 1
}

echo "==> Pregătim arborele de instalare"
rm -rf "${STAGING}"
mkdir -p "${STAGING}/DEBIAN"
mkdir -p "${STAGING}/usr/bin"
mkdir -p "${STAGING}/usr/lib/${APP_NAME}"
mkdir -p "${STAGING}/usr/share/applications"
mkdir -p "${STAGING}/usr/share/icons/hicolor"

# Bundle-ul aplicației (executabil + biblioteci Python înglobate).
cp -a "${APP_BUNDLE}/." "${STAGING}/usr/lib/${APP_NAME}/"

# Symlink în /usr/bin, ca aplicația să fie pornibilă ca `ollama-control`.
ln -sf "/usr/lib/${APP_NAME}/ollama_control" "${STAGING}/usr/bin/${APP_NAME}"

# Fișier .desktop + iconițe.
install -m 0644 "${PACKAGING_DIR}/${APP_NAME}.desktop" \
    "${STAGING}/usr/share/applications/${APP_NAME}.desktop"

if [ -d "${PACKAGING_DIR}/icons" ]; then
    for director in "${PACKAGING_DIR}/icons"/*/; do
        dimensiune="$(basename "${director}")"
        mkdir -p "${STAGING}/usr/share/icons/hicolor/${dimensiune}/apps"
        install -m 0644 "${director}${APP_NAME}.png" \
            "${STAGING}/usr/share/icons/hicolor/${dimensiune}/apps/${APP_NAME}.png"
    done
fi

# Fișierul de control Debian.
INSTALLED_SIZE="$(du -ks "${STAGING}/usr/lib/${APP_NAME}" | cut -f1)"

cat > "${STAGING}/DEBIAN/control" << EOF
Package: ${APP_NAME}
Version: ${APP_VERSION}
Section: ${SECTION}
Priority: ${PRIORITY}
Architecture: ${ARCH}
Maintainer: ${MAINTAINER}
Installed-Size: ${INSTALLED_SIZE}
Homepage: ${HOMEPAGE}
Depends: libc6, libgtk-3-0, libx11-6, libxext6, libxrender1, libxi6, libfreetype6, libfontconfig1, libxkbcommon0, libdbus-1-3, libglib2.0-0, policykit-1, curl
Recommends: ollama
Description: Panou desktop pentru controlul serviciului local Ollama
 Ollama Control oferă o interfață grafică pentru administrarea unei
 instanțe locale Ollama: pornirea, oprirea și repornirea serviciului,
 detectarea modelului activ, încărcarea și ejectarea modelelor, crearea
 de variante cu context personalizat și ștergerea modelelor.
EOF

cat > "${STAGING}/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
# Reimprospateaza cache-ul iconitelor si al desktop-urilor, daca sunt disponibile.
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache > /dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF

cat > "${STAGING}/DEBIAN/postrm" << 'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache > /dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
fi
exit 0
EOF

chmod 0755 "${STAGING}/DEBIAN/postinst" "${STAGING}/DEBIAN/postrm"

DEBIAN_FILE="${RELEASE_DIR}/${APP_NAME}_${APP_VERSION}_${ARCH}.deb"

echo "==> Construim ${DEBIAN_FILE}"
fakeroot dpkg-deb --root-owner-group --build "${STAGING}" "${DEBIAN_FILE}"

echo "==> Validare"
dpkg-deb --info "${DEBIAN_FILE}" | head -20
desktop-file-validate "${STAGING}/usr/share/applications/${APP_NAME}.desktop" \
    && echo "Desktop file valid."

echo "Pachet creat: ${DEBIAN_FILE}"
