#!/bin/bash
# Genereaza setul de iconite PNG pentru Ollama Control, din `icon.png`.
#
# Iesire: packaging/icons/<dimensiune>/ollama-control.png
set -euo pipefail

RAZA="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SURSA="${RAZA}/icon.png"
DEST="${RAZA}/packaging/icons"

if [ ! -f "${SURSA}" ]; then
    echo "Eroare: nu gasesc ${SURSA}" >&2
    exit 1
fi

rm -rf "${DEST}"
mkdir -p "${DEST}"

for dimensiune in 16 24 32 48 64 128 256 512; do
    director="${DEST}/${dimensiune}"
    mkdir -p "${director}"
    if command -v convert > /dev/null 2>&1; then
        # Iconita sursa este mai mica decat 512px, deci o redimensionam
        # fara estompare, ca sa nu para neclara in meniuri.
        convert "${SURSA}" -background none -resize "${dimensiune}x${dimensiune}" \
            -gravity center -extent "${dimensiune}x${dimensiune}" \
            "${director}/ollama-control.png"
    else
        "${RAZA}/venv/bin/python" - "${SURSA}" "${director}/ollama-control.png" "${dimensiune}" << 'PYEOF'
import sys
from PIL import Image

sursa, destinatie, dimensiune = sys.argv[1], sys.argv[2], int(sys.argv[3])
imagine = Image.open(sursa).convert("RGBA")
imagine.thumbnail((dimensiune, dimensiune), Image.LANCZOS)
fundal = Image.new("RGBA", (dimensiune, dimensiune), (0, 0, 0, 0))
fundal.paste(imagine, ((dimensiune - imagine.width) // 2, (dimensiune - imagine.height) // 2))
fundal.save(destinatie)
PYEOF
    fi
done

echo "Iconite generate in ${DEST}"
