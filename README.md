# 🚀 DDEV Studio

**DDEV Studio** es una aplicación de escritorio nativa (GUI) moderna, rápida y altamente modular diseñada para Linux (Ubuntu, Debian, Linux Mint, MATE, GNOME, XFCE) que te permite crear, importar, administrar, inspeccionar y monitorear proyectos basados en **[DDEV](https://ddev.com)** con 1 solo clic.

![Linux](https://img.shields.io/badge/Linux-Ubuntu%20%7C%20Debian%20%7C%20MATE%20%7C%20GNOME-E95420?logo=linux&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![GTK3](https://img.shields.io/badge/GTK-3.0-4E9A06?logo=gnome&logoColor=white)
![DDEV](https://img.shields.io/badge/DDEV-v1.23+-0074D9?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-Passing%20(60%2F60)-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🌟 Características Principales

### ⚡ Creación en 1 Clic con Patrón Estrategia (Strategy Pattern)
Arquitectura modular y desacoplada con recetas especializadas para cada tecnología:
- 💧 **Drupal (Multisite & Standalone):**
  - Selector unificado para **Drupal 11, 10, 9, 8 y 7** con Composer y Drush.
  - Instalación desatendida automática (`admin / admin`).
  - **Soporte Avanzado para Drupal Multisite:** Gestión nativa de subsitios, bases de datos dedicadas por subsitio, sincronización atómica de FQDNs (`additional_fqdns`), `sites.php` dinámico y ejecución de Drush contextual por sitio.
- 🌐 **WordPress:** Descarga automática del núcleo con WP-CLI, base de datos y usuario administrador preconfigurado.
- 🔴 **Laravel:** Instalación con Composer, estructura `public/`, soporte SQLite/.env automático y `php artisan migrate`.
- 🐍 **Django (Python 3):**
  - Estructura inicial con `django-admin startproject`.
  - Aislamiento automático en entorno virtual (`.venv`) dentro del proyecto.
  - Conectores para MySQL (`PyMySQL`), PostgreSQL (`psycopg2-binary`) o SQLite.
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
- ⚛️ **Next.js (React Full-Stack / App Router):**
  - Scaffolding completo con `create-next-app` (TypeScript, Tailwind CSS, App Router, ESLint, alias `@/*`).
  - Nginx Reverse Proxy integrado con soporte para Fast Refresh / WebSockets en `https://<proyecto>.ddev.site`.
  - Servidor de desarrollo gestionado como daemon de fondo con Node.js 22 LTS.
- ⚛️ **React (Vite + TypeScript):** Scaffolding rápido con Vite, Fast Refresh y proxy a puerto expuesto.
- 💚 **Vue 3 (Vite + TypeScript):** Plantilla moderna con Hot Module Replacement (HMR).
- 🎼 **Symfony:** Proyecto con Skeleton y bundle WebApp listo para producción.
- 🐘 **PHP Plano / HTML:** Entorno limpio para scripts PHP o maquetaciones rápidas.

---

### 📁 Importación Inteligente de Proyectos Existentes
- **Detección Automática Heurística:** Analiza carpetas locales y autodetecta la tecnología (Drupal, WordPress, Laravel, Symfony, Django, Flask, Next.js, Angular, React, Vue, PHP), la raíz web (`docroot`, `public`, `web`, `dist`, etc.), la versión óptima de PHP y configuración de Drupal Multisite.
- **Parsing Estructurado de `.ddev/config.yaml`:** Procesamiento seguro con PyYAML y fallback tolerante a fallos para lectura de tipos, versiones de PHP, omit_containers y bases de datos.
- **Modo Switcher en Nuevo Proyecto:** Alterna fluidamente entre `📦 Descargar Proyecto Nuevo` y `📁 Importar Carpeta Existente`.

---

### 🔍 Inspector Técnico Profundo & Control de Servicios
- **Panel de Detalles de Proyecto:** Inspección exhaustiva de runtimes (PHP, Python, Node.js), servidor web, docroot y dominios/URLs HTTPS registrados.
- **Credenciales y Conexión Externa de Base de Datos:** Host `127.0.0.1`, puertos externos publicados, base de datos, usuario, contraseña y botón para copiar la cadena de conexión completa con 1 clic.
- **Gestores Visuales de BD en Contenedores Docker:**
  - Habilitación y gestión de **DBeaver (CloudBeaver)**, **phpMyAdmin** y **Adminer** como add-ons de DDEV con 1 clic.
- **Control de Xdebug en Tiempo Real:** Detección de estado en vivo y conmutador `ON/OFF` con 1 clic (`ddev xdebug on/off`).
- **Respaldo y Restauración de Base de Datos:** Exportación (`ddev export-db --file=...`) a `.sql.gz` e importación (`ddev import-db --file=...`) con selector nativo de archivos y confirmaciones de seguridad.

---

### 💧 Suite Drush Integrada para Drupal
- ⚡ **Limpieza de Caché Inmediata** (`drush cr` / `drush cc all`).
- 🔑 **Acceso Admin One-Time Login** (`drush uli`) con apertura automática en navegador.
- 🔄 **Actualización de Base de Datos** (`drush updatedb -y`).
- 📤 / 📥 **Exportación e Importación de Configuración** (`drush cex` / `drush cim`).
- ⏰ **Ejecución de Cron** (`drush cron`).
- 📊 **Diagnóstico del Sitio** (`drush status`) y **Visor de Logs** (`drush watchdog`).
- 🧩 **Módulos Habilitados** (`drush pm:list`).

---

### ⚙️ Arquitectura Robusta, Modular y Resiliente
- **Vistas Desacopladas:** Ventana principal modularizada separando `GlobalToolsView` (herramientas globales y monitor Docker) y `NewProjectView` (asistente de creación e importación).
- **Invocación Segura de Terminales:** Sanitización estricta con `shlex.quote` y soporte nativo para `gnome-terminal`, `mate-terminal`, `xfce4-terminal`, `konsole`, `terminator`, `alacritty`, `kitty` y `xterm`.
- **Sistema de Logging Estructurado:** Módulo centralizado `ddev_studio/logger.py` con formateo profesional (timestamp, módulo, línea) y bandera `--debug` / `DDEV_STUDIO_DEBUG=1`.
- **Nginx Reverse Proxy Automático (`.ddev/nginx_full/nginx-site.conf`):** Redirige transparentemente el tráfico HTTP/HTTPS y WebSockets para aplicaciones Node.js y Python hacia sus puertos internos (`8000`, `5000`, `4200`, `5173`, `3000`).
- **Configuraciones Modulares (`.ddev/config.daemon.yaml`):** Cero conflictos de sintaxis YAML o duplicación de claves en `.ddev/config.yaml`.
- **Monitor de Docker en Tiempo Real:** Medición de CPU, memoria, red y E/S de disco por contenedor.
- **Plantillas CI/CD:** Generación de workflows de GitHub Actions para pruebas automatizadas con DDEV.

---

## 📦 Requisitos Previos

1. **Docker Engine / Docker Desktop:**
   ```bash
   # Instalación rápida oficial de Docker Engine:
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   ```
   *(O mediante paquetes de Ubuntu/Debian: `sudo apt update && sudo apt install -y docker.io docker-compose-plugin && sudo usermod -aG docker $USER`)*

2. **DDEV** (Versión 1.23 o superior):
   ```bash
   curl -fsSL https://ddev.com/install.sh | bash
   ```
3. **Python 3, PyGObject, GTK3 y PyYAML (Ubuntu / Debian / Linux Mint):**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-gi gir1.2-gtk-3.0 python3-yaml
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
- Copiará el paquete `ddev_studio` y recursos a `~/.local/share/ddev-studio/`.
- Creará los comandos CLI globales `ddev-studio` y `ddev-gui` en `~/.local/bin/`.
- Registrará los accesos directos en tu **Escritorio** y en el **Menú de Aplicaciones** (en la categoría *Desarrollo / Programación*).
- Limpiará automáticamente instalaciones obsoletas previas de versiones anteriores.

---

## 💻 Formas de Uso

Puedes iniciar **DDEV Studio** de 3 maneras:

1. **Desde la Terminal:**
   ```bash
   ddev-studio             # Modo normal (o también: ddev-gui)
   ddev-studio --debug     # Modo diagnóstico con logging detallado
   ```
2. **Desde el Menú de Aplicaciones:** Busca **DDEV Studio** en la sección *Desarrollo / Programación*.
3. **Desde el Escritorio:** Doble clic en el icono **DDEV Studio**.

---

## 🧪 Pruebas Automatizadas

El proyecto incluye una suite completa de **60 pruebas unitarias** que validan la robustez de la arquitectura:

```bash
# Ejecutar todas las pruebas unitarias
python3 -m unittest discover -s tests -v

# Validar sintaxis y compilación de todo el proyecto
python3 -m py_compile ddev_manager.py ddev_studio/*.py ddev_studio/**/*.py tests/*.py
```

---

## 📂 Estructura del Proyecto

```text
ddev-studio/
├── ddev_manager.py                 # Launcher de compatibilidad raíz
├── install.sh                      # Script de instalación automática para Linux
├── uninstall.sh                    # Script de desinstalación limpia
├── icons/                          # Iconos SVG de tecnologías soportadas
├── tests/                          # Suite de pruebas automatizadas
│   ├── test_smoke.py               # Tests unitarios de importación, core, logger y recipes
│   ├── test_addons.py              # Tests de marketplace de add-ons
│   ├── test_docker_monitor.py      # Tests de monitor de recursos de contenedores
│   └── test_drupal_tools.py        # Tests de scaffolding y suite Drush
├── ddev_studio/                    # Paquete modular principal
│   ├── __init__.py                 # Metadatos del paquete
│   ├── constants.py                # CSS, frameworks, versiones de Drupal y rutas
│   ├── logger.py                   # Sistema unificado de logging estructurado
│   ├── main.py                     # Entrypoint de ejecución de la interfaz GTK
│   ├── core/                       # Lógica de bajo nivel
│   │   ├── ci_templates.py         # Generación de flujos GitHub Actions CI/CD
│   │   ├── detector.py             # Detección heurística de proyectos e inspección YAML
│   │   ├── docker_monitor.py       # Monitoreo de recursos y estadísticas de Docker
│   │   ├── process.py              # Ejecutor de subprocess con streaming a GLib
│   │   └── terminal.py             # Integración segura con emuladores de terminal
│   ├── recipes/                    # Desacoplamiento de Recetas (Strategy Pattern)
│   │   ├── __init__.py             # Exportaciones públicas
│   │   ├── base.py                 # Clase abstracta BaseRecipe y utilidades de configuración
│   │   ├── context.py              # Encapsulamiento de RecipeContext
│   │   ├── node.py                 # Estrategias para Next.js, React, Vue y Angular
│   │   ├── php.py                  # Estrategias para Drupal, WordPress, Laravel, Symfony y PHP
│   │   ├── python.py               # Estrategias para Django y Flask
│   │   ├── registry.py             # Registro dinámico y fábrica de recetas (get_recipe)
│   │   └── runner.py               # Orquestador de creación e importación no bloqueante
│   └── ui/                         # Interfaz gráfica GTK 3
│       ├── helpers.py              # Carga de iconos y constructores de menú
│       ├── window.py               # Ventana principal (DDEVManagerWindow)
│       ├── dialogs/                # Diálogos modales
│       │   ├── progress.py         # Diálogo de progreso con log en vivo
│       │   └── db_containers.py    # Gestor de DBeaver, phpMyAdmin y Adminer
│       └── views/                  # Vistas modulares desacopladas
│           ├── addons.py           # Marketplace de complementos y servicios oficiales
│           ├── details.py          # Panel inspector de proyecto y Xdebug
│           ├── docker_monitor.py   # Vista del monitor de rendimiento de contenedores
│           ├── drupal_tools.py     # Suite de herramientas avanzadas y Drush para Drupal
│           ├── new_project.py      # Asistente de creación e importación (NewProjectView)
│           ├── subsites.py         # Gestor de Drupal Multisite
│           └── tools.py            # Herramientas globales del sistema (GlobalToolsView)
├── .github/workflows/
│   └── ci.yml                      # Integración Continua con ejecución de tests
├── .gitignore                      # Exclusiones de Git
├── LICENSE                         # Licencia MIT
└── README.md                       # Documentación oficial del proyecto
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
