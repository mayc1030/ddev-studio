# -*- coding: utf-8 -*-
"""
Catálogo canónico y resolvedor de herramientas y comandos contextuales por framework
para DDEV Studio (Laravel, Django, WordPress, Symfony, Node/Frontend y utilidades comunes).
"""

import os


FRAMEWORK_TOOLKITS = {
    "laravel": {
        "id": "laravel",
        "icon": "laravel.svg",
        "title": "Laravel Developer Toolkit (Artisan)",
        "desc": "Herramientas de Artisan para migraciones, estado de esquemas, rutas, optimización y consola interactiva Tinker.",
        "tools": [
            {
                "id": "migrate",
                "label": "Ejecutar Migraciones",
                "icon": "system-run-symbolic",
                "cmd": ["ddev", "artisan", "migrate"],
                "type": "progress",
                "success_msg": "¡Migraciones de Laravel ejecutadas con éxito!",
                "tooltip": "Ejecutar las migraciones pendientes en la base de datos (php artisan migrate)",
            },
            {
                "id": "migrate_status",
                "label": "Estado de Migraciones",
                "icon": "view-list-symbolic",
                "cmd": ["ddev", "artisan", "migrate:status"],
                "type": "progress",
                "success_msg": "Estado de migraciones obtenido",
                "tooltip": "Ver qué migraciones se han ejecutado y cuáles están pendientes (php artisan migrate:status)",
            },
            {
                "id": "optimize_clear",
                "label": "Limpiar Caché & Optimizar",
                "icon": "edit-clear-all-symbolic",
                "cmd": ["ddev", "artisan", "optimize:clear"],
                "type": "progress",
                "success_msg": "¡Caché de Laravel optimizada y limpiada!",
                "tooltip": "Limpiar caché de rutas, configuración, vistas y eventos compilados (php artisan optimize:clear)",
            },
            {
                "id": "route_list",
                "label": "Listar Rutas",
                "icon": "format-indent-more-symbolic",
                "cmd": ["ddev", "artisan", "route:list"],
                "type": "progress",
                "success_msg": "Listado de rutas generado",
                "tooltip": "Listar todas las rutas registradas y controladores vinculados (php artisan route:list)",
            },
            {
                "id": "tinker",
                "label": "Consola Tinker",
                "icon": "utilities-terminal-symbolic",
                "cmd": "ddev artisan tinker",
                "type": "terminal",
                "tooltip": "Abrir terminal interactiva de Laravel Tinker (REPL en vivo)",
            },
            {
                "id": "composer_dump",
                "label": "Dump Autoload",
                "icon": "package-x-generic-symbolic",
                "cmd": ["ddev", "composer", "dump-autoload"],
                "type": "progress",
                "success_msg": "Autoload de Composer regenerado con éxito",
                "tooltip": "Regenerar el mapa de clases de Composer (composer dump-autoload)",
            },
        ],
    },
    "django": {
        "id": "django",
        "icon": "django.svg",
        "title": "Django Developer Toolkit (manage.py)",
        "desc": "Comandos de gestión Django para migraciones ORM, recolección de estáticos, superusuario y shell interactiva.",
        "tools": [
            {
                "id": "migrate",
                "label": "Aplicar Migraciones",
                "icon": "system-run-symbolic",
                "cmd": ["ddev", "exec", "python", "manage.py", "migrate"],
                "type": "progress",
                "success_msg": "¡Migraciones de Django aplicadas exitosamente!",
                "tooltip": "Sincronizar el estado de la base de datos con los modelos (python manage.py migrate)",
            },
            {
                "id": "makemigrations",
                "label": "Crear Migraciones",
                "icon": "document-new-symbolic",
                "cmd": ["ddev", "exec", "python", "manage.py", "makemigrations"],
                "type": "progress",
                "success_msg": "Nuevas migraciones generadas",
                "tooltip": "Generar nuevas migraciones según los cambios detectados en models.py (python manage.py makemigrations)",
            },
            {
                "id": "showmigrations",
                "label": "Ver Migraciones",
                "icon": "view-list-symbolic",
                "cmd": ["ddev", "exec", "python", "manage.py", "showmigrations"],
                "type": "progress",
                "success_msg": "Listado de migraciones obtenido",
                "tooltip": "Inspeccionar el estado de todas las aplicaciones y sus migraciones (python manage.py showmigrations)",
            },
            {
                "id": "collectstatic",
                "label": "Recolectar Estáticos",
                "icon": "folder-download-symbolic",
                "cmd": ["ddev", "exec", "python", "manage.py", "collectstatic", "--noinput"],
                "type": "progress",
                "success_msg": "¡Archivos estáticos recolectados con éxito!",
                "tooltip": "Recolectar archivos estáticos en STATIC_ROOT (python manage.py collectstatic --noinput)",
            },
            {
                "id": "createsuperuser",
                "label": "Crear Superusuario",
                "icon": "avatar-default-symbolic",
                "cmd": "ddev exec python manage.py createsuperuser",
                "type": "terminal",
                "tooltip": "Crear un superusuario interactivo para el panel de administración (/admin)",
            },
            {
                "id": "shell",
                "label": "Django Shell",
                "icon": "utilities-terminal-symbolic",
                "cmd": "ddev exec python manage.py shell",
                "type": "terminal",
                "tooltip": "Abrir terminal interactiva de Python con el entorno de Django cargado",
            },
        ],
    },
    "wordpress": {
        "id": "wordpress",
        "icon": "wordpress.svg",
        "title": "WordPress WP-CLI Developer Toolkit",
        "desc": "Gestión avanzada de WordPress con WP-CLI para caché de objetos, plugins, permalinks y actualizaciones del core.",
        "tools": [
            {
                "id": "cache_flush",
                "label": "Vaciar Caché (wp cache flush)",
                "icon": "edit-clear-all-symbolic",
                "cmd": ["ddev", "wp", "cache", "flush"],
                "type": "progress",
                "success_msg": "¡Caché de WordPress vaciada con éxito!",
                "tooltip": "Vaciar la caché de objetos y transitorios de WordPress (wp cache flush)",
            },
            {
                "id": "plugin_list",
                "label": "Listar Plugins",
                "icon": "view-list-symbolic",
                "cmd": ["ddev", "wp", "plugin", "list"],
                "type": "progress",
                "success_msg": "Listado de plugins obtenido",
                "tooltip": "Listar todos los plugins instalados y su estado (wp plugin list)",
            },
            {
                "id": "plugin_update",
                "label": "Actualizar Plugins",
                "icon": "software-update-available-symbolic",
                "cmd": ["ddev", "wp", "plugin", "update", "--all"],
                "type": "progress",
                "success_msg": "¡Plugins actualizados con éxito!",
                "tooltip": "Actualizar todos los plugins instalados a su versión más reciente (wp plugin update --all)",
            },
            {
                "id": "rewrite_flush",
                "label": "Regenerar Permalinks",
                "icon": "insert-link-symbolic",
                "cmd": ["ddev", "wp", "rewrite", "flush"],
                "type": "progress",
                "success_msg": "Reglas de reescritura de WordPress regeneradas",
                "tooltip": "Regenerar las reglas de reescritura de URL y permalinks (wp rewrite flush)",
            },
            {
                "id": "core_update",
                "label": "Actualizar Core",
                "icon": "system-software-update-symbolic",
                "cmd": ["ddev", "wp", "core", "update"],
                "type": "progress",
                "success_msg": "¡Núcleo de WordPress actualizado!",
                "tooltip": "Comprobar y actualizar el núcleo de WordPress a la versión más reciente (wp core update)",
            },
            {
                "id": "shell",
                "label": "WP-CLI Shell",
                "icon": "utilities-terminal-symbolic",
                "cmd": "ddev wp shell",
                "type": "terminal",
                "tooltip": "Abrir consola interactiva de PHP con WordPress inicializado (wp shell)",
            },
        ],
    },
    "symfony": {
        "id": "symfony",
        "icon": "symfony.svg",
        "title": "Symfony Console Developer Toolkit",
        "desc": "Comandos de la consola Symfony (bin/console) para depuración de rutas, caché y migraciones Doctrine.",
        "tools": [
            {
                "id": "cache_clear",
                "label": "Limpiar Caché",
                "icon": "edit-clear-all-symbolic",
                "cmd": ["ddev", "exec", "php", "bin/console", "cache:clear"],
                "type": "progress",
                "success_msg": "¡Caché de Symfony vaciada y reconstruida!",
                "tooltip": "Vaciar y calentar la caché del entorno actual (php bin/console cache:clear)",
            },
            {
                "id": "doctrine_migrate",
                "label": "Migraciones Doctrine",
                "icon": "system-run-symbolic",
                "cmd": ["ddev", "exec", "php", "bin/console", "doctrine:migrations:migrate", "--no-interaction"],
                "type": "progress",
                "success_msg": "¡Migraciones de Doctrine ejecutadas!",
                "tooltip": "Ejecutar las migraciones pendientes de base de datos con Doctrine",
            },
            {
                "id": "debug_router",
                "label": "Inspeccionar Rutas",
                "icon": "format-indent-more-symbolic",
                "cmd": ["ddev", "exec", "php", "bin/console", "debug:router"],
                "type": "progress",
                "success_msg": "Listado de rutas de Symfony generado",
                "tooltip": "Inspeccionar todas las rutas registradas y sus controladores (debug:router)",
            },
            {
                "id": "console",
                "label": "Consola Interactiva",
                "icon": "utilities-terminal-symbolic",
                "cmd": "ddev exec php bin/console",
                "type": "terminal",
                "tooltip": "Abrir la consola interactiva de Symfony en terminal",
            },
        ],
    },
    "frontend": {
        "id": "frontend",
        "icon": "nextjs.svg",
        "title": "Frontend SPA & Node.js Developer Toolkit",
        "desc": "Scripts de ciclo de vida del frontend: compilación de producción, dependencias y pruebas.",
        "tools": [
            {
                "id": "npm_install",
                "label": "Instalar Paquetes (npm install)",
                "icon": "software-update-available-symbolic",
                "cmd": ["ddev", "npm", "install"],
                "type": "progress",
                "success_msg": "¡Dependencias de npm instaladas exitosamente!",
                "tooltip": "Instalar dependencias declaradas en package.json (ddev npm install)",
            },
            {
                "id": "npm_build",
                "label": "Compilar (npm run build)",
                "icon": "system-run-symbolic",
                "cmd": ["ddev", "npm", "run", "build"],
                "type": "progress",
                "success_msg": "¡Compilación de producción completada!",
                "tooltip": "Generar build optimizado para producción (ddev npm run build)",
            },
            {
                "id": "npm_test",
                "label": "Pruebas / Linter",
                "icon": "checkbox-checked-symbolic",
                "cmd": ["ddev", "npm", "test"],
                "type": "progress",
                "success_msg": "Ejecución de pruebas/linter finalizada",
                "tooltip": "Ejecutar el script de pruebas configurado en package.json (ddev npm test)",
            },
            {
                "id": "npm_cli",
                "label": "Consola NPM",
                "icon": "utilities-terminal-symbolic",
                "cmd": "ddev npm",
                "type": "terminal",
                "tooltip": "Abrir terminal interactiva con el entorno Node.js/NPM del contenedor",
            },
        ],
    },
    "php_generic": {
        "id": "php_generic",
        "icon": "php.svg",
        "title": "PHP & Composer Developer Toolkit",
        "desc": "Gestión de paquetes Composer y utilidades para proyectos basados en PHP.",
        "tools": [
            {
                "id": "composer_install",
                "label": "Composer Install",
                "icon": "software-update-available-symbolic",
                "cmd": ["ddev", "composer", "install"],
                "type": "progress",
                "success_msg": "¡Dependencias de Composer instaladas!",
                "tooltip": "Instalar dependencias definidas en composer.lock o composer.json",
            },
            {
                "id": "composer_update",
                "label": "Composer Update",
                "icon": "system-software-update-symbolic",
                "cmd": ["ddev", "composer", "update"],
                "type": "progress",
                "success_msg": "¡Dependencias de Composer actualizadas!",
                "tooltip": "Actualizar paquetes de Composer según restricciones de versión",
            },
            {
                "id": "composer_dump",
                "label": "Dump Autoload",
                "icon": "package-x-generic-symbolic",
                "cmd": ["ddev", "composer", "dump-autoload"],
                "type": "progress",
                "success_msg": "Autoload de Composer optimizado",
                "tooltip": "Regenerar el mapa de clases optimizado de Composer",
            },
        ],
    },
    "python_generic": {
        "id": "python_generic",
        "icon": "python.svg",
        "title": "Python Developer Toolkit (Pip & WSGI)",
        "desc": "Gestión de paquetes pip y entorno interactivo para aplicaciones Flask, FastAPI o Python.",
        "tools": [
            {
                "id": "pip_list",
                "label": "Listar Paquetes (pip list)",
                "icon": "view-list-symbolic",
                "cmd": ["ddev", "exec", "pip", "list"],
                "type": "progress",
                "success_msg": "Listado de paquetes pip obtenido",
                "tooltip": "Ver las versiones de paquetes instalados en el entorno Python",
            },
            {
                "id": "pip_install",
                "label": "Instalar requirements.txt",
                "icon": "software-update-available-symbolic",
                "cmd": ["ddev", "exec", "pip", "install", "-r", "requirements.txt"],
                "type": "progress",
                "success_msg": "¡Paquetes de requirements.txt instalados con éxito!",
                "tooltip": "Instalar dependencias declaradas en requirements.txt",
            },
            {
                "id": "py_shell",
                "label": "Consola Python",
                "icon": "utilities-terminal-symbolic",
                "cmd": "ddev exec python",
                "type": "terminal",
                "tooltip": "Abrir intérprete interactivo de Python dentro del contenedor",
            },
        ],
    },
    "n8n": {
        "id": "n8n",
        "icon": "n8n.svg",
        "title": "n8n Automation Toolkit (Flujos y Webhooks)",
        "desc": "Herramientas de gestión para n8n: exportación de flujos, respaldo de credenciales y actualización.",
        "tools": [
            {
                "id": "export_workflows",
                "label": "Exportar Flujos (JSON)",
                "icon": "document-save-symbolic",
                "cmd": ["ddev", "exec", "npx", "n8n", "export:workflow", "--all", "--output=/var/www/html/workflows-backup.json"],
                "type": "progress",
                "success_msg": "¡Flujos exportados a workflows-backup.json con éxito!",
                "tooltip": "Exportar todos los flujos de trabajo de n8n a un archivo JSON local (n8n export:workflow --all)",
            },
            {
                "id": "export_credentials",
                "label": "Exportar Credenciales",
                "icon": "channel-secure-symbolic",
                "cmd": ["ddev", "exec", "npx", "n8n", "export:credentials", "--all", "--output=/var/www/html/credentials-backup.json"],
                "type": "progress",
                "success_msg": "¡Credenciales exportadas a credentials-backup.json con éxito!",
                "tooltip": "Exportar las credenciales configuradas en n8n a un archivo JSON seguro",
            },
            {
                "id": "update_n8n",
                "label": "Actualizar n8n",
                "icon": "software-update-available-symbolic",
                "cmd": ["ddev", "exec", "npm", "update", "n8n"],
                "type": "progress",
                "success_msg": "¡Plataforma n8n actualizada con éxito!",
                "tooltip": "Actualizar el paquete n8n a la última versión disponible (npm update n8n)",
            },
            {
                "id": "n8n_term",
                "label": "Terminal n8n CLI",
                "icon": "utilities-terminal-symbolic",
                "cmd": "ddev exec npx n8n",
                "type": "terminal",
                "tooltip": "Abrir terminal CLI para ejecutar comandos directos de n8n",
            },
        ],
    },
    "openclaw": {
        "id": "openclaw",
        "icon": "openclaw.svg",
        "title": "OpenClaw AI Agent Toolkit (Pasarela y Tareas)",
        "desc": "Herramientas de control e inspección para el agente autónomo OpenClaw y su conexión con Ollama.",
        "tools": [
            {
                "id": "openclaw_status",
                "label": "Estado del Agente",
                "icon": "system-run-symbolic",
                "cmd": ["ddev", "exec", "npx", "openclaw", "status"],
                "type": "progress",
                "success_msg": "Estado de OpenClaw obtenido",
                "tooltip": "Consultar estado de la pasarela y agentes de OpenClaw (npx openclaw status)",
            },
            {
                "id": "openclaw_onboard",
                "label": "Asistente Onboarding",
                "icon": "utilities-terminal-symbolic",
                "cmd": "ddev exec npx openclaw onboard",
                "type": "terminal",
                "tooltip": "Lanzar el asistente de configuración interactivo de OpenClaw (canales, LLM, credenciales)",
            },
            {
                "id": "update_openclaw",
                "label": "Actualizar OpenClaw",
                "icon": "software-update-available-symbolic",
                "cmd": ["ddev", "exec", "npm", "update", "openclaw"],
                "type": "progress",
                "success_msg": "¡OpenClaw actualizado con éxito!",
                "tooltip": "Actualizar el framework de OpenClaw a la versión más reciente (npm update openclaw)",
            },
            {
                "id": "openclaw_term",
                "label": "Terminal OpenClaw",
                "icon": "utilities-terminal-symbolic",
                "cmd": "ddev exec npx openclaw",
                "type": "terminal",
                "tooltip": "Abrir consola interactiva para el agente OpenClaw",
            },
        ],
    },
}


UNIVERSAL_TOOLS = [
    {
        "id": "logs",
        "label": "Ver Logs en Vivo",
        "icon": "text-x-generic-symbolic",
        "cmd": "ddev logs -f",
        "type": "terminal",
        "tooltip": "Seguir en tiempo real los registros de acceso y errores del contenedor web (ddev logs -f)",
    },
    {
        "id": "ssh",
        "label": "Shell Web (ddev ssh)",
        "icon": "utilities-terminal-symbolic",
        "cmd": "ddev ssh",
        "type": "terminal",
        "tooltip": "Entrar a la línea de comandos bash del contenedor web (ddev ssh)",
    },
    {
        "id": "describe",
        "label": "Inspección DDEV",
        "icon": "dialog-information-symbolic",
        "cmd": ["ddev", "describe"],
        "type": "progress",
        "success_msg": "Inspección de proyecto completada",
        "tooltip": "Obtener el reporte completo de puertos, URLs y servicios activos en DDEV",
    },
]


def get_framework_toolkit(tech_type: str, approot: str = "") -> dict | None:
    """
    Retorna el toolkit de framework correspondiente para el proyecto, adaptando
    el icono si se trata de un frontend específico (Next, React, Vue, Angular, etc.).
    """
    clean_tech = (tech_type or "").lower().strip()
    
    # 0. n8n & OpenClaw (Automatización & Agentes)
    if "n8n" in clean_tech or (approot and os.path.exists(os.path.join(approot, ".n8n"))):
        return FRAMEWORK_TOOLKITS["n8n"]
    if "openclaw" in clean_tech or (approot and os.path.exists(os.path.join(approot, ".openclaw"))):
        return FRAMEWORK_TOOLKITS["openclaw"]

    # 1. Laravel
    if "laravel" in clean_tech or (approot and os.path.exists(os.path.join(approot, "artisan"))):
        return FRAMEWORK_TOOLKITS["laravel"]
        
    # 2. Django
    if "django" in clean_tech or (approot and os.path.exists(os.path.join(approot, "manage.py"))):
        return FRAMEWORK_TOOLKITS["django"]
        
    # 3. WordPress
    if "wordpress" in clean_tech:
        return FRAMEWORK_TOOLKITS["wordpress"]
        
    # 4. Symfony
    if "symfony" in clean_tech:
        return FRAMEWORK_TOOLKITS["symfony"]
        
    # 5. Frontend SPA & Node.js
    frontend_keys = ["next", "react", "vue", "angular", "nuxt", "svelte", "astro", "node"]
    matched_fe = next((k for k in frontend_keys if k in clean_tech), None)
    if matched_fe or (approot and os.path.exists(os.path.join(approot, "package.json")) and not (approot and os.path.exists(os.path.join(approot, "composer.json")))):
        tk = dict(FRAMEWORK_TOOLKITS["frontend"])
        icon_cand = f"{matched_fe}.svg" if matched_fe in ["nextjs", "react", "vue", "angular"] else "nextjs.svg"
        if matched_fe == "next":
            icon_cand = "nextjs.svg"
        tk["icon"] = icon_cand
        fw_name = matched_fe.capitalize() if matched_fe else "Frontend"
        tk["title"] = f"{fw_name} Developer Toolkit (NPM / Node.js)"
        return tk

    # 6. Python genérico (Flask, FastAPI, Python plano)
    if any(k in clean_tech for k in ["python", "flask", "fastapi"]):
        tk = dict(FRAMEWORK_TOOLKITS["python_generic"])
        if "flask" in clean_tech:
            tk["icon"] = "flask.svg"
            tk["title"] = "Flask Developer Toolkit (Pip & Python)"
        return tk
        
    # 7. PHP genérico con Composer
    if "php" in clean_tech or (approot and os.path.exists(os.path.join(approot, "composer.json"))):
        # No aplicamos a Drupal aquí porque Drupal tiene su propio Studio completo
        if "drupal" not in clean_tech:
            return FRAMEWORK_TOOLKITS["php_generic"]

    return None


def get_universal_tools(tech_type: str = "", approot: str = "") -> list:
    """
    Retorna la lista de herramientas universales para desarrollo local en DDEV.
    """
    return list(UNIVERSAL_TOOLS)
