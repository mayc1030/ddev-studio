# 🚀 DDEV Studio

**DDEV Studio** es una aplicación de escritorio nativa (GUI) moderna, rápida y ligera diseñada para Linux (Ubuntu, Debian, MATE, GNOME, XFCE) que te permite crear, administrar y monitorear proyectos basados en **[DDEV](https://ddev.com)** con 1 solo clic.

![Linux](https://img.shields.io/badge/Linux-Ubuntu%20%7C%20Debian%20%7C%20MATE-E95420?logo=linux&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![GTK3](https://img.shields.io/badge/GTK-3.0-4E9A06?logo=gnome&logoColor=white)
![DDEV](https://img.shields.io/badge/DDEV-v1.23+-0074D9?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🌟 Características Principales

- ⚡ **Creación en 1 Clic con Recetas Inteligentes:**
  - 💧 **Drupal:** Selector de versión unificado (**Drupal 11, 10, 9, 8 y 7**) con Composer, Drush e instalación desatendida (`admin / admin`).
  - 🌐 **WordPress:** Descarga automática del núcleo con WP-CLI, base de datos y usuario administrador preconfigurado.
  - 🔴 **Laravel:** Instalación con Composer, estructura `public/` y generación automática de `APP_KEY`.
  - ⚛️ **React (Vite + TypeScript):** Scaffolding rápido con Vite, enlace a puerto expuesto 5173 e instalación de paquetes npm.
  - 💚 **Vue 3 (Vite + TypeScript):** Configuración automática de Fast Refresh y compilación `npm run build`.
  - 🎼 **Symfony:** Proyecto con Skeleton y bundle WebApp listo para producción.
  - 🐘 **PHP Plano / HTML:** Entorno limpio para scripts PHP o maquetaciones rápidas.

- 📊 **Panel Visual de Proyectos:**
  - Lista interactiva de todos tus proyectos DDEV con estados en tiempo real (**Running / Stopped / Paused**).
  - Botones de acción rápida: **Iniciar ▶**, **Detener ⏹**, **Abrir en Navegador 🌐**, **Abrir Carpeta 📁**, **Abrir Terminal 💻** y **Eliminar 🗑**.
  - Buscador dinámico de proyectos por nombre o tecnología.

- ⚙️ **Opciones Avanzadas:**
  - Selector de versión de PHP (8.4, 8.3, 8.2, 8.1, 8.0, 7.4).
  - Selector de Base de Datos (MariaDB 10.11 / 10.5, MySQL 8.0, PostgreSQL 16).
  - Selector de Node.js (v22, v20, v18).
  - Manejo automático de conflictos de volúmenes huérfanos y limpieza de directorios.

- 🛠️ **Herramientas Globales:**
  - Apagar todos los proyectos activos (`ddev poweroff`).
  - Iniciar todos los proyectos (`ddev start -a`).
  - Limpieza de caché de imágenes de Docker (`ddev clean`).
  - Acceso directo al panel Traefik Router.

---

## 📦 Requisitos Previos

Antes de instalar DDEV Studio, asegúrate de tener instalado:

1. **Docker / Docker Desktop**
2. **DDEV** (Versión 1.23 o superior):
   ```bash
   curl -fsSL https://ddev.com/install.sh | bash
   ```
3. **Python 3 y paquetes GTK3 en Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-gi gir1.2-gtk-3.0
   ```

---

## 🚀 Instalación Rápida

1. Clona este repositorio o descarga la carpeta:
   ```bash
   git clone https://github.com/mayc1030/ddev-studio.git
   cd ddev-studio
   ```

2. Ejecuta el script de instalación:
   ```bash
   ./install.sh
   ```

¡Listo! La aplicación se instalará en `~/.local/share/ddev-manager`, agregará el comando `ddev-gui` a tu terminal y creará los accesos directos en el menú de aplicaciones y en tu Escritorio.

---

## 💻 Uso

Puedes abrir **DDEV Studio** de 3 formas:

- **Desde el Menú:** Busca **DDEV Studio** en la sección *Desarrollo / Programación*.
- **Desde el Escritorio:** Doble clic en el icono **DDEV Studio** en tu escritorio.
- **Desde la Terminal:**
  ```bash
  ddev-gui
  ```

---

## 📂 Estructura del Repositorio

```text
ddev-studio/
├── ddev_manager.py       # Aplicación principal en Python 3 + GTK3
├── icons/                # Iconos SVG de tecnologías (WordPress, Drupal, Laravel, etc.)
│   ├── ddev.svg
│   ├── drupal.svg
│   ├── laravel.svg
│   ├── php.svg
│   ├── react.svg
│   ├── symfony.svg
│   ├── vue.svg
│   └── wordpress.svg
├── ddev-studio.desktop   # Archivo de acceso directo de escritorio
├── install.sh            # Script de instalación automática
├── uninstall.sh          # Script de desinstalación limpia
├── .gitignore            # Exclusiones de control de versiones
├── LICENSE               # Licencia MIT
└── README.md             # Documentación del proyecto
```

---

## 🗑️ Desinstalación

Para desinstalar DDEV Studio de tu sistema:
```bash
./uninstall.sh
```

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Siéntete libre de abrir un *Issue* o enviar un *Pull Request* con nuevas recetas de frameworks o mejoras a la interfaz.

---

## 📄 Licencia

Distribuido bajo la Licencia **MIT**. Consulta el archivo `LICENSE` para más detalles.
