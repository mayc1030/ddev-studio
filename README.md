# 🚀 DDEV Studio

**DDEV Studio** es una aplicación de escritorio nativa (GUI) moderna, rápida y ligera diseñada para Linux (Ubuntu, Debian, Linux Mint, MATE, GNOME, XFCE) que te permite crear, importar, administrar y monitorear proyectos basados en **[DDEV](https://ddev.com)** con 1 solo clic.

![Linux](https://img.shields.io/badge/Linux-Ubuntu%20%7C%20Debian%20%7C%20MATE-E95420?logo=linux&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![GTK3](https://img.shields.io/badge/GTK-3.0-4E9A06?logo=gnome&logoColor=white)
![DDEV](https://img.shields.io/badge/DDEV-v1.23+-0074D9?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🌟 Características Principales

### ⚡ Creación en 1 Clic con Recetas Inteligentes
- 💧 **Drupal (Multisite & Standalone):**
  - Selector de versión unificado (**Drupal 11, 10, 9, 8 y 7**) con Composer y Drush.
  - Instalación desatendida automática (`admin / admin`).
  - **Soporte Avanzado para Drupal Multisite:** Gestión nativa de subsitios, sincronización atómica de FQDNs (`additional_fqdns`), base de datos dedicada por subsitio y ejecución de Drush contextual por sitio.
- 🌐 **WordPress:** Descarga automática del núcleo con WP-CLI, base de datos y usuario administrador preconfigurado.
- 🔴 **Laravel:** Instalación con Composer, estructura `public/` y generación automática de `APP_KEY`.
- 🐍 **Django (Python 3):**
  - Estructura inicial con `django-admin startproject`.
  - Aislamiento automático en entorno virtual (`.venv`) dentro del proyecto.
  - Conectores para MySQL (`PyMySQL`) y PostgreSQL (`psycopg2-binary`).
  - Migraciones automáticas y creación de superusuario (`admin / admin`).
  - Nginx Reverse Proxy integrado para servir en `https://<proyecto>.ddev.site`.
- 🧪 **Flask (Python 3):**
  - Scaffolding de microframework con `app.py` estilizado y listo para ejecutar.
  - Entorno virtual aislado (`.venv`) y proxy reverso en Nginx.
- 🅰️ **Angular:**
  - Scaffolding oficial mediante `@angular/cli` y Node.js v22/v20/v18.
  - Compatibilidad completa con dev server moderno Vite y `--allowed-hosts`.
  - Desactivación no interactiva de analíticas (`NG_CLI_ANALYTICS=false`).
  - Live Dev Server en segundo plano conectado a `https://<proyecto>.ddev.site`.
- ⚛️ **React (Vite + TypeScript):** Scaffolding rápido con Vite, Fast Refresh y proxy a puerto expuesto.
- 💚 **Vue 3 (Vite + TypeScript):** Plantilla moderna con Hot Module Replacement (HMR).
- 🎼 **Symfony:** Proyecto con Skeleton y bundle WebApp listo para producción.
- 🐘 **PHP Plano / HTML:** Entorno limpio para scripts PHP o maquetaciones rápidas.

---

### 📁 Importación Inteligente de Proyectos Existentes
- **Detección Automática:** Analiza carpetas locales y autodetecta la tecnología (Drupal, WordPress, Laravel, Symfony, Django, Flask, Angular, React, Vue, PHP), la raíz web (`docroot`, `public`, `web`, `dist`, etc.), la versión óptima de PHP y configuración de Drupal Multisite.
- **Modo Switcher en Nuevo Proyecto:** Alterna entre `📦 Descargar Proyecto Nuevo` y `📁 Importar Carpeta Existente`.
- **Acceso Rápido:** Botón de importación directa desde el buscador y en el estado vacío de *Mis Proyectos*.

---

### 📊 Panel Visual de Gestión y Control
- **Monitoreo en Tiempo Real:** Visualiza el estado de cada contenedor (**Running 🟢 / Stopped 🔴 / Paused 🟡**).
- **Acciones Rápidas en 1 Clic:**
  - Iniciar ▶, Detener ⏹, Reiniciar 🔄.
  - Abrir en Navegador 🌐 (con soporte HTTPS / SSL automático).
  - Abrir Carpeta 📁 (en el explorador de archivos del sistema).
  - Abrir Terminal SSH 💻 (`ddev ssh` interactivo).
  - Eliminar Proyecto 🗑 (con confirmación segura).
- **💧 Suite Drush Integrada para Drupal:**
  - ⚡ Limpieza de Caché Inmediata (`drush cr` / `drush cc all`).
  - 🔑 Acceso Admin One-Time Login (`drush uli`) con apertura automática en navegador.
  - 🔄 Ejecución de actualizaciones de Base de Datos (`drush updb -y`).
  - 📤 / 📥 Exportación e Importación de Configuración (`drush cex` / `drush cim`).
  - ⏰ Ejecución de Cron (`drush cron`).
  - 📊 Diagnóstico del Sitio (`drush status`) y Visor de Logs (`drush watchdog`).

---

### ⚙️ Arquitectura Robusta y Resiliente
- **Nginx Reverse Proxy Automático (`.ddev/nginx_full/nginx-site.conf`):** Redirige transparentemente el tráfico HTTP/HTTPS y WebSockets para aplicaciones Node.js y Python hacia sus puertos internos (`8000`, `5000`, `4200`, `5173`).
- **Configuraciones Modulares (`.ddev/config.daemon.yaml`):** Cero conflictos de sintaxis YAML o duplicación de claves en `.ddev/config.yaml`.
- **Selector de Base de Datos:** MariaDB 10.11 / 10.5, MySQL 8.0, PostgreSQL 16.
- **Selector de PHP y Node.js:** PHP 8.4, 8.3, 8.2, 8.1, 8.0, 7.4 y Node.js 22, 20, 18.
- **Herramientas Globales:**
  - Apagar todos los proyectos (`ddev poweroff`).
  - Iniciar todos los proyectos (`ddev start -a`).
  - Limpieza de imágenes de Docker huérfanas (`ddev clean`).
  - Acceso al panel de enrutamiento Traefik Router.

---

## 📦 Requisitos Previos

Antes de instalar DDEV Studio, asegúrate de tener instalado:

1. **Docker / Docker Desktop / Docker Engine**
2. **DDEV** (Versión 1.23 o superior):
   ```bash
   curl -fsSL https://ddev.com/install.sh | bash
   ```
3. **Python 3 y dependencias de GTK3 (Ubuntu / Debian / Linux Mint):**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-gi gir1.2-gtk-3.0
   ```

---

## 🚀 Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/mayc1030/ddev-studio.git
   cd ddev-studio
   ```

2. Ejecuta el instalador automático:
   ```bash
   ./install.sh
   ```

El instalador:
- Copiará los archivos a `~/.local/share/ddev-manager`.
- Creará el comando CLI global `ddev-gui`.
- Registrará los accesos directos en tu **Escritorio** y en el **Menú de Aplicaciones** (en la categoría *Desarrollo / Programación*).

---

## 💻 Formas de Uso

Puedes iniciar **DDEV Studio** de 3 maneras:

1. **Desde la Terminal:**
   ```bash
   ddev-gui
   ```
2. **Desde el Menú de Aplicaciones:** Busca **DDEV Studio** en la sección *Desarrollo / Programación*.
3. **Desde el Escritorio:** Doble clic en el icono **DDEV Studio**.

---

## 📂 Estructura del Proyecto

```text
ddev-studio/
├── ddev_manager.py       # Núcleo de la aplicación en Python 3 + GTK3
├── icons/                # Iconos SVG de tecnologías soportadas
│   ├── angular.svg
│   ├── ddev.svg
│   ├── django.svg
│   ├── drupal.svg
│   ├── flask.svg
│   ├── laravel.svg
│   ├── php.svg
│   ├── react.svg
│   ├── symfony.svg
│   ├── vue.svg
│   └── wordpress.svg
├── ddev-studio.desktop   # Archivo de integración con el escritorio Linux
├── install.sh            # Script de instalación automática
├── uninstall.sh          # Script de desinstalación limpia
├── .gitignore            # Exclusiones de Git
├── LICENSE               # Licencia MIT
└── README.md             # Documentación oficial del proyecto
```

---

## 🗑️ Desinstalación

Para desinstalar DDEV Studio limpiamente de tu sistema:
```bash
./uninstall.sh
```

---

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Si deseas agregar soporte para nuevos frameworks, optimizaciones o mejoras visuales:
1. Haz un Fork del repositorio.
2. Crea una rama para tu feature (`git checkout -b feature/nueva-receta`).
3. Haz commit de tus cambios (`git commit -m 'feat: soporte para nuevo framework'`).
4. Haz Push a la rama (`git push origin feature/nueva-receta`).
5. Abre un **Pull Request**.

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.
