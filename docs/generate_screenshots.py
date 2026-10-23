# -*- coding: utf-8 -*-
"""
Script de generación automatizada de capturas de pantalla de alta fidelidad
para el Manual Oficial de DDEV Studio.
"""

import os
import sys

# Ensure ddev_studio can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import json
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib

from ddev_studio.constants import CUSTOM_CSS, DEFAULT_SITES_DIR
from ddev_studio.ui.window import DDEVManagerWindow
from ddev_studio.ui.dialogs.ssl_diag import SSLDiagDialog
from ddev_studio.ui.dialogs.ci_dialog import CIDialog
from ddev_studio.ui.dialogs.drupal_uninstall import DrupalUninstallDialog
from ddev_studio.ui.dialogs.progress import ProgressDialog
from ddev_studio.ui.views.docker_monitor import DockerMonitorView

SCREENSHOTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "manual", "screenshots"))
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def capture_window(win, filename, width=1100, height=760, delay=0.2, scroll_to_top=True):
    win.set_default_size(width, height)
    win.resize(width, height)
    win.show_all()
    
    # Process events
    for _ in range(6):
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(delay / 6)
        
    gdk_win = win.get_window()
    if not gdk_win:
        print(f"Error: GdkWindow not realized for {filename}")
        return False
        
    w = gdk_win.get_width()
    h = gdk_win.get_height()
    pix = Gdk.pixbuf_get_from_window(gdk_win, 0, 0, w, h)
    target_path = os.path.join(SCREENSHOTS_DIR, filename)
    pix.savev(target_path, "png", [], [])
    print(f"✔ Captura exitosa: {filename} ({w}x{h})")
    return True


def run_all_captures():
    print("Iniciando generación de capturas de pantalla de DDEV Studio...")
    
    # Datos de demostración de proyectos ricos y diversos
    sample_projects = [
        {
            "name": "portal-drupal11",
            "status": "running",
            "type": "drupal11",
            "_tech_type": "drupal11",
            "php_version": "8.3",
            "httpurl": "http://portal-drupal11.ddev.site",
            "httpsurl": "https://portal-drupal11.ddev.site",
            "primary_url": "https://portal-drupal11.ddev.site",
            "approot": "/home/maycol/sites/portal-drupal11",
            "docroot": "web",
            "mailpit_url": "https://portal-drupal11.ddev.site:8026",
            "database_info": {
                "type": "mariadb",
                "version": "10.11",
                "host": "127.0.0.1",
                "published_port": 3306,
                "username": "db",
                "password": "db",
                "database": "db"
            },
            "services": {
                "web": {"status": "healthy"},
                "db": {"status": "healthy"},
                "mailpit": {"status": "running"},
                "phpmyadmin": {"status": "running", "https_url": "https://portal-drupal11.ddev.site:8037"}
            },
            "is_xdebug_live": False
        },
        {
            "name": "api-laravel11",
            "status": "running",
            "type": "laravel",
            "_tech_type": "laravel",
            "php_version": "8.3",
            "httpurl": "http://api-laravel11.ddev.site",
            "httpsurl": "https://api-laravel11.ddev.site",
            "primary_url": "https://api-laravel11.ddev.site",
            "approot": "/home/maycol/sites/api-laravel11",
            "docroot": "public",
            "database_info": {
                "type": "mysql",
                "version": "8.0",
                "host": "127.0.0.1",
                "published_port": 3307,
                "username": "db",
                "password": "db",
                "database": "db"
            },
            "services": {
                "web": {"status": "healthy"},
                "db": {"status": "healthy"}
            },
            "is_xdebug_live": True
        },
        {
            "name": "dashboard-nextjs",
            "status": "running",
            "type": "nodejs",
            "_tech_type": "nextjs",
            "nodejs_version": "20",
            "httpurl": "http://dashboard-nextjs.ddev.site",
            "httpsurl": "https://dashboard-nextjs.ddev.site",
            "primary_url": "https://dashboard-nextjs.ddev.site",
            "approot": "/home/maycol/sites/dashboard-nextjs",
            "docroot": ".",
            "services": {
                "web": {"status": "healthy"}
            }
        },
        {
            "name": "ecommerce-django",
            "status": "stopped",
            "type": "django",
            "_tech_type": "django",
            "python_version": "3.11",
            "httpurl": "http://ecommerce-django.ddev.site",
            "httpsurl": "https://ecommerce-django.ddev.site",
            "primary_url": "https://ecommerce-django.ddev.site",
            "approot": "/home/maycol/sites/ecommerce-django",
            "docroot": "."
        },
        {
            "name": "corporativo-wp",
            "status": "paused",
            "type": "wordpress",
            "_tech_type": "wordpress",
            "php_version": "8.2",
            "httpurl": "http://corporativo-wp.ddev.site",
            "httpsurl": "https://corporativo-wp.ddev.site",
            "primary_url": "https://corporativo-wp.ddev.site",
            "approot": "/home/maycol/sites/corporativo-wp",
            "docroot": "web"
        }
    ]

    app = DDEVManagerWindow()
    app.set_default_size(1120, 780)
    app.show_all()
    app.init_state()
    
    # -------------------------------------------------------------------------
    # 1. Pestaña Mis Proyectos (Listado)
    # -------------------------------------------------------------------------
    app.notebook.set_current_page(0)
    app.stack_projects_tab.set_visible_child_name("list")
    app.update_projects_ui(sample_projects)
    capture_window(app, "01_proyectos_lista.png")

    # -------------------------------------------------------------------------
    # 2. Detalles del Proyecto - General (portal-drupal11)
    # -------------------------------------------------------------------------
    app.notebook.set_current_page(0)
    app.stack_projects_tab.set_visible_child_name("details")
    proj_drupal = sample_projects[0]
    app.project_details_view.proj = proj_drupal
    app.project_details_view.proj_name = proj_drupal["name"]
    app.project_details_view.base_dir = proj_drupal["approot"]
    app.project_details_view.render_details_ui(proj_drupal)
    # Asegurar scroll al tope
    adj = app.project_details_view.scrolled.get_vadjustment()
    adj.set_value(0)
    capture_window(app, "02_detalles_proyecto_general.png")

    # -------------------------------------------------------------------------
    # 3. Detalles del Proyecto - Base de Datos
    # -------------------------------------------------------------------------
    # Hacemos scroll hacia la tarjeta de Base de Datos
    adj.set_value(220)
    capture_window(app, "03_detalles_base_datos.png")

    # -------------------------------------------------------------------------
    # 4. Detalles del Proyecto - Framework Developer Toolkit (api-laravel11)
    # -------------------------------------------------------------------------
    proj_laravel = sample_projects[1]
    app.project_details_view.proj = proj_laravel
    app.project_details_view.proj_name = proj_laravel["name"]
    app.project_details_view.base_dir = proj_laravel["approot"]
    app.project_details_view.render_details_ui(proj_laravel)
    adj.set_value(400)
    capture_window(app, "04_detalles_framework_toolkit.png")

    # -------------------------------------------------------------------------
    # 5. Nuevo Proyecto - Descargar Proyecto Nuevo (Modo 1)
    # -------------------------------------------------------------------------
    app.notebook.set_current_page(1)
    app.tab_new.switch_mode("create")
    app.tab_new.entry_name.set_text("mi-nuevo-proyecto")
    capture_window(app, "05_nuevo_proyecto_descarga.png")

    # -------------------------------------------------------------------------
    # 6. Nuevo Proyecto - Importar Carpeta Existente (Modo 2)
    # -------------------------------------------------------------------------
    app.tab_new.switch_mode("import")
    app.tab_new.entry_import_path.set_text("/home/maycol/sites/portal-drupal11")
    app.tab_new.entry_import_name.set_text("portal-drupal11")
    app.tab_new.combo_import_type.set_active_id("drupal11")
    for idx, dr_text in enumerate(["docroot", "web", "public", "dist", "."]):
        if dr_text == "web":
            app.tab_new.combo_import_docroot.set_active(idx)
            break
    app.tab_new.lbl_import_status_badge.set_markup("<span color='#10b981'><b>✓ Stack detectado: Drupal 11 (PHP 8.3) con docroot 'web'</b></span>")
    capture_window(app, "06_nuevo_proyecto_importar.png")

    # -------------------------------------------------------------------------
    # 7. Herramientas Globales
    # -------------------------------------------------------------------------
    app.notebook.set_current_page(2)
    adj_tools = app.tab_tools.get_vadjustment()
    adj_tools.set_value(0)
    capture_window(app, "07_herramientas_globales.png")

    # -------------------------------------------------------------------------
    # 8. Monitor de Docker en Tiempo Real
    # -------------------------------------------------------------------------
    # Creamos métricas sintéticas ricas para mostrar el monitor activo
    mock_docker_stats = {
        "is_docker_available": True,
        "error_message": "",
        "containers": [
            {
                "id": "c1a2b3c4d5e6",
                "name": "ddev-portal-drupal11-web",
                "project": "portal-drupal11",
                "service": "web",
                "scope": "project",
                "cpu_percent": 3.4,
                "mem_used_bytes": 268435456,
                "mem_limit_bytes": 16777216000,
                "mem_used_str": "256.0 MiB",
                "mem_limit_str": "15.6 GiB",
                "mem_percent": 1.6,
                "net_io": "13.8MB / 28.4MB",
                "block_io": "1.0MB / 8.0MB",
                "pids": 18
            },
            {
                "id": "d2e3f4a5b6c7",
                "name": "ddev-portal-drupal11-db",
                "project": "portal-drupal11",
                "service": "db",
                "scope": "project",
                "cpu_percent": 1.2,
                "mem_used_bytes": 188743680,
                "mem_limit_bytes": 16777216000,
                "mem_used_str": "180.0 MiB",
                "mem_limit_str": "15.6 GiB",
                "mem_percent": 1.1,
                "net_io": "4.9MB / 8.5MB",
                "block_io": "20.0MB / 40.0MB",
                "pids": 24
            },
            {
                "id": "e3f4a5b6c7d8",
                "name": "ddev-api-laravel11-web",
                "project": "api-laravel11",
                "service": "web",
                "scope": "project",
                "cpu_percent": 0.8,
                "mem_used_bytes": 134217728,
                "mem_limit_bytes": 16777216000,
                "mem_used_str": "128.0 MiB",
                "mem_limit_str": "15.6 GiB",
                "mem_percent": 0.8,
                "net_io": "2.9MB / 4.3MB",
                "block_io": "512KB / 2.0MB",
                "pids": 12
            },
            {
                "id": "f4a5b6c7d8e9",
                "name": "ddev-router",
                "project": "DDEV Sistema",
                "service": "router",
                "scope": "system",
                "cpu_percent": 0.4,
                "mem_used_bytes": 67108864,
                "mem_limit_bytes": 16777216000,
                "mem_used_str": "64.0 MiB",
                "mem_limit_str": "15.6 GiB",
                "mem_percent": 0.4,
                "net_io": "42.9MB / 59.1MB",
                "block_io": "0B / 1.0MB",
                "pids": 8
            }
        ],
        "projects": {
            "portal-drupal11": {
                "project_name": "portal-drupal11",
                "scope": "project",
                "container_count": 2,
                "total_cpu_pct": 4.6,
                "total_mem_bytes": 457179136,
                "total_mem_limit_bytes": 16777216000,
                "total_mem_str": "436.0 MiB",
                "mem_percent": 2.7,
                "containers": []
            },
            "api-laravel11": {
                "project_name": "api-laravel11",
                "scope": "project",
                "container_count": 1,
                "total_cpu_pct": 0.8,
                "total_mem_bytes": 134217728,
                "total_mem_limit_bytes": 16777216000,
                "total_mem_str": "128.0 MiB",
                "mem_percent": 0.8,
                "containers": []
            },
            "DDEV Sistema": {
                "project_name": "DDEV Sistema",
                "scope": "system",
                "container_count": 1,
                "total_cpu_pct": 0.4,
                "total_mem_bytes": 67108864,
                "total_mem_limit_bytes": 16777216000,
                "total_mem_str": "64.0 MiB",
                "mem_percent": 0.4,
                "containers": []
            }
        },
        "global_summary": {
            "total_cpu_pct": 5.8,
            "total_mem_bytes": 658505728,
            "total_mem_limit_bytes": 16777216000,
            "total_mem_str": "628.0 MiB",
            "total_limit_str": "15.6 GiB",
            "mem_percent": 3.9,
            "container_count": 4,
            "ddev_container_count": 4,
            "total_net_in_bytes": 67800000,
            "total_net_out_bytes": 105200000,
            "total_net_str": "64.6 MiB / 100.3 MiB",
            "total_block_str": "21.5 MiB / 51.0 MiB"
        }
    }
    
    # Renderizamos en la vista de docker_monitor embebida en Tools
    if hasattr(app.tab_tools, "docker_monitor_view"):
        dm_view = app.tab_tools.docker_monitor_view
        dm_view.stop_polling()
        dm_view.cached_stats = mock_docker_stats
        dm_view.apply_stats_to_ui()
    adj_tools.set_value(260)
    capture_window(app, "08_docker_monitor.png")

    # -------------------------------------------------------------------------
    # 9. Add-ons Marketplace
    # -------------------------------------------------------------------------
    app.notebook.set_current_page(3)
    app.tab_addons.update_projects(sample_projects)
    capture_window(app, "09_addons_marketplace.png")

    # -------------------------------------------------------------------------
    # 10. Asistente Drupal - Generador de Código (Scaffolding)
    # -------------------------------------------------------------------------
    app.notebook.set_current_page(0)
    app.stack_projects_tab.set_visible_child_name("drupal_tools")
    app.drupal_tools_view.load_project(proj_drupal, from_view="list")
    app.drupal_tools_view.notebook.set_current_page(0)
    app.drupal_tools_view.btn_gen_module.set_active(True)
    capture_window(app, "10_drupal_tools_scaffold.png")

    # -------------------------------------------------------------------------
    # 11. Asistente Drupal - Temas Starterkit y Presets
    # -------------------------------------------------------------------------
    app.drupal_tools_view.btn_gen_theme.set_active(True)
    capture_window(app, "11_drupal_tools_themes.png")

    # -------------------------------------------------------------------------
    # 12. Asistente Drupal - Suite de Módulos y APIs Fundamentales
    # -------------------------------------------------------------------------
    app.drupal_tools_view.notebook.set_current_page(1)
    capture_window(app, "12_drupal_tools_modules.png")

    # -------------------------------------------------------------------------
    # 13. Drupal Multisitio
    # -------------------------------------------------------------------------
    app.stack_projects_tab.set_visible_child_name("subsites")
    app.subsites_manager_view.load_project(proj_drupal)
    subsites_sample = [
        {
            "name": "portal-tienda",
            "path": "/home/maycol/sites/portal-drupal11/web/sites/portal-tienda",
            "url": "https://portal-tienda.ddev.site",
            "db": "portal_tienda",
            "config_exists": True
        },
        {
            "name": "portal-blog",
            "path": "/home/maycol/sites/portal-drupal11/web/sites/portal-blog",
            "url": "https://portal-blog.ddev.site",
            "db": "portal_blog",
            "config_exists": True
        }
    ]
    app.subsites_manager_view.update_subsites_ui(subsites_sample, proj_drupal)
    capture_window(app, "13_drupal_subsitios.png")

    # -------------------------------------------------------------------------
    # 14. Asistente IA Local - Chat con Ollama
    # -------------------------------------------------------------------------
    app.notebook.set_current_page(4)
    app.tab_ai.active_model = "qwen2.5:3b"
    app.tab_ai.lbl_status.set_markup("<span color='#10b981'>● Ollama Activo (qwen2.5:3b)</span>")
    app.tab_ai.combo_models.remove_all()
    app.tab_ai.combo_models.append("qwen2.5:3b", "qwen2.5:3b (2.3 GB) - Recomendado")
    app.tab_ai.combo_models.append("llama3.2:3b", "llama3.2:3b (2.0 GB)")
    app.tab_ai.combo_models.set_active(0)
    app.tab_ai.stack.set_visible_child_name("chat")
    
    # Poblamos mensajes interactivos
    app.tab_ai.clear_chat()
    app.tab_ai._add_user_message_ui("¿Cómo configuro un reverse proxy Nginx con WebSockets para HMR en Next.js con DDEV?")
    app.tab_ai._add_assistant_message_ui()
    assistant_reply = (
        "Para habilitar el soporte completo de **Fast Refresh / HMR (Hot Module Replacement)** en Next.js dentro de DDEV, "
        "crea el archivo `.ddev/nginx_full/nginx-site.conf` con la siguiente directiva de reverse proxy para WebSockets:\n\n"
        "```nginx\n"
        "location / {\n"
        "    proxy_pass http://127.0.0.1:3000;\n"
        "    proxy_http_version 1.1;\n"
        "    proxy_set_header Upgrade $http_upgrade;\n"
        "    proxy_set_header Connection \"Upgrade\";\n"
        "    proxy_set_header Host $host;\n"
        "    proxy_read_timeout 86400s;\n"
        "}\n"
        "```\n\n"
        "Luego define el proceso en segundo plano en `.ddev/config.daemon.yaml` ejecutando `npm run dev` y reinicia con `ddev restart`."
    )
    app.tab_ai.current_assistant_text = assistant_reply
    app.tab_ai.current_assistant_label.set_text(assistant_reply)
    capture_window(app, "14_asistente_ia_chat.png")

    # -------------------------------------------------------------------------
    # 15. Asistente IA Local - Onboarding y Catálogo de Modelos
    # -------------------------------------------------------------------------
    app.tab_ai.stack.set_visible_child_name("onboarding")
    capture_window(app, "15_asistente_ia_onboarding.png")

    # -------------------------------------------------------------------------
    # 16. Diálogo Modal de Diagnóstico SSL
    # -------------------------------------------------------------------------
    ssl_dlg = SSLDiagDialog(app)
    ssl_dlg.lbl_subtitle.set_markup("Comprobación exhaustiva de <b>mkcert</b> y <b>certutil</b> en los almacenes locales.")
    ssl_dlg.lbl_chk_mkcert.set_markup("✔ <b>mkcert:</b> Instalado y funcional en el sistema (/usr/local/bin/mkcert)")
    ssl_dlg.lbl_chk_certutil.set_markup("✔ <b>certutil (libnss3-tools):</b> Registrado en Chrome, Chromium y Firefox")
    ssl_dlg.lbl_chk_trust.set_markup("✔ <b>Almacén de Autoridades:</b> La CA raíz de DDEV es plenamente confiable")
    capture_window(ssl_dlg, "16_dialogo_ssl.png", width=640, height=520)
    ssl_dlg.destroy()

    # -------------------------------------------------------------------------
    # 17. Diálogo Modal de Integración Continua (CI/CD GitHub Actions)
    # -------------------------------------------------------------------------
    ci_dlg = CIDialog(app, "/home/maycol/ddev-studio", "portal-drupal11", "drupal11")
    capture_window(ci_dlg, "17_dialogo_ci_cd.png", width=700, height=580)
    ci_dlg.destroy()

    # -------------------------------------------------------------------------
    # 18. Diálogo Modal de Desinstalación Segura de Módulo Drupal
    # -------------------------------------------------------------------------
    mod_sample = {
        "machine_name": "devel_generate",
        "label": "Devel Generate",
        "package": "Desarrollo",
        "description": "Generador de nodos, taxonomías y usuarios de prueba"
    }
    un_dlg = DrupalUninstallDialog(app, mod_sample, "https://portal-drupal11.ddev.site")
    capture_window(un_dlg, "18_dialogo_desinstalacion_drupal.png", width=600, height=460)
    un_dlg.destroy()

    # -------------------------------------------------------------------------
    # 19. Diálogo Modal de Progreso de Tareas en Segundo Plano
    # -------------------------------------------------------------------------
    prog_dlg = ProgressDialog(app, title="Instalación de Add-on: ddev-redis")
    prog_dlg.set_status("Instalando complemento ddev-redis y recargando contenedor...")
    prog_dlg.progress_bar.set_fraction(0.85)
    log_sample = (
        "🚀 Ejecutando: ddev get ddev/ddev-redis\n"
        "⬇ Descargando repositorio oficial desde GitHub...\n"
        "✔ Archivo .ddev/docker-compose.redis.yaml inyectado con éxito.\n"
        "✔ Metadatos de add-on registrados en .ddev/addon-metadata/\n"
        "🔄 Reiniciando proyecto con 'ddev restart'...\n"
        "   - Deteniendo contenedores web y db...\n"
        "   - Levantando contenedor adicional: ddev-portal-drupal11-redis (Redis 7.2 Alpine)\n"
        "   - Verificando estado de salud de servicios...\n"
        "✔ ¡Instalación completada con éxito! Redis disponible en el puerto 6379."
    )
    prog_dlg.append_log(log_sample)
    capture_window(prog_dlg, "19_dialogo_progreso.png", width=700, height=500)
    prog_dlg.destroy()

    # -------------------------------------------------------------------------
    # 20. Diálogo Acerca de DDEV Studio
    # -------------------------------------------------------------------------
    about_dlg = Gtk.AboutDialog(transient_for=app, modal=True)
    about_dlg.set_program_name("DDEV Studio")
    about_dlg.set_version("1.2.0")
    about_dlg.set_comments(
        "Estación de Trabajo Visual y DevOps Universal para DDEV en Linux.\n"
        "Soporte de primer nivel para Drupal (11-7), WordPress, Laravel, Symfony,\n"
        "Next.js, Angular, React, Vue, Django, Flask y Asistente IA Local con Ollama."
    )
    about_dlg.set_website("https://github.com/mayc1030/ddev-studio")
    about_dlg.set_website_label("Repositorio Oficial GitHub")
    from ddev_studio.ui.helpers import load_icon
    ddev_icon = load_icon("ddev.svg", 64)
    if ddev_icon:
        about_dlg.set_logo(ddev_icon)
    capture_window(about_dlg, "20_dialogo_acerca_de.png", width=560, height=440)
    about_dlg.destroy()

    app.destroy()
    print("¡Todas las capturas se han generado exitosamente!")


if __name__ == "__main__":
    run_all_captures()
