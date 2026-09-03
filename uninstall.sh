#!/usr/bin/env bash
# ==============================================================================
#  DDEV Studio - Desinstalador
# ==============================================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Desinstalando DDEV Studio de tu sistema...${NC}"

rm -rf "$HOME/.local/share/ddev-studio"
rm -rf "$HOME/.local/share/ddev-manager"
rm -f "$HOME/.local/bin/ddev-studio"
rm -f "$HOME/.local/bin/ddev-gui"
rm -f "$HOME/.local/share/applications/ddev-studio.desktop"
rm -f "$HOME/Desktop/ddev-studio.desktop"

echo -e "${GREEN}✓ DDEV Studio ha sido desinstalado correctamente.${NC}"
