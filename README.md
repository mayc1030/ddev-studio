# 🚀 DDEV Studio

**DDEV Studio** es una estación de trabajo nativa (GUI) moderna, rápida y altamente modular diseñada para Linux (Ubuntu, Debian, Linux Mint, MATE, GNOME, XFCE) que te permite crear, importar, administrar, inspeccionar, acelerar y monitorear proyectos basados en **[DDEV](https://ddev.com)** con 1 solo clic.

![Linux](https://img.shields.io/badge/Linux-Ubuntu%20%7C%20Debian%20%7C%20MATE%20%7C%20GNOME-E95420?logo=linux&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![GTK3](https://img.shields.io/badge/GTK-3.0-4E9A06?logo=gnome&logoColor=white)
![DDEV](https://img.shields.io/badge/DDEV-v1.23+-0074D9?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-Passing%20(108%2F108)-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 🌟 Características Principales

### ⚡ Creación en 1 Clic con Patrón Estrategia (Strategy Pattern)
Arquitectura modular y desacoplada con recetas especializadas para **11 tecnologías**:
- 💧 **Drupal (11, 10, 9, 8, 7 y Multisitio):** Descarga vía Composer (`drupal/recommended-project`), instalación automática desatendida (`admin / admin`) y Drush integrado.
- 🌐 **WordPress:** Descarga automática del núcleo con WP-CLI, base de datos y usuario administrador preconfigurado.
- 🔴 **Laravel:** Instalación con Composer, estructura `public/`, soporte SQLite/.env automático y migraciones (`php artisan migrate --force`).
- 🐍 **Django (Python 3):** Scaffolding completo con `django-admin startproject`, entorno virtual aislado (`.venv`), soporte PostgreSQL/MySQL/SQLite, migraciones, superusuario (`admin / admin`), Nginx Reverse Proxy y daemon en segundo plano (`runserver`).
- 🧪 **Flask (Python 3):** Scaffolding modular con `app.py`, entorno virtual (`.venv`), Nginx Reverse Proxy (puerto 5000) y daemon.
- 🅰️ **Angular:** Generación con `@angular/cli`, compatibilidad Vite dev server, `--allowed-hosts`, reverse proxy Nginx (puerto 4200) y daemon.
- ⚛️ **Next.js (App Router):** `create-next-app` con TypeScript, Tailwind CSS, App Router, soporte Fast Refresh / WebSockets en Nginx Reverse Proxy (puerto 3000) y daemon.
- ⚛️ **React (Vite + TypeScript):** Scaffolding rápido con Vite, Fast Refresh y proxy a puerto expuesto (5173).
- 💚 **Vue 3 (Vite + TypeScript):** Plantilla moderna con Hot Module Replacement (HMR).
- 🎼 **Symfony:** Proyecto con Skeleton y bundle WebApp listo para producción.
- 🐘 **PHP Plano / HTML:** Entorno limpio para scripts PHP o maquetaciones rápidas.

---

### 📁 Importación Inteligente de Proyectos Existentes
- **Detección Heurística Automática:** Analiza carpetas locales y autodeduce la tecnología, la raíz web (`web`, `docroot`, `public`, `dist` o `.`), la versión de PHP o Node.js y la presencia de Drupal Multisitio.
- **Parsing Estructurado de `.ddev/config.yaml`:** Procesamiento con PyYAML y fallback tolerante a fallos para lectura de tipos, runtimes, omit_containers y bases de datos.
- **Selector de Modo en Nuevo Proyecto:** Alterna fluidamente entre `📦 Descargar Proyecto Nuevo` y `📁 Importar Carpeta Existente`.

---

### 🔍 Inspector Técnico Profundo & Control de Servicios
- **Panel de Detalles de Proyecto:** Inspección de runtimes (PHP, Python, Node.js), servidor web, docroot y dominios/URLs HTTPS registrados.
- **Credenciales y Conexión de Base de Datos:** Host `127.0.0.1`, puertos externos publicados, base de datos, usuario, contraseña y botón para copiar la cadena de conexión completa con 1 clic.
- **Soporte SQLite Inteligente:** Si el proyecto usa SQLite (Laravel o Django), reporta 0 MB de consumo de RAM en Docker y muestra la ruta del archivo `.sqlite` con su tamaño.
- **Gestores Visuales de BD en Docker:** Habilitación y apertura de **CloudBeaver (DBeaver Web)**, **phpMyAdmin** y **Adminer** con 1 clic.
- **Control de Xdebug en Tiempo Real:** Detección de estado en vivo y conmutador `ON/OFF` con 1 clic (`ddev xdebug on/off`).
- **Respaldo y Restauración de Base de Datos:** Exportación (`ddev export-db`) e importación (`ddev import-db`) con selector nativo y confirmaciones de seguridad.

---

### ⚡ Framework Developer Toolkits
Tarjeta dedicada en la vista de Detalles de Proyecto con acciones canónicas y feedback visual en tiempo real:
- **Laravel (Artisan):** `migrate`, `migrate:status`, `optimize:clear`, `route:list`, REPL interactivo `tinker` y `composer dump-autoload`.
- **Django (manage.py):** `migrate`, `makemigrations`, `showmigrations`, `collectstatic`, creación interactiva de superusuario y `shell`.
- **WordPress (WP-CLI):** `cache flush`, `plugin list`, `plugin update --all`, `rewrite flush`, `core update` y REPL `wp shell`.
- **Symfony (Console):** `cache:clear`, `doctrine:migrations:migrate`, `debug:router` y consola interactiva `bin/console`.
- **Frontend SPA / Node.js:** `npm install`, `npm run build`, `npm test` y consola interactiva `ddev npm`.
- **Python Genérico (Flask, FastAPI):** `pip list`, `pip install -r requirements.txt` y terminal `ddev exec python`.
- **PHP Genérico:** `composer install`, `composer update` y optimización de autoload.
- **Herramientas Universales DDEV:** `📜 Logs en Vivo` (`ddev logs -f`), `💻 Shell Web` (`ddev ssh`) e `📊 Inspección DDEV` (`ddev describe`).

---

### 🤖 Asistente IA Local Integrado (Ollama)
Nueva pestaña **"Asistente IA"** que añade inteligencia artificial local directamente en tu entorno de desarrollo:
- **Zero ML Bloat & Arquitectura Desacoplada:** Se comunica exclusivamente mediante HTTP/REST nativo con el daemon local de [Ollama](https://ollama.com) (`http://localhost:11434`), sin dependencias pesadas de Python (sin PyTorch ni HuggingFace).
- **Onboarding Guiado en 1 Clic:** Detecta si Ollama está instalado o iniciado; permite instalarlo con elevación gráfica (`pkexec`) o mediante terminal.
- **Catálogo de Modelos Recomendados:** Descarga con 1 solo clic modelos optimizados para desarrollo local:
  - `llama3.2:3b`: Consultas generales, explicaciones técnicas y redacción.
  - `qwen2.5:3b`: DevOps, Docker, redes, comandos Linux y código políglota.
  - `qwen2.5-coder:1.5b`: Ultra rápido y liviano, ideal para hardware con recursos limitados.
  - `phi3.5:3.8b`: Razonamiento avanzado de Microsoft.
- **Chat Interactivo & UX:** Burbujas de chat estilizadas, detección automática de bloques de código Markdown con botón de copia al portapapeles, atajo `Ctrl+Enter` para enviar e inyección contextual opcional del proyecto activo (tecnología, docroot, URLs y estado).

---

### 🔒 Diagnóstico y Certificados SSL Locales (mkcert & certutil)
- **Solución Asistida para Errores SSL:** Módulo `core/ssl_tools.py` y diálogo `ui/dialogs/ssl_diag.py` para diagnosticar y registrar certificados locales de `mkcert` en los almacenes NSS de Google Chrome, Brave, Chromium y Firefox.
- **Prevención de `NET::ERR_CERT_AUTHORITY_INVALID`:** Alerta y repara automáticamente la ausencia de `libnss3-tools` (`certutil`), asegurando que todos los dominios `.ddev.site` sean 100% confiables en tu navegador.

---

### 💧 Suite Drush & Módulos para Drupal
- **Generador de Código (Drush Generate):** Asistente visual para módulos custom, controladores, formularios, servicios y plugins `@RestResource`.
- **Generador de Temas Starterkit & Presets:** Generación automática con presets guiados para **Olivero**, **Bootstrap 5**, **Bootstrap Barrio**, **Radix (SDC)**, **Gin Admin**, **Claro** y **Bartik/Classy** con instalación de dependencias vía Composer.
- **Suite de Módulos & APIs:** Catálogo canónico con instalación en lote o individual ("uno a uno") de paquetes de Administración, SEO, Performance, Medios y APIs/Headless.
- **Desinstalación Segura Dual:** Modal inteligente (`DrupalUninstallDialog`) con opción de desinstalación directa por Drush CLI (`pm:uninstall` y `cr`) o navegación asistida al desinstalador web de Drupal, con soporte para Drupal Multisitio (`--uri`).
- **Drupal Multisitio Nativo:** Creación y administración visual de subsitios en `sites/<subsitio>`, sincronización atómica de `additional_fqdns`, inyección de `sites/sites.php` y base de datos independiente.

---

### 🐳 Monitor de Docker & Control de Contenedores Externos
- **Métricas en Tiempo Real:** Monitor numérico y visual de CPU %, consumo de memoria RAM (`MiB / GiB`), tráfico de red y operaciones de E/S en disco.
- **Filtros Dinámicos:** Vista global, proyectos DDEV, servicios del sistema DDEV (router/ssh-agent) y **contenedores externos no-DDEV**.
- **Control de Contenedores Independientes:** Detención selectiva de contenedores Docker externos (bases de datos independientes, microservicios) con vista previa de nombres e IDs.
- **Apagado Global Total:** Botón para ejecutar `ddev poweroff` y detener en paralelo todos los contenedores Docker externos activos.
- **Menú Contextual:** Detener, reiniciar, ver logs en vivo y abrir terminal interactiva en cualquier contenedor.

---

### 📖 Manual Oficial de Usuario y Arquitectura Técnica
El repositorio incluye documentación completa y profesional generada para desarrolladores y administradores de sistemas:
- **PDF de Alta Definición:** [`docs/manual/manual_ddev_studio.pdf`](docs/manual/manual_ddev_studio.pdf) con 21 secciones arquitectónicas y 20 capturas de pantalla de alta fidelidad.
- **Versión HTML:** [`docs/manual/manual_ddev_studio.html`](docs/manual/manual_ddev_studio.html).
- **Generador Automatizado de Capturas:** [`docs/generate_screenshots.py`](docs/generate_screenshots.py) para recrear todas las capturas visuales de la aplicación.

---

## 📦 Requisitos Previos

1. **Docker Engine / Docker Desktop:**
   ```bash
   # Instalación rápida oficial de Docker Engine:
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   ```

2. **DDEV** (Versión 1.23 o superior):
   ```bash
   curl -fsSL https://ddev.com/install.sh | bash
   ```

3. **Python 3, PyGObject, GTK3, PyYAML y Herramientas SSL (Ubuntu / Debian / Linux Mint):**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-gi gir1.2-gtk-3.0 python3-yaml libnss3-tools
   ```
   > 💡 **Nota sobre SSL/HTTPS en navegadores:** El paquete `libnss3-tools` provee `certutil`, necesario para que Google Chrome, Brave, Chromium y Firefox reconozcan automáticamente los certificados HTTPS locales generados por DDEV (`mkcert`), evitando el error `NET::ERR_CERT_AUTHORITY_INVALID` ("La conexión no es privada").

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
- Validará las herramientas SSL del sistema informando del estado de `mkcert` y `certutil`.
- Limpiará automáticamente instalaciones obsoletas de versiones anteriores.

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

El proyecto incluye una suite completa de **108 pruebas unitarias** que validan la robustez de la arquitectura:

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
├── PROJECT_CONTEXT.md              # Memoria técnica permanente y fuente única de verdad
├── icons/                          # Iconos SVG de tecnologías soportadas
├── docs/                           # Documentación oficial y manuales
│   ├── generate_screenshots.py     # Automatización de capturas de pantalla de la GUI
│   └── manual/                     # Manual de usuario en HTML y PDF con capturas HD
├── tests/                          # Suite de 108 pruebas automatizadas
│   ├── test_smoke.py               # Tests unitarios de importación, core, UI y recipes
│   ├── test_addons.py              # Tests de marketplace de add-ons
│   ├── test_docker_monitor.py      # Tests de monitor de recursos de contenedores
│   ├── test_drupal_tools.py        # Tests de scaffolding, suite Drush y desinstalación
│   ├── test_ai_client.py           # Tests de cliente REST HTTP de Ollama
│   ├── test_framework_tools.py     # Tests de toolkits por framework (Laravel, Django, etc.)
│   └── test_ssl_tools.py           # Tests de diagnóstico mkcert y libnss3-tools
├── ddev_studio/                    # Paquete modular principal
│   ├── __init__.py                 # Metadatos del paquete
│   ├── constants.py                # CSS, frameworks, versiones y rutas
│   ├── logger.py                   # Sistema unificado de logging estructurado
│   ├── main.py                     # Entrypoint de ejecución de la interfaz GTK
│   ├── core/                       # Lógica de negocio (desacoplada de la UI)
│   │   ├── ai_client.py            # Cliente REST local para Ollama (Zero ML Bloat)
│   │   ├── framework_tools.py      # Resolvedor de acciones canónicas por framework
│   │   ├── ssl_tools.py            # Diagnóstico y gestión de certificados HTTPS locales
│   │   ├── drupal_tools.py         # Lógica pura de Drupal (Drush, starters, paquetes)
│   │   ├── addons.py               # Catálogo y orquestación de complementos DDEV
│   │   ├── ci_templates.py         # Generación de flujos GitHub Actions CI/CD
│   │   ├── detector.py             # Detección heurística de proyectos e inspección YAML
│   │   ├── docker_monitor.py       # Monitoreo y parsing de métricas de Docker
│   │   ├── process.py              # Ejecutor de subprocess con streaming a GLib
│   │   └── terminal.py             # Integración segura con emuladores de terminal
│   ├── recipes/                    # Desacoplamiento de Recetas (Strategy Pattern)
│   │   ├── __init__.py             # Exportaciones públicas
│   │   ├── base.py                 # Clase abstracta BaseRecipe y utilidades
│   │   ├── context.py              # Encapsulamiento de RecipeContext
│   │   ├── node.py                 # Estrategias para Next.js, React, Vue y Angular
│   │   ├── php.py                  # Estrategias para Drupal, WordPress, Laravel, Symfony y PHP
│   │   ├── python.py               # Estrategias para Django y Flask
│   │   ├── registry.py             # Registro dinámico y fábrica de recetas (get_recipe)
│   │   └── runner.py               # Orquestador de creación e importación no bloqueante
│   └── ui/                         # Interfaz gráfica GTK 3
│       ├── helpers.py              # Carga de iconos y constructores de menú
│       ├── window.py               # Ventana principal (DDEVManagerWindow y Notebook)
│       ├── dialogs/                # Diálogos modales
│       │   ├── progress.py         # Diálogo de progreso con log en vivo
│       │   ├── db_containers.py    # Gestor de DBeaver, phpMyAdmin y Adminer
│       │   ├── ssl_diag.py         # Diálogo de diagnóstico y reparación SSL
│       │   ├── drupal_uninstall.py # Diálogo modal de desinstalación de módulos Drupal
│       │   └── ci_dialog.py        # Asistente de configuración CI/CD
│       └── views/                  # Vistas modulares desacopladas
│           ├── addons.py           # Marketplace de complementos y servicios oficiales
│           ├── ai_assistant.py     # Pestaña Asistente IA Local (Ollama)
│           ├── details.py          # Panel inspector, toolkits por framework y Xdebug
│           ├── docker_monitor.py   # Vista del monitor de rendimiento de contenedores
│           ├── drupal_tools.py     # Suite de herramientas avanzadas y Drush para Drupal
│           ├── new_project.py      # Asistente de creación e importación (NewProjectView)
│           ├── subsites.py         # Gestor visual de Drupal Multisitio
│           └── tools.py            # Herramientas globales del sistema (GlobalToolsView)
├── .agents/                        # Directivas y reglas arquitectónicas multiagente
│   └── rules/                      # Buenas prácticas de desarrollo y contexto vivo
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
