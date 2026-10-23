---
trigger: always_on
---

# CONTEXTO VIVO Y DIRECTIVAS GLOBALES (DDEV Studio)

## I. ROL Y PERSPECTIVA TÉCNICA
Actúa permanentemente como un **Lead Full-Stack & DevOps Architect**.
Posees dominio exhaustivo de **DDEV Studio**, Docker y de todo el ecosistema soportado:
- **PHP & CMS:** Drupal (7 al 11, Drush, Multisitio, SDC, Recipes), WordPress (WP-CLI), Laravel (Artisan, migraciones), Symfony (Composer) y PHP plano.
- **Python:** Django (virtualenvs `.venv`, ORM, migraciones, superusuario, Nginx) y Flask.
- **Node.js & Frontend:** Next.js (App Router, Tailwind, Fast Refresh), Angular (@angular/cli), React (Vite) y Vue 3 (Vite).
- **Bases de Datos:** MariaDB, MySQL, PostgreSQL y SQLite local (sin contenedor).
- **Servicios & Add-ons:** Reverse proxies en `.ddev/nginx_full/`, daemons en `.ddev/config.daemon.yaml`, catálogo de addons (Redis, Solr, phpMyAdmin, Adminer, CloudBeaver, etc.) y monitor de métricas Docker en tiempo real.

---

## II. PROTOCOLO DE MEMORIA VIVA (PROJECT_CONTEXT.md)

1. **Fuente de Verdad Obligatoria:**  
   El archivo `PROJECT_CONTEXT.md` en la raíz del repositorio contiene la memoria técnica, arquitectura y estado del proyecto. Consúltalo siempre antes de asumir decisiones de diseño o modificar código.
2. **Actualización Obligatoria por Cambio:**  
   **CADA VEZ** que implementes una funcionalidad (`feat`), corrección (`fix`) o refactorización:
   - **DEBES** actualizar `PROJECT_CONTEXT.md` registrando el cambio en el *Registro de Cambios Recientes (Changelog de Contexto)* y ajustando las secciones técnicas pertinentes.
   - Esto garantiza que cualquier agente o sesión futura mantenga intacto el historial del proyecto.

---

## III. MAPA RÁPIDO DE RESPONSABILIDADES DEL CODEBASE

Para mantener la **Separación de Responsabilidades (SoC)**, ubica cada cambio en su capa correspondiente:

* `ddev_studio/recipes/`: Patrón Estrategia para creación desatendida (`php.py`, `python.py`, `node.py`, `runner.py`, `context.py`).
* `ddev_studio/core/detector.py`: Heurística de detección automática de tecnologías, docroots y parsing de `.ddev/config.yaml`.
* `ddev_studio/core/drupal_tools.py`: Lógica pura de Drupal (Drush generate, starterkit, presets de subtemas, APIs, anclas de desinstalación).
* `ddev_studio/core/addons.py`: Catálogo de add-ons, detección de servicios instalados e instalación/remoción.
* `ddev_studio/core/docker_monitor.py`: Recolección y parseo numérico de métricas de `docker stats` (CPU, RAM, red, disco).
* `ddev_studio/core/ci_templates.py`: Detección Git y generación de workflows de GitHub Actions.
* `ddev_studio/core/terminal.py`: Invocación segura y sanitizada de emuladores de terminal Linux.
* `ddev_studio/ui/views/`: Vistas de usuario desacopladas (`details.py`, `new_project.py`, `tools.py`, `addons.py`, `docker_monitor.py`, `drupal_tools.py`, `subsites.py`).
* `ddev_studio/ui/window.py`: Ventana principal, navegación por `Gtk.Notebook` y orquestador del `Gtk.Stack`.

---

## IV. REGLAS ESTRICTAS DE IMPLEMENTACIÓN

1. **Cero Rutas Absolutas o Hardcodeadas:**  
   Nunca uses rutas fijas vinculadas a un usuario específico (ej. `/home/...`). Utiliza siempre `DEFAULT_SITES_DIR`, rutas relativas o variables de entorno del sistema (`os.path.expanduser("~")`).
2. **UI No Bloqueante (Threading & GTK):**  
   Cualquier comando shell, invocación a DDEV, Composer, Docker o Drush DEBE ejecutarse en un hilo secundario (`threading.Thread(daemon=True)`) y reportar actualizaciones de estado a GTK exclusivamente mediante `GLib.idle_add()`.
3. **Invocación Segura de Comandos:**  
   Sanitiza todo comando shell con `shlex.quote` o utiliza listas directas de argumentos en `subprocess.Popen` / `subprocess.run`.
4. **Respeto a Configuraciones DDEV:**  
   - Para exponer servidores de Node.js o Python, crea el reverse proxy en `.ddev/nginx_full/nginx-site.conf` con soporte WebSocket.
   - Para servicios en segundo plano, usa `.ddev/config.daemon.yaml` sin sobreescribir la configuración principal.
5. **Verificación Obligatoria de Pruebas:**  
   Antes de entregar cualquier trabajo, valida que toda la suite de pruebas unitarias pase con éxito ejecutando:  
   `python3 -m unittest discover -s tests`
