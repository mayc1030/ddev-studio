# -*- coding: utf-8 -*-
"""
Motor de orquestación de creación e importación de proyectos en DDEV Studio.
Delega el aprovisionamiento de cada tecnología a su estrategia correspondiente (Strategy Pattern).
"""

import os
import re
import shutil
import subprocess
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

from ddev_studio.logger import logger
from ddev_studio.core.detector import sanitize_project_name
from ddev_studio.core.process import run_subproc
from ddev_studio.recipes.base import SITES_PHP_TEMPLATE, NGINX_FULL_PROXY_TEMPLATE
from ddev_studio.recipes.context import RecipeContext
from ddev_studio.recipes.registry import get_recipe
from ddev_studio.ui.dialogs.progress import ProgressDialog


def run_create_project(
    parent_window,
    raw_name,
    base_dir,
    clean_target_before,
    fw,
    drupal_ver_info,
    php_version,
    db_type,
    node_version,
    auto_install,
    is_multisite_enabled,
    on_success_callback=None
):
    """
    Ejecuta el flujo completo de creación y scaffolding para el framework seleccionado
    delegando a la estrategia correspondiente en el registro de recetas.
    """
    slug = sanitize_project_name(raw_name)
    node_version = re.sub(r'[^\d]', '', str(node_version or '')) or "22"
    target_dir = os.path.join(base_dir, slug)
    fw_id = fw["id"]

    dialog_title = f"Creando {fw['name']}"
    if fw_id == "drupal":
        dialog_title = f"Creando Drupal {drupal_ver_info.get('id', '10')}: {slug}"
    else:
        dialog_title = f"Creando {fw['name']}: {slug}"

    dialog = ProgressDialog(parent_window, title=dialog_title)
    dialog.set_status(f"Iniciando creación de {dialog_title}...")

    primary_url = f"https://{slug}.ddev.site"

    ctx = RecipeContext(
        parent_window=parent_window,
        raw_name=raw_name,
        slug=slug,
        target_dir=target_dir,
        fw=fw,
        drupal_ver_info=drupal_ver_info,
        php_version=php_version,
        db_type=db_type,
        node_version=node_version,
        auto_install=auto_install,
        is_multisite_enabled=is_multisite_enabled,
        dialog=dialog,
        primary_url=primary_url,
        on_success_callback=on_success_callback
    )

    def run_creation():
        try:
            ctx.set_status("Limpiando contenedores anteriores si existen...")
            subprocess.run(["ddev", "delete", "-O", "-y", slug], capture_output=True)

            if clean_target_before and os.path.exists(target_dir):
                ctx.set_status("Vaciando carpeta de proyecto...")
                shutil.rmtree(target_dir, ignore_errors=True)

            os.makedirs(target_dir, exist_ok=True)

            ctx.log(f"📁 Directorio del proyecto: {target_dir}")
            ctx.log(f"🚀 Tecnología: {fw['name']}" + (f" (Versión {drupal_ver_info['id']})" if fw_id == 'drupal' else ""))

            db_label = "SQLite (Archivo local)" if db_type == "sqlite" else ("Ninguna" if db_type == "none" else db_type)
            if fw_id in ["nextjs", "react", "vue", "angular"]:
                ctx.log(f"📦 Entorno: Node.js (v{node_version}) | DB: {db_label}\n" + "="*50)
            elif fw_id in ["django", "flask"]:
                ctx.log(f"🐍 Entorno: Python 3 (Virtualenv) | DB: {db_label}\n" + "="*50)
            elif fw_id == "html":
                ctx.log(f"🌐 Entorno: HTML5 Estático (Nginx)\n" + "="*50)
            else:
                ctx.log(f"🐘 Versión de PHP: {php_version} | DB: {db_label}\n" + "="*50)

            recipe = get_recipe(fw_id)
            recipe.execute(ctx)

            ctx.log("\n" + "="*50)
            ctx.log(f"URL: {primary_url}")
            ctx.log("¡Completado con éxito!")
            GLib.idle_add(dialog.finish, True, f"¡Proyecto '{slug}' creado con éxito!", primary_url, target_dir)
            if on_success_callback:
                GLib.idle_add(on_success_callback)

        except Exception as e:
            logger.error(f"Error creando proyecto '{slug}': {e}", exc_info=True)
            ctx.log(f"\n❌ ERROR: {str(e)}")
            GLib.idle_add(dialog.finish, False, f"Error en la creación: {str(e)}", "", target_dir)

    threading.Thread(target=run_creation, daemon=True).start()


def run_import_project(
    parent_window,
    target_dir,
    slug,
    p_type,
    docroot,
    php_ver,
    node_ver,
    db_type,
    is_multisite,
    do_composer,
    on_success_callback=None
):
    """
    Ejecuta el flujo de importación y configuración de un proyecto local existente en DDEV.
    """
    slug = sanitize_project_name(slug or os.path.basename(target_dir.rstrip("/")))
    node_ver = re.sub(r'[^\d]', '', str(node_ver or '')) or "22"

    is_php = ("drupal" in p_type) or p_type in ["laravel", "php", "symfony", "wordpress"]
    is_node = p_type in ["angular", "react", "vue", "nextjs", "generic"]
    is_python = p_type in ["django", "flask"]

    dialog = ProgressDialog(parent_window, title=f"Importando Proyecto: {slug}")
    dialog.set_status(f"Configurando DDEV en {target_dir}...")

    def run_import():
        try:
            def log(text):
                GLib.idle_add(dialog.append_log, text + "\n")

            def set_st(st):
                GLib.idle_add(dialog.set_status, st)

            log(f"📁 Directorio base: {target_dir}")
            log(f"🚀 Tecnología: {p_type} | Docroot: {docroot}")
            if is_php:
                log(f"🐘 PHP: {php_ver} | BD: {db_type}")
            elif is_node:
                log(f"🟢 Node.js: v{node_ver} | BD: {db_type}")
            elif is_python:
                log(f"🐍 Python 3 + venv | BD: {db_type}")
            log("="*50)

            # 1. ddev config
            set_st("Configurando DDEV en el proyecto...")
            ddev_type = p_type
            if p_type in ["angular", "react", "vue", "nextjs", "django", "flask"]:
                ddev_type = "generic"
            elif p_type == "symfony":
                ddev_type = "php"

            cfg_cmd = [
                "ddev", "config",
                f"--project-name={slug}",
                f"--project-type={ddev_type}",
                f"--docroot={docroot}"
            ]

            if is_php:
                cfg_cmd.append(f"--php-version={php_ver}")
            elif is_node:
                cfg_cmd.append(f"--nodejs-version={node_ver}")
                if p_type == "angular":
                    cfg_cmd.append("--web-environment-add=NG_CLI_ANALYTICS=false")
            elif is_python:
                cfg_cmd.append("--webimage-extra-packages=python3-venv,python3-pip")

            if db_type == "none":
                cfg_cmd.append("--omit-containers=db")
            else:
                cfg_cmd.append(f"--database={db_type}")

            run_subproc(cfg_cmd, target_dir, dialog)

            # Daemon & Reverse Proxy for non-PHP stacks if needed
            daemon_map = {
                "django": (8000, "django-server", "/var/www/html/.venv/bin/python manage.py runserver 0.0.0.0:8000"),
                "flask": (5000, "flask-server", "/var/www/html/.venv/bin/python app.py"),
                "angular": (4200, "angular-dev-server", "npx ng serve --host 0.0.0.0 --port 4200 --allowed-hosts"),
                "nextjs": (3000, "nextjs-dev-server", "npm run dev"),
            }

            if p_type in daemon_map:
                port, daemon_name, daemon_cmd = daemon_map[p_type]
                nginx_full_dir = os.path.join(target_dir, ".ddev", "nginx_full")
                os.makedirs(nginx_full_dir, exist_ok=True)
                with open(os.path.join(nginx_full_dir, "nginx-site.conf"), "w", encoding="utf-8") as nf:
                    nf.write(NGINX_FULL_PROXY_TEMPLATE.format(port=port))
                with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w", encoding="utf-8") as df:
                    df.write(f"""#ddev-silent-no-warn
web_extra_daemons:
  - name: {daemon_name}
    command: "{daemon_cmd}"
    directory: /var/www/html
""")

            # 2. Dynamic sites.php if Drupal Multisite
            if is_multisite:
                set_st("Configurando enrutador dinámico Drupal Multisite...")
                sites_dir = os.path.join(target_dir, docroot, "sites") if docroot != "." else os.path.join(target_dir, "sites")
                os.makedirs(sites_dir, exist_ok=True)
                sites_php_file = os.path.join(sites_dir, "sites.php")
                if not os.path.exists(sites_php_file):
                    with open(sites_php_file, "w", encoding="utf-8") as sf:
                        sf.write(SITES_PHP_TEMPLATE)
                    log("✓ Archivo sites.php con mapeo dinámico multisite creado.")
                else:
                    log("✓ Archivo sites.php ya presente en el proyecto.")

            # 3. Start containers
            set_st("Iniciando contenedores DDEV...")
            run_subproc(["ddev", "start", "-y"], target_dir, dialog)

            # 4. Dependency install if requested and needed
            if do_composer:
                vendor_dir = os.path.join(target_dir, "vendor")
                composer_json = os.path.join(target_dir, "composer.json")
                if os.path.exists(composer_json) and not os.path.exists(vendor_dir):
                    set_st("Instalando dependencias de Composer...")
                    log("📦 Ejecutando 'ddev composer install'...")
                    run_subproc(["ddev", "composer", "install"], target_dir, dialog)
                    log("✓ Dependencias de Composer instaladas.")

                node_modules = os.path.join(target_dir, "node_modules")
                package_json = os.path.join(target_dir, "package.json")
                if os.path.exists(package_json) and not os.path.exists(node_modules) and not os.path.exists(composer_json):
                    set_st("Instalando dependencias de Node.js...")
                    log("📦 Ejecutando 'ddev npm install'...")
                    run_subproc(["ddev", "npm", "install"], target_dir, dialog)
                    log("✓ Dependencias de Node.js instaladas.")

                req_txt = os.path.join(target_dir, "requirements.txt")
                venv_dir = os.path.join(target_dir, ".venv")
                if os.path.exists(req_txt) and not os.path.exists(venv_dir):
                    set_st("Configurando entorno virtual Python e instalando dependencias...")
                    log("🐍 Creando .venv e instalando dependencias...")
                    run_subproc(["ddev", "exec", "python3 -m venv /var/www/html/.venv && /var/www/html/.venv/bin/pip install -r requirements.txt"], target_dir, dialog)
                    log("✓ Dependencias de Python instaladas.")

            primary_url = f"https://{slug}.ddev.site"
            log("\n" + "="*50)
            log(f"¡Proyecto '{slug}' importado y activado con éxito!")
            log(f"🌐 URL: {primary_url}")

            GLib.idle_add(dialog.finish, True, f"¡Proyecto '{slug}' listo!", primary_url, target_dir)
            if on_success_callback:
                GLib.idle_add(on_success_callback)

        except Exception as ex:
            logger.error(f"Error importando proyecto '{slug}': {ex}", exc_info=True)
            log(f"\n❌ ERROR: {str(ex)}")
            GLib.idle_add(dialog.finish, False, f"Error importando proyecto: {str(ex)}", "", target_dir)

    threading.Thread(target=run_import, daemon=True).start()
