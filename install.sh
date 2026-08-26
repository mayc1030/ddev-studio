#!/usr/bin/env bash
# ==============================================================================
#  DDEV Studio - Instalador Automático para Linux (Ubuntu / Debian / MATE / GNOME)
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}        🚀 Instalando DDEV Studio en tu Sistema       ${NC}"
echo -e "${BLUE}======================================================${NC}"

# Directorios de destino
INSTALL_DIR="$HOME/.local/share/ddev-manager"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$HOME/Desktop"

# 1. Comprobar dependencias del sistema
echo -e "\n${YELLOW}[1/5] Verificando dependencias...${NC}"
if ! command -v ddev &> /dev/null; then
    echo -e "${RED}⚠️  Advertencia: 'ddev' no fue detectado en PATH. Asegúrate de tener DDEV instalado.${NC}"
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Se requiere Python 3.${NC}"
    exit 1
fi

# 2. Crear carpetas necesarias
echo -e "${YELLOW}[2/5] Creando directorios de instalación...${NC}"
mkdir -p "$INSTALL_DIR/icons"
mkdir -p "$BIN_DIR"
mkdir -p "$APP_DIR"

# 3. Copiar archivos de la aplicación
echo -e "${YELLOW}[3/5] Copiando archivos de DDEV Studio...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -f "$SCRIPT_DIR/ddev_manager.py" "$INSTALL_DIR/ddev_manager.py"
cp -rf "$SCRIPT_DIR/icons/"* "$INSTALL_DIR/icons/"
chmod +x "$INSTALL_DIR/ddev_manager.py"

# 4. Crear comando CLI ddev-gui
echo -e "${YELLOW}[4/5] Creando acceso directo CLI (ddev-gui)...${NC}"
cat << 'LAUNCHER' > "$BIN_DIR/ddev-gui"
#!/usr/bin/env bash
python3 "$HOME/.local/share/ddev-manager/ddev_manager.py" "$@"
LAUNCHER
chmod +x "$BIN_DIR/ddev-gui"

# 5. Crear lanzadores de escritorio y menú
echo -e "${YELLOW}[5/5] Registrando accesos directos de escritorio y menú de aplicaciones...${NC}"
cat << DESKTOP_FILE > "$APP_DIR/ddev-studio.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=DDEV Studio
Comment=Gestor Visual de Proyectos DDEV
Exec=python3 $INSTALL_DIR/ddev_manager.py
Icon=$INSTALL_DIR/icons/ddev.svg
Terminal=false
Categories=Development;IDE;GTK;
StartupNotify=true
DESKTOP_FILE
chmod +x "$APP_DIR/ddev-studio.desktop"

# Copiar al Escritorio si existe la carpeta Desktop
if [ -d "$DESKTOP_DIR" ]; then
    cp -f "$APP_DIR/ddev-studio.desktop" "$DESKTOP_DIR/ddev-studio.desktop"
    chmod +x "$DESKTOP_DIR/ddev-studio.desktop"
    gio set "$DESKTOP_DIR/ddev-studio.desktop" metadata::trusted true 2>/dev/null || true
fi

# Asegurar PATH en .bashrc si no está presente
if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.bashrc" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    fi
fi

echo -e "\n${GREEN}======================================================${NC}"
echo -e "${GREEN}  ✅ ¡Instalación de DDEV Studio completada con éxito!  ${NC}"
echo -e "${GREEN}======================================================${NC}"
echo -e "Puedes abrirlo de las siguientes maneras:"
echo -e "  1. Desde el menú de aplicaciones de tu escritorio (Programación > DDEV Studio)"
echo -e "  2. Desde el icono en tu Escritorio"
echo -e "  3. Desde la terminal ejecutando: ${BLUE}ddev-gui${NC}\n"
