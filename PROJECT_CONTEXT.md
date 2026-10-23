# 🧠 PROJECT_CONTEXT: DDEV Studio (Universal Architecture, Living Memory & Deep Code Map)

> **Documento Maestro de Contexto y Memoria Técnica Permanente**  
> *Este documento es la fuente única de verdad sobre la arquitectura completa, cada una de las vistas de la aplicación, el catálogo de add-ons, herramientas globales, monitor de recursos y el despliegue de los 11 frameworks soportados.*  
> **Regla Mandatoria:** Cualquier agente o desarrollador que agregue, modifique o elimine funcionalidades DEBE actualizar este archivo al finalizar su tarea.

---

## 1. Visión General del Proyecto

**DDEV Studio** es una aplicación de escritorio nativa para Linux desarrollada en **Python 3** y **GTK+ 3 (PyGObject)** con diseño moderno y soporte para temas oscuros/claros del sistema. Su objetivo es proporcionar una estación de trabajo gráfica completa, visual, rápida e intuitiva para crear, importar, inspeccionar, administrar y monitorear entornos de desarrollo contenerizados con **DDEV**, soportando un ecosistema políglota universal:

* 🐘 **PHP & CMSs:** Drupal (11, 10, 9, 8, 7 y Multisitio nativo), WordPress, Laravel, Symfony y PHP Plano / HTML.
* 🐍 **Python:** Django (PostgreSQL/MySQL/SQLite, virtualenvs, migraciones, superuser) y Flask.
* ⚛️ **Node.js & Frontend Moderno:** Next.js (App Router, Tailwind, TypeScript, Fast Refresh), Angular (@angular/cli, Vite dev server), React (Vite + TypeScript) y Vue 3 (Vite + TypeScript).
* 🗄️ **Bases de Datos & Add-ons:** MariaDB, MySQL, PostgreSQL, SQLite local, phpMyAdmin, Adminer, CloudBeaver (DBeaver Web), Redis, Solr, Elasticsearch, etc.
* 🛠️ **DevOps & Monitoreo:** Monitor de métricas Docker en tiempo real (CPU, RAM, red, E/S), generador de flujos CI/CD para GitHub Actions, conmutador de Xdebug con 1 clic, respaldos de BD y terminales nativas del sistema.

---

## 2. Arquitectura del Sistema (Separación Estricta de Responsabilidades - SoC)

El proyecto sigue una estricta separación entre Lógica de Negocio, Capa de Datos y UI (definida en `.agents/rules/buenas-practricas-desarrollo.md`):

```
ddev_studio/
├── constants.py          # Tokens de diseño, estilos CSS, paletas, frameworks y metadatos
├── logger.py             # Sistema de logs centralizado (--debug / DDEV_STUDIO_DEBUG=1)
├── main.py               # Punto de entrada de la aplicación GTK
├── core/                 # LÓGICA DE NEGOCIO Y OPERACIONES (CIEGA DE LA UI)
│   ├── detector.py       # Heurística de detección automática de tecnologías y configs DDEV
│   ├── framework_tools.py# Catálogo canónico y resolvedor de acciones contextuales por framework
│   ├── drupal_tools.py   # Lógica pura de Drupal (Drush generate, starterkit, APIs, uninstall)
│   ├── addons.py         # Catálogo y orquestación de complementos DDEV (DB, servicios, búsqueda)
│   ├── docker_monitor.py # Parsing y agregación de métricas Docker en tiempo real (CPU, RAM, E/S, red)
│   ├── ai_client.py      # Cliente REST local para Ollama (sin dependencias ML pesadas, HTTP nativo)
│   ├── ssl_tools.py      # Diagnóstico y gestión de mkcert, certutil (libnss3-tools) y certificados HTTPS
│   ├── ci_templates.py   # Detección Git y generación de workflows GitHub Actions para DDEV
│   ├── process.py        # Ejecución segura de subprocesos
│   └── terminal.py       # Lanzador inteligente y sanitizado de emuladores de terminal Linux
├── recipes/              # PATRÓN ESTRATEGIA: CREACIÓN DESATENDIDA POR TECNOLOGÍA
│   ├── base.py           # Clase abstracta BaseRecipe (config, start, restart, nginx_proxy, daemons)
│   ├── registry.py       # Fábrica y registro central de recetas (_RECIPES)
│   ├── runner.py         # Orquestador asíncrono con reportes de progreso y logs
│   ├── context.py        # Objeto RecipeContext con parámetros unificados de ejecución
│   ├── php.py            # Recetas PHP: Drupal (7-11, Multisite), WordPress, Laravel, Symfony, PHP Plano
│   ├── python.py         # Recetas Python: Django y Flask (virtualenv aislado, Nginx reverse proxy)
│   └── node.py           # Recetas Node: Next.js, Angular, React, Vue (Nginx WebSocket proxy, daemons)
└── ui/                   # CAPA DE PRESENTACIÓN (UI GTK3 DESACOPLADA)
    ├── helpers.py        # Utilidades visuales, carga de iconos SVG/PNG y formateo
    ├── window.py         # Ventana principal, navegación por Gtk.Notebook y Gtk.Stack
    ├── views/            # Vistas principales
    │   ├── details.py        # Panel de inspección técnica, runtimes, credenciales DB, Xdebug, backups
    │   ├── new_project.py    # Asistente de creación e importación (switcher nueva descarga / importar)
    │   ├── tools.py          # Herramientas globales (poweroff, clean, traefik, monitor Docker)
    │   ├── addons.py         # Marketplace visual de add-ons oficiales y comunitarios DDEV
    │   ├── ai_assistant.py   # Pestaña Asistente IA Local: chat interactivo, onboarding Ollama y modelos
    │   ├── docker_monitor.py # Panel de monitoreo de métricas de contenedores en vivo
    │   ├── drupal_tools.py   # Suite especializada de herramientas Drush, APIs y temas Drupal
    │   └── subsites.py       # Gestor visual de Drupal Multisitio
    └── dialogs/          # Diálogos modales auxiliares (progreso, confirmación, CI/CD, DB containers, ssl_diag, drupal_uninstall)
```

---

## 3. Módulo "Mis Proyectos" & "Detalles del Proyecto"

La pestaña principal (`Mis Proyectos`) gestiona el ciclo de vida y la inspección profunda de cada proyecto:

### A. Listado de Proyectos (`ui/window.py`)
* **Detección en Vivo:** Ejecuta `ddev list -j` en segundo plano para obtener el listado estructurado de proyectos DDEV activos e inactivos.
* **Filtros Dinámicos:**
  * Barra de búsqueda reactiva por nombre o tecnología (`search-changed`).
  * Selector desplegable filtrable por tecnología con iconos SVG oficiales desde `icons/` (Drupal, WordPress, Laravel, Django, Next.js, etc.).
* **Tarjeta de Proyecto:** Cada proyecto se dibuja con su nombre, badge de estado (`running`, `stopped`, `paused`), badge de tecnología, URL HTTPS principal y botones de acción rápida:
  * **Iniciar / Detener:** Invocación asíncrona con control de proyectos ocupados (`busy_projects`) para evitar ejecuciones concurrentes o bloqueos de UI.
  * **Abrir Web:** Apertura en el navegador predeterminado mediante `webbrowser.open()`.
  * **Terminal:** Abre la terminal del sistema ubicada en la raíz del proyecto.
  * **Carpeta:** Abre el gestor de archivos local con `xdg-open`.
  * **Detalles:** Cambia al subpanel de detalles técnicos (`ProjectDetailsView`).
  * **Eliminar:** Diálogo de confirmación con opciones para eliminar registro o purgar base de datos (`ddev delete`).
  * **Atajos Contextuales:** Si el proyecto es Drupal, muestra el botón directo *"Asistente Drupal"* y, si tiene multisitio, el botón *"Subsitios"*.

### B. Vista de Detalles del Proyecto (`ui/views/details.py`)
Al seleccionar un proyecto, se activa `ProjectDetailsView` dentro del `Gtk.Stack`:
* **Inspección Técnica Profunda:** Ejecuta `ddev describe -j <proyecto>` para extraer puertos asignados, servicios de correo (Mailpit), bases de datos y runtimes.
* **Tarjeta de Base de Datos Local / Docker:**
  * **SQLite:** Si se detecta base de datos SQLite (ej. Laravel o Django sin contenedor DB), reporta 0 MB de consumo de RAM en Docker, ruta exacta del archivo `.sqlite` y su tamaño.
  * **MariaDB / MySQL / PostgreSQL:** Muestra Host (`127.0.0.1`), Puerto Externo publicado, usuario, contraseña, nombre de BD y botón para copiar la cadena de conexión completa con 1 clic (`mysql -h 127.0.0.1 -P ...`).
  * **Gestores Web de BD:** Detecta si el proyecto tiene instalado **phpMyAdmin** (puerto 8037), **Adminer** (puerto 9101) o **CloudBeaver / DBeaver** (puerto 8979) y ofrece botón para abrirlos en el navegador o instalarlos con 1 clic.
* **Control de Xdebug en Tiempo Real:**
  * Consulta en vivo el estado con `ddev xdebug status`.
  * Muestra conmutador visual `ON / OFF` que ejecuta `ddev xdebug on` o `ddev xdebug off` sin reiniciar el contenedor.
* **Respaldos de Base de Datos:**
  * **Exportar BD:** Abre selector nativo de guardado y ejecuta `ddev export-db --file=<ruta.sql.gz>` en background con barra de progreso.
  * **Importar BD:** Abre selector de archivos `.sql`, `.sql.gz`, `.tar.gz` o `.zip`, solicita confirmación por seguridad y ejecuta `ddev import-db --file=<ruta>` con recarga automática.
* **Integración CI/CD:** Detecta si el proyecto tiene repositorio Git (`.git`) y flujos existentes en `.github/workflows/`, permitiendo generar plantillas de GitHub Actions adaptadas a la tecnología.
* **Framework Developer Toolkits (`core/framework_tools.py`):**
  * Detección canónica de la tecnología (Laravel, Django, WordPress, Symfony, Frontend SPA / Node.js, Python genérico, PHP genérico).
  * Renderizado reactivo en `ProjectDetailsView` con tarjeta dedicada (`Framework Developer Toolkit`), icono oficial SVG y FlowBox de botones con feedback visual (`.btn-quick`, `.btn-quick-cache`, `.btn-quick-term`):
    * **Laravel (Artisan):** `php artisan migrate`, `migrate:status`, `optimize:clear`, `route:list`, REPL interactivo `tinker` y `composer dump-autoload`.
    * **Django (manage.py):** `manage.py migrate`, `makemigrations`, `showmigrations`, `collectstatic`, consola interactiva `createsuperuser` y `shell`.
    * **WordPress (WP-CLI):** `wp cache flush`, `wp plugin list`, `wp plugin update --all`, `wp rewrite flush`, `wp core update` y REPL `wp shell`.
    * **Symfony (Console):** `cache:clear`, `doctrine:migrations:migrate`, `debug:router` y consola interactiva `bin/console`.
    * **Frontend SPA / Node.js:** `npm install`, `npm run build`, `npm test` y consola interactiva `ddev npm`.
    * **Python Genérico (Flask, FastAPI):** `pip list`, `pip install -r requirements.txt` y terminal interactiva `ddev exec python`.
    * **PHP Genérico:** `composer install`, `composer update` e instalación/dump optimizado de autoload.
  * Invocación segura no bloqueante: tareas de terminal se abren en el emulador del sistema mediante `open_terminal()`, y tareas de proceso ejecutan en segundo plano vía `ProgressDialog` con streaming en tiempo real y detección de código de retorno. Deshabilitación inteligente con tooltip descriptivo cuando el contenedor está detenido.
* **Herramientas Universales DDEV:**
  * Tarjeta presente en todos los proyectos (incluyendo Drupal): `📜 Ver Logs en Vivo` (`ddev logs -f`), `💻 Shell Web` (`ddev ssh`) y `📊 Inspección DDEV` (`ddev describe`).

---

## 4. Módulo "Nuevo Proyecto" (Creación Desatendida & Detección Heurística)

La vista `NewProjectView` (`ddev_studio/ui/views/new_project.py`) cuenta con un selector en cápsula segmentada para conmutar entre dos modos:

### Modo 1: Descargar Proyecto Nuevo (Patrón Estrategia - 11 Tecnologías)
1. 💧 **Drupal (11, 10, 9, 8, 7 y Multisitio):** Descarga vía Composer con `drupal/recommended-project`, instala Drush (`drush/drush`), ejecuta `drush site:install standard` (`admin/admin`) y opcionalmente inyecta `sites.php` para multisitio.
2. 🌐 **WordPress:** Descarga del core con `ddev wp core download` y ejecución desatendida de `ddev wp core install`.
3. 🔴 **Laravel:** `ddev composer create-project --prefer-dist laravel/laravel .`, soporte SQLite/MySQL/.env y migraciones automáticas (`php artisan migrate --force`).
4. 🎼 **Symfony:** Descarga con Composer (`symfony/skeleton`), instalación de `webapp-pack` y generación de `.env.local` con `DATABASE_URL`.
5. 🐘 **PHP Plano / HTML:** Generación de `index.php` moderno y estilizado con reporte de versión PHP.
6. 🐍 **Django:** Creación de `.venv`, instalación de dependencias (`django`, `psycopg2-binary`, `PyMySQL`), `django-admin startproject app .`, configuración de `ALLOWED_HOSTS = ['*']` y `DATABASES`, migraciones, superusuario `admin/admin`, **Reverse Proxy Nginx** hacia puerto 8000 y **Daemon** en `.ddev/config.daemon.yaml` ejecutando `runserver`.
7. 🧪 **Flask:** Creación de `.venv`, `pip install flask`, generación de `app.py` modular, **Reverse Proxy Nginx** hacia puerto 5000 y **Daemon** en segundo plano.
8. ⚛️ **Next.js:** `create-next-app@latest` con TypeScript, Tailwind CSS, App Router, ajuste del script dev a `-H 0.0.0.0 -p 3000`, **Reverse Proxy Nginx con WebSockets/HMR** y **Daemon** ejecutando `npm run dev`.
9. 🅰️ **Angular:** `@angular/cli new` con `--routing --style=css --skip-git --defaults`, `NG_CLI_ANALYTICS=false`, **Reverse Proxy Nginx** hacia puerto 4200 y **Daemon** con `ng serve --allowed-hosts`.
10. ⚛️ **React (Vite):** `create-vite` con plantilla `react-ts`, inyección de `vite.config.ts` (`allowedHosts: true`, HMR en puerto 443), **Reverse Proxy Nginx** hacia puerto 5173 y **Daemon** `npm run dev`.
11. 💚 **Vue 3 (Vite):** `create-vite` con plantilla `vue-ts`, inyección de `vite.config.ts` (HMR 443), **Reverse Proxy Nginx** hacia puerto 5173 y **Daemon** `npm run dev`.

### Modo 2: Importar Carpeta Existente (`core/detector.py`)
Al seleccionar una carpeta local en disco, la función `detect_project_details()` analiza la estructura:
* Si existe `.ddev/config.yaml`: procesa nombre, tipo, docroot, php_version, nodejs_version, base de datos y omit_containers.
* Si no existe `.ddev`: analiza archivos característicos (`artisan`, `wp-config.php`, `core/lib/Drupal.php`, `manage.py`, `app.py`, `angular.json`, `next.config.*`, `vite.config.*`), deduciendo automáticamente la tecnología, la versión de PHP o Node.js y la raíz web (`web`, `docroot`, `public`, `dist` o `.`).

---

## 5. Módulo "Herramientas" (Global Tools & CI/CD)

La pestaña `Herramientas` (`ddev_studio/ui/views/tools.py`) centraliza la gestión del ecosistema global de DDEV y Docker:

* 🛑 **Poweroff Global (`ddev poweroff`):** Detiene todos los contenedores de todos los proyectos activos liberando memoria y puertos.
* ▶️ **Iniciar Todos (`ddev start -a`):** Inicia en bloque todos los proyectos registrados.
* 🧹 **Limpiar DDEV (`ddev clean -y`):** Purga cachés locales, imágenes Docker intermedias y archivos temporales.
* 🌐 **Panel Traefik Router:** Acceso directo con 1 clic al panel web del router de DDEV en `http://127.0.0.1:10999`.
* 🐳 **Detener Contenedores Externos (Docker):** Detiene selectivamente contenedores independientes que no pertenecen a DDEV (bases de datos independientes, microservicios, etc.) previa confirmación segura con vista previa de nombres e IDs.
* 🛑 **Detener TODO en Docker:** Ejecuta `ddev poweroff` y detiene simultáneamente todos los contenedores Docker externos activos con un reporte unificado.
* 🔒 **Diagnóstico y Reparación de Certificados SSL (mkcert & libnss3-tools):** Módulo `core/ssl_tools.py` y diálogo `ui/dialogs/ssl_diag.py` para verificar que `mkcert` y `certutil` estén instalados y registrados en los almacenes de confianza de Google Chrome, Chromium y Firefox, resolviendo el error `NET::ERR_CERT_AUTHORITY_INVALID` ("La conexión no es privada") de forma asistida.
* 📊 **Monitor de Docker Integrado:** Muestra el panel de métricas en tiempo real.
* ℹ️ **Versiones del Entorno:** Reporte dinámico en tiempo real de versiones instaladas de DDEV, Docker Engine, estado de confianza de certificados SSL y ruta predeterminada de proyectos (`~/sites`).
* 🚀 **Invocador Seguro de Terminales (`core/terminal.py`):** Detección automática en el PATH de emuladores de terminal Linux (`mate-terminal`, `gnome-terminal`, `xfce4-terminal`, `konsole`, `terminator`, `alacritty`, `kitty`, `x-terminal-emulator`, `xterm`) y sanitización estricta con `shlex.quote`.
* 🤖 **Generador de CI/CD (`core/ci_templates.py`):** Generador de workflows YAML para GitHub Actions probados en contenedor con matrices de PHP/Node, MySQL/Postgres y tests automatizados.

---

## 6. Módulo "Add-ons" (Marketplace & Gestión de Servicios)

La pestaña `Add-ons` (`ddev_studio/ui/views/addons.py` y `ddev_studio/core/addons.py`) permite extender cualquier proyecto con servicios adicionales contenerizados:

* **Catálogo Oficial y Comunitario:**
  * **Bases de Datos & Caché:** `ddev-redis`, `ddev-memcached`, `ddev-mongo`, `ddev-phpmyadmin`, `ddev-adminer`.
  * **Motores de Búsqueda:** `ddev-solr` (Apache Solr para Drupal Search API y WP), `ddev-elasticsearch`.
  * **DevOps & Colas:** `ddev-cron` (ejecución periódica en contenedor web), `ddev-rabbitmq` (AMQP con panel web).
  * **Frontend & DX:** `ddev-browsersync` (recarga en vivo de estilos y scripts).
  * **Testing & QA:** `ddev-selenium-standalone-chrome` (E2E con Chrome), `ddev-playwright`.
* **Filtros por Categoría:** Pestañas visuales: *Todos, Oficiales, Bases de Datos & Caché, Búsqueda, Frontend & DX, DevOps, Testing, Contrib* e *Instalados en este proyecto*.
* **Inspección de Add-ons Instalados:** Revisa `.ddev/docker-compose.<addon>.yaml` y metadatos en `.ddev/addon-metadata/`.
* **Operaciones:**
  * **Instalar:** Ejecuta `ddev get <addon>` seguido de `ddev restart` mostrando logs en vivo en un `ProgressDialog`.
  * **Desinstalar:** Ejecuta `ddev addon remove <addon>` o limpia las configuraciones asociadas y reinicia el proyecto.

---

## 7. Módulo "Monitor de Docker en Tiempo Real"

Implementado en `ddev_studio/core/docker_monitor.py` y `ddev_studio/ui/views/docker_monitor.py`:

* **Recolección de Métricas:** Consulta periódica mediante hilo en segundo plano ejecutando `docker stats --no-stream --format '{{json .}}'`.
* **Métricas Extraídas:**
  * **CPU %:** Porcentaje de CPU usado por contenedor con barra de progreso visual.
  * **Memoria:** Bytes consumidos, límite total disponible y porcentaje de uso (`MiB / GiB`).
  * **Red I/O:** Tráfico de red entrante y saliente (`B, KiB, MiB`).
  * **Disco I/O (Block I/O):** Lectura y escritura en disco.
* **Filtros de Ámbito Dinámicos:**
  * `🌐 Vista Global (Todos los contenedores)`
  * `📦 Todos los Proyectos DDEV`
  * `⚙️ DDEV Sistema (Router, SSH-Agent)`
  * `🐳 Otros Contenedores / Externos (No DDEV)` (aisla el consumo de contenedores independientes)
  * Proyectos DDEV específicos.
* **Menú Contextual (Clic Derecho en la Tabla):**
  * ⏹️ **Detener Contenedor:** Ejecuta `docker stop <id>`.
  * 🔄 **Reiniciar Contenedor:** Ejecuta `docker restart <id>`.
  * 📋 **Ver Logs Recientes:** Abre visor modal con las últimas 150 líneas de `docker logs`.
  * 💻 **Abrir Terminal (docker exec):** Lanza una consola interactiva `sh` / `bash` dentro del contenedor.
* **Optimización de Recursos (Battery / CPU Saver):** El polling se pausa automáticamente cuando el usuario cambia de pestaña y se reanuda al volver a la vista de Herramientas.

---

## 8. Módulo "Drupal Suite & Multisitio"

Especialización profunda para Drupal en `ddev_studio/ui/views/drupal_tools.py`, `ddev_studio/ui/views/subsites.py` y `ddev_studio/core/drupal_tools.py`:

* **Generador de Código (Drush Generate):** Asistente visual para módulos custom, controladores (`ControllerBase`), formularios (`FormBase`), servicios en `.services.yml` y plugins `@RestResource`.
* **Generador de Temas Starterkit & Presets:**
  * Detección dinámica de `vendor/bin/dr` vs `php core/scripts/drupal generate-theme` para Drupal 10/11.
  * Presets guiados para subtemas populares: **Olivero**, **Bootstrap 5**, **Bootstrap Barrio**, **Radix (SDC)**, **Gin Admin**, **Claro** y **Bartik/Classy** con require automático de paquetes vía Composer.
* **Suite de APIs & Estado de Módulos (Instalación y Desinstalación Individual o por Paquetes):**
  * Consulta en vivo del estado de extensiones mediante `drush pm:list --status=enabled --format=json`.
  * Catálogo canónico desacoplado en `DRUPAL_ESSENTIAL_BUNDLES` con generadores de comandos `build_module_install_command`, `build_module_uninstall_command` y `build_bundle_install_command`.
  * Soporte dual de instalación: en lote (paquete completo) e individual ("uno a uno") con Composer y Drush (`pm:enable` y `cr`).
  * Matriz visual responsiva en `Gtk.FlowBox` con estados dinámicos (`✔ Activo` / `○ Inactivo`), botones de instalación individual (`⬇ Instalar`), y flujo dual de desinstalación con modal inteligente (`DrupalUninstallDialog`): opción directa por Drush CLI (`pm:uninstall` y `cr` con control y reporte seguro de dependencias) y opción asistida web en Drupal (`/admin/modules/uninstall#edit-uninstall-<modulo>`), respetando multisitio (`--uri`).
* **Drupal Multisitio Nativo:**
  * Gestión de subsitios en `sites/<subsitio>`.
  * Sincronización atómica de dominios en `.ddev/config.yaml` (`additional_fqdns`).
  * Inyección y mantenimiento de `sites/sites.php`.
  * Base de datos dedicada por subsitio (`subsite_db`).
  * Invocación contextual de comandos Drush respetando `--uri=<subsitio_url>`.

---

## 9. Módulo "Asistente IA Local (Ollama)"

Implementado en `ddev_studio/core/ai_client.py` y `ddev_studio/ui/views/ai_assistant.py`:

* **Aislamiento Arquitectónico & Zero ML Bloat:**
  * No añade dependencias de PyTorch, HuggingFace ni bibliotecas pesadas de Python.
  * Se comunica exclusivamente mediante HTTP/REST con el daemon local de **Ollama** (`http://localhost:11434`) usando `urllib.request` y `json` estándar.
  * Si Ollama no está instalado o detenido, la aplicación funciona al 100% sin ninguna degradación.
* **Flujo Asistido de Onboarding (3 Estados Reactivos en `Gtk.Stack`):**
  * `onboarding`: Si `ollama` no se detecta en el sistema o no está en ejecución, muestra instrucciones claras y botón de 1 clic para instalar (`curl -fsSL https://ollama.com/install.sh | sh`) o iniciar el servicio (`systemctl start ollama`).
  * `no_models`: Si Ollama está activo pero no hay ningún modelo descargado, presenta un catálogo de modelos recomendados para descargar con un solo clic.
  * `chat`: Interfaz de conversación lista para responder cualquier consulta general o técnica.
* **Catálogo Integrado de Modelos Recomendados:**
  * `llama3.2:3b` (2.0 GB): Ideal para consultas generales, redacción técnica y explicaciones en español.
  * `qwen2.5:3b` (2.3 GB): Sobresaliente en DevOps, Docker, redes, comandos Linux y código.
  * `qwen2.5-coder:1.5b` (1.0 GB): Ultra rápido y liviano, apto para hardware con recursos limitados.
  * `phi3.5:3.8b` (2.2 GB): Razonamiento didáctico avanzado de Microsoft.
* **Interfaz de Chat Profesional & UX:**
  * Burbujas de chat estilizadas mediante CSS personalizado (`.chat-bubble-user`, `.chat-bubble-ai`, `.chat-code-block`).
  * Detección de bloques de código Markdown (\`\`\`) con botón para copiar al portapapeles con 1 clic.
  * Desplazamiento automático (`autoscroll`) inteligente hacia el último mensaje.
  * Campo de entrada multilínea con atajo `Ctrl+Enter` para enviar rápidamente y botón de parada/cancelación (`cancel_event`).
  * Inyección opcional y conmutable de contexto del proyecto activo (tecnología, docroot, estado y URL) como `system_prompt` para respuestas orientadas al proyecto.

---

## 10. Registro de Cambios Recientes (Changelog de Contexto)

| Commit / Versión | Tipo | Descripción | Componentes Afectados |
| *Actual* | `legal/feat` | Transición a Licencia Apache 2.0 con archivo `NOTICE` y atribución obligatoria a Maycol Sanchez Salazar (`mayc1030@gmail.com`), permitiendo uso y venta comercial con reconocimiento mandatorio de autoría en GUI y documentación | `LICENSE`, `NOTICE`, `README.md`, `ui/window.py` (Gtk.AboutDialog) |
| `3a53b50` | `feat` | Asistente IA local Ollama, Framework Developer Toolkits, diagnóstico SSL, desinstalación de módulos Drupal y 108 pruebas | `core/`, `ui/`, `tests/`, `docs/`, `PROJECT_CONTEXT.md`, `README.md` |
| `3a53b50` | `docs/feat` | Manual Oficial de Usuario y Arquitectura Técnica en PDF (`docs/manual/manual_ddev_studio.pdf`, `manual_ddev_studio.html`) con 20 capturas de pantalla de alta fidelidad (`docs/generate_screenshots.py`), 21 secciones arquitectónicas centradas en funcionalidades, sin sección de instalación externa | `docs/manual/`, `docs/generate_screenshots.py`, `ui/dialogs/ci_dialog.py`, `ui/dialogs/progress.py` |
| `3a53b50` | `fix` | Soporte para elevación de privilegios gráfica con PolicyKit (`pkexec`) y botón alternativo "Instalar en Terminal" para la instalación de Ollama, resolviendo el bloqueo `sudo: a terminal is required` | `core/ai_client.py`, `ui/views/ai_assistant.py`, `tests/test_ai_client.py`, `tests/test_smoke.py` |
| `3a53b50` | `feat` | Módulo desacoplado de Asistente IA Local ("Asistente IA") integrado en Gtk.Notebook junto a Add-ons: cliente Ollama nativo HTTP, onboarding de instalación guiada en 1 clic, catálogo de modelos recomendados (Llama 3.2, Qwen 2.5, Phi 3.5), streaming en tiempo real, bloques de código con copia al portapapeles e inyección contextual opcional del proyecto activo | `core/ai_client.py`, `ui/views/ai_assistant.py`, `ui/window.py`, `constants.py`, `tests/test_ai_client.py`, `tests/test_smoke.py` |
| `3a53b50` | `feat` | Desinstalación directa por CLI (`drush pm:uninstall` y `cr`) con diálogo modal inteligente (`DrupalUninstallDialog`), preservación de la vía web asistida, soporte para multisitio (`--uri`) y control preventivo de dependencias | `core/drupal_tools.py`, `ui/dialogs/drupal_uninstall.py`, `ui/views/drupal_tools.py`, `tests/test_drupal_tools.py`, `tests/test_smoke.py` |
| `3a53b50` | `feat` | Acciones contextuales por framework en la vista de Detalles (`Framework Developer Toolkits` para Laravel, Django, WordPress, Symfony, Frontend SPA Node.js, Python genérico y PHP genérico) con etiquetas limpias (solo iconos GTK simbólicos nativos, sin prefijos de emojis), ejecución desacoplada (`ProgressDialog` / terminal) y herramientas universales DDEV | `core/framework_tools.py`, `ui/views/details.py`, `constants.py`, `tests/test_framework_tools.py`, `tests/test_smoke.py` |
| `3a53b50` | `refactor` | Eliminación de código muerto: remoción de `ddev_studio/ui/dialogs/drupal_tools.py` (1.133 líneas huérfanas) y actualización de imports en `tests/test_smoke.py` | `ui/dialogs/drupal_tools.py`, `tests/test_smoke.py` |
| `3a53b50` | `refactor` | Unificación visual de módulos Drupal: eliminación de la fila redundante de atajos de desinstalación inferiores, integrando la acción `Desinstalar` directamente dentro de cada tarjeta de módulo en la cuadrícula | `ui/views/drupal_tools.py`, `tests/test_smoke.py` |
| `3a53b50` | `feat` | Instalación individual ("uno a uno") y en lote de módulos en la Suite de APIs y Módulos Fundamentales de Drupal, con catálogo canónico en Core y FlowBox interactivo en UI | `core/drupal_tools.py`, `ui/views/drupal_tools.py`, `constants.py`, `tests/test_drupal_tools.py` |
| `3a53b50` | `feat` | Diagnóstico, validación y reparación guiada de certificados SSL (`mkcert` y `libnss3-tools`), diálogo modal dedicado, comprobación en instalador y estado en tiempo real | `core/ssl_tools.py`, `ui/dialogs/ssl_diag.py`, `ui/views/tools.py`, `install.sh`, `tests/test_ssl_tools.py` |
| `f45391a` | `feat` | Control y detención de contenedores Docker externos (no DDEV), menú contextual en monitor (stop, restart, logs, terminal) y botones globales | `core/docker_monitor.py`, `ui/views/tools.py`, `ui/views/docker_monitor.py`, `tests/test_docker_monitor.py` |
| `3a53b50` | `docs/context` | Mapeo exhaustivo y detallado de cada módulo del sistema: Mis Proyectos, Detalles, Nuevo Proyecto (11 frameworks), Herramientas, Add-ons, Docker Monitor y Drupal Multisitio | `PROJECT_CONTEXT.md` |
| `f8ab1c8` | `fix` | Corregir visibilidad de atajos de desinstalación en GTK liberando `no_show_all` | `ui/views/drupal_tools.py` |
| `c3e7cf3` | `feat` | Agregar atajos seguros de desinstalación por módulo en interfaz web de Drupal | `core/drupal_tools.py`, `ui/views/drupal_tools.py` |
| `eaece19` | `fix` | Resolver `AttributeError` en `on_execute_scaffold` y asegurar `present()` de `ProgressDialog` | `ui/views/drupal_tools.py` |
| `b7c7234` | `feat` | Presets guiados para subtemas populares (Bootstrap 5, Barrio, Radix, Gin, etc.) con Composer | `core/drupal_tools.py`, `ui/views/drupal_tools.py` |
| `0f40680` | `fix` | Soporte y detección automática de generación de temas para Drupal 8 y 9 | `core/drupal_tools.py` |
| `1e1ded7` | `fix` | Corregir generación de temas starterkit en Drupal 10/11 | `core/drupal_tools.py` |
| `ffd3fb7` | `refactor` | Encapsulación de arranque, control de `busy_projects` y estandarización de `ddev exec` | `core/`, `ui/window.py` |

---

## 11. Deuda Técnica Identificada & Hoja de Ruta

1. **Buscador / Filtro en Suite de Módulos Drupal:**  
   Añadir filtrado en tiempo real en la barra de herramientas de la Suite de Módulos & APIs de Drupal para localizar módulos rápidamente.
2. **Gestor Universal de Paquetes en GUI:**  
   Permitir buscar e instalar paquetes de Composer, npm o pip directamente desde una interfaz visual sin recurrir a la terminal.
