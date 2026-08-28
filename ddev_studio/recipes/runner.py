# -*- coding: utf-8 -*-
"""
Motor de ejecución de recetas de creación e importación de proyectos en DDEV.
"""

import json
import os
import re
import shutil
import subprocess
import threading
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

from ddev_studio.constants import FRAMEWORKS, DRUPAL_VERSIONS
from ddev_studio.core.detector import sanitize_project_name
from ddev_studio.core.process import run_subproc
from ddev_studio.ui.dialogs.progress import ProgressDialog


SITES_PHP_TEMPLATE = '''<?php
/**
 * @file
 * Drupal multi-site configuration file for DDEV.
 */

// Dynamic DDEV multisite mapping
$sites_base = __DIR__;
if (is_dir($sites_base)) {
  $entries = scandir($sites_base);
  foreach ($entries as $entry) {
    if ($entry !== '.' && $entry !== '..' && $entry !== 'default' && $entry !== 'all' && $entry !== 'g' && $entry !== 'settings' && is_dir($sites_base . '/' . $entry)) {
      $sites[$entry . '.ddev.site'] = $entry;
      if (!empty($_ENV['DDEV_PROJECT'])) {
        $sites[$entry . '.' . $_ENV['DDEV_PROJECT'] . '.ddev.site'] = $entry;
      }
      $sites['local.' . $entry . '.com'] = $entry;
    }
  }
}
'''


def run_create_project(parent_window, raw_name, base_dir, clean_target_before, fw, drupal_ver_info, php_version, db_type, node_version, auto_install, is_multisite_enabled, on_success_callback=None):
    """
    Ejecuta el flujo completo de creación y scaffolding para el framework seleccionado.
    """
    slug = sanitize_project_name(raw_name)
    node_version = re.sub(r'[^\d]', '', str(node_version or '')) or "22"
    target_dir = os.path.join(base_dir, slug)
    fw_id = fw["id"]
    
    dialog_title = f"Creando {fw['name']}"
    if fw_id == "drupal":
        dialog_title = f"Creando Drupal {drupal_ver_info['id']}: {slug}"
    else:
        dialog_title = f"Creando {fw['name']}: {slug}"
        
    dialog = ProgressDialog(parent_window, title=dialog_title)
    dialog.set_status(f"Iniciando creación de {dialog_title}...")
    
    def run_creation():
        try:
            def log(text):
                GLib.idle_add(dialog.append_log, text + "\n")
                
            def set_st(st):
                GLib.idle_add(dialog.set_status, st)
                
            set_st("Limpiando contenedores anteriores si existen...")
            subprocess.run(["ddev", "delete", "-O", "-y", slug], capture_output=True)
            
            if clean_target_before and os.path.exists(target_dir):
                set_st("Vaciando carpeta de proyecto...")
                shutil.rmtree(target_dir, ignore_errors=True)
                
            os.makedirs(target_dir, exist_ok=True)
            
            log(f"📁 Directorio del proyecto: {target_dir}")
            log(f"🚀 Tecnología: {fw['name']}" + (f" (Versión {drupal_ver_info['id']})" if fw_id == 'drupal' else ""))
            log(f"🐘 Versión de PHP: {php_version} | DB: {db_type}\n" + "="*50)
            
            primary_url = f"https://{slug}.ddev.site"
            
            if fw_id == "drupal":
                d_ver = drupal_ver_info["id"]
                d_type = drupal_ver_info["type"]
                d_docroot = drupal_ver_info["docroot"]
                
                set_st(f"Configurando DDEV para Drupal {d_ver}...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    f"--project-type={d_type}",
                    f"--docroot={d_docroot}",
                    f"--php-version={php_version}",
                    f"--database={db_type}"
                ]
                run_subproc(cfg_cmd, target_dir, dialog)
                
                set_st("Levantando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                if d_ver in ["11", "10", "9", "8"]:
                    set_st(f"Descargando Drupal {d_ver} con Composer...")
                    pkg = "drupal/recommended-project"
                    if d_ver == "11":
                        pkg = "drupal/recommended-project:^11"
                    elif d_ver == "10":
                        pkg = "drupal/recommended-project:^10"
                    elif d_ver == "9":
                        pkg = "drupal/recommended-project:^9"
                    elif d_ver == "8":
                        pkg = "drupal/recommended-project:^8"
                        
                    run_subproc(["ddev", "composer", "create-project", pkg, "/tmp/drupal-pkg"], target_dir, dialog)
                    
                    set_st("Moviendo archivos del proyecto...")
                    run_subproc(["ddev", "exec", "sh -c 'cp -a /tmp/drupal-pkg/. . && rm -rf /tmp/drupal-pkg'"], target_dir, dialog)
                    
                    set_st("Instalando Drush...")
                    drush_pkg = "drush/drush"
                    if d_ver == "8":
                        drush_pkg = "drush/drush:^10"
                    run_subproc(["ddev", "composer", "require", drush_pkg], target_dir, dialog)
                    
                    if auto_install:
                        set_st("Instalando Drupal estándar con Drush...")
                        inst_cmd = [
                            "ddev", "drush", "site:install", "standard",
                            "--account-name=admin",
                            "--account-pass=admin",
                            f"--site-name={slug.capitalize()}",
                            "-y"
                        ]
                        run_subproc(inst_cmd, target_dir, dialog)
                        log("\n🎉 Drupal instalado con éxito!")
                        log("Credenciales: admin / admin")
                        
                elif d_ver == "7":
                    set_st("Descargando Drupal 7...")
                    run_subproc(["ddev", "drush", "dl", "drupal-7", "-y", "--destination=/tmp/d7"], target_dir, dialog)
                    run_subproc(["ddev", "exec", "sh -c 'cp -a /tmp/d7/drupal-7*/* /var/www/html/ && cp -a /tmp/d7/drupal-7*/.* /var/www/html/ 2>/dev/null || true; rm -rf /tmp/d7'"], target_dir, dialog)
                    
                    if auto_install:
                        set_st("Instalando Drupal 7 estándar...")
                        inst_cmd = [
                            "ddev", "drush", "site:install", "standard",
                            "--account-name=admin",
                            "--account-pass=admin",
                            f"--site-name={slug.capitalize()}",
                            "-y"
                        ]
                        run_subproc(inst_cmd, target_dir, dialog)
                        log("\n🎉 Drupal 7 instalado con éxito!")
                        log("Credenciales: admin / admin")

                # Drupal Multisite Architecture
                if is_multisite_enabled:
                    set_st("Configurando arquitectura Drupal Multisite...")
                    sites_php_dir = os.path.join(target_dir, d_docroot, "sites") if d_docroot else os.path.join(target_dir, "sites")
                    os.makedirs(sites_php_dir, exist_ok=True)
                    sites_php_file = os.path.join(sites_php_dir, "sites.php")
                    with open(sites_php_file, "w") as sf:
                        sf.write(SITES_PHP_TEMPLATE)
                    log("✓ Arquitectura Multisite habilitada en sites/sites.php con mapeo dinámico.")

            elif fw_id == "wordpress":
                set_st("Configurando DDEV para WordPress...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=wordpress",
                    "--docroot=.",
                    f"--php-version={php_version}",
                    f"--database={db_type}"
                ]
                run_subproc(cfg_cmd, target_dir, dialog)
                
                set_st("Levantando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                set_st("Descargando núcleo de WordPress...")
                run_subproc(["ddev", "wp", "core", "download"], target_dir, dialog)
                
                if auto_install:
                    set_st("Instalando base de datos y usuario admin...")
                    install_cmd = [
                        "ddev", "wp", "core", "install",
                        f"--url=https://{slug}.ddev.site",
                        f"--title={slug.capitalize()}",
                        "--admin_user=admin",
                        "--admin_password=admin",
                        "--admin_email=admin@example.com",
                        "--skip-email"
                    ]
                    run_subproc(install_cmd, target_dir, dialog)
                    log("\n🎉 WordPress instalado!")
                    log("Credenciales: admin / admin")

            elif fw_id == "laravel":
                set_st("Configurando DDEV para Laravel...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=laravel",
                    "--docroot=public",
                    f"--php-version={php_version}",
                    f"--database={db_type}"
                ]
                run_subproc(cfg_cmd, target_dir, dialog)
                
                set_st("Levantando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                set_st("Instalando Laravel con Composer...")
                run_subproc(["ddev", "composer", "create-project", "--prefer-dist", "laravel/laravel"], target_dir, dialog)
                
                set_st("Generando clave de aplicación...")
                run_subproc(["ddev", "exec", "php artisan key:generate"], target_dir, dialog)
            elif fw_id == "nextjs":
                set_st("Configurando DDEV para Next.js (React Full-Stack)...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=generic",
                    "--docroot=.",
                    f"--nodejs-version={node_version}",
                ]
                if db_type == "none":
                    cfg_cmd.append("--omit-containers=db")
                else:
                    cfg_cmd.append(f"--database={db_type}")
                run_subproc(cfg_cmd, target_dir, dialog)
                
                try:
                    cfg_yaml = os.path.join(target_dir, ".ddev", "config.yaml")
                    if os.path.exists(cfg_yaml):
                        with open(cfg_yaml, "a") as f:
                            f.write("\nweb_extra_exposed_ports:\n  - name: nodejs\n    container_port: 3000\n    http_port: 2999\n    https_port: 3000\n")
                except Exception:
                    pass
                
                set_st("Levantando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                set_st("Creando aplicación Next.js con App Router y Tailwind CSS...")
                run_subproc([
                    "ddev", "npx", "--yes", "create-next-app@latest", "tmp-next",
                    "--typescript",
                    "--tailwind",
                    "--eslint",
                    "--app",
                    "--src-dir",
                    '--import-alias=@/*',
                    "--use-npm"
                ], target_dir, dialog)
                
                set_st("Organizando estructura del proyecto...")
                run_subproc(["ddev", "exec", "sh -c 'cp -a tmp-next/. . && rm -rf tmp-next'"], target_dir, dialog)
                run_subproc(["ddev", "exec", "sed -i 's/\"dev\": \"next dev\"/\"dev\": \"next dev -H 0.0.0.0 -p 3000\"/g' package.json"], target_dir, dialog)
                
                set_st("Configurando Nginx Reverse Proxy y daemon en segundo plano...")
                nginx_full_dir = os.path.join(target_dir, ".ddev", "nginx_full")
                os.makedirs(nginx_full_dir, exist_ok=True)
                with open(os.path.join(nginx_full_dir, "nginx-site.conf"), "w") as nf:
                    nf.write("""location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
""")
                with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                    df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: nextjs-dev-server
    command: "npm run dev"
    directory: /var/www/html
""")
                set_st("Reiniciando DDEV para activar el servidor Next.js...")
                run_subproc(["ddev", "restart", "-y"], target_dir, dialog)
                log("\n🎉 ¡Proyecto Next.js creado y ejecutándose en segundo plano!")

            elif fw_id == "react":
                set_st("Configurando DDEV para React...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=generic",
                    "--docroot=dist",
                    f"--nodejs-version={node_version}",
                    f"--database={db_type}"
                ]
                run_subproc(cfg_cmd, target_dir, dialog)
                
                try:
                    cfg_yaml = os.path.join(target_dir, ".ddev", "config.yaml")
                    if os.path.exists(cfg_yaml):
                        with open(cfg_yaml, "a") as f:
                            f.write("\nweb_extra_exposed_ports:\n  - name: nodejs\n    container_port: 5173\n    http_port: 5172\n    https_port: 5173\n")
                except Exception:
                    pass
                
                set_st("Levantando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                set_st("Creando plantilla React con Vite...")
                run_subproc(["ddev", "npx", "--yes", "create-vite@latest", "tmp-vite", "--template", "react-ts"], target_dir, dialog)
                
                set_st("Organizando estructura del proyecto...")
                run_subproc(["ddev", "exec", "sh -c 'cp -a tmp-vite/. . && rm -rf tmp-vite'"], target_dir, dialog)
                run_subproc(["ddev", "exec", "sed -i 's/\"dev\": \"vite\"/\"dev\": \"vite --host 0.0.0.0\"/g' package.json"], target_dir, dialog)
                
                set_st("Instalando dependencias npm...")
                run_subproc(["ddev", "npm", "install"], target_dir, dialog)
                
                set_st("Compilando versión inicial...")
                run_subproc(["ddev", "npm", "run", "build"], target_dir, dialog)
                log("\n🎉 Proyecto React listo!")

            elif fw_id == "vue":
                set_st("Configurando DDEV para Vue 3...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=generic",
                    "--docroot=dist",
                    f"--nodejs-version={node_version}",
                    f"--database={db_type}"
                ]
                run_subproc(cfg_cmd, target_dir, dialog)
                
                try:
                    cfg_yaml = os.path.join(target_dir, ".ddev", "config.yaml")
                    if os.path.exists(cfg_yaml):
                        with open(cfg_yaml, "a") as f:
                            f.write("\nweb_extra_exposed_ports:\n  - name: nodejs\n    container_port: 5173\n    http_port: 5172\n    https_port: 5173\n")
                except Exception:
                    pass
                
                set_st("Levantando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                set_st("Creando plantilla Vue 3 con Vite...")
                run_subproc(["ddev", "npx", "--yes", "create-vite@latest", "tmp-vite", "--template", "vue-ts"], target_dir, dialog)
                
                set_st("Organizando estructura del proyecto...")
                run_subproc(["ddev", "exec", "sh -c 'cp -a tmp-vite/. . && rm -rf tmp-vite'"], target_dir, dialog)
                run_subproc(["ddev", "exec", "sed -i 's/\"dev\": \"vite\"/\"dev\": \"vite --host 0.0.0.0\"/g' package.json"], target_dir, dialog)
                
                set_st("Instalando dependencias npm...")
                run_subproc(["ddev", "npm", "install"], target_dir, dialog)
                
                set_st("Compilando versión inicial...")
                run_subproc(["ddev", "npm", "run", "build"], target_dir, dialog)
                log("\n🎉 Proyecto Vue listo!")

            elif fw_id == "django":
                set_st("Configurando DDEV para Django...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=generic",
                    "--docroot=.",
                    f"--database={db_type}",
                    "--webimage-extra-packages=python3-venv,python3-pip"
                ]
                run_subproc(cfg_cmd, target_dir, dialog)
                
                set_st("Iniciando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                set_st("Creando entorno virtual Python (.venv)...")
                run_subproc(["ddev", "exec", "python3 -m venv /var/www/html/.venv"], target_dir, dialog)
                
                set_st("Instalando Django y conectores de base de datos...")
                run_subproc(["ddev", "exec", "/var/www/html/.venv/bin/pip install django PyMySQL cryptography psycopg2-binary"], target_dir, dialog)
                
                set_st("Generando estructura inicial de Django...")
                run_subproc(["ddev", "exec", "/var/www/html/.venv/bin/django-admin startproject app ."], target_dir, dialog)
                
                set_st("Configurando base de datos y ALLOWED_HOSTS...")
                settings_py_path = os.path.join(target_dir, "app", "settings.py")
                if os.path.exists(settings_py_path):
                    try:
                        with open(settings_py_path, "r") as sf:
                            s_code = sf.read()
                        s_code = s_code.replace("ALLOWED_HOSTS = []", "ALLOWED_HOSTS = ['*']")
                        if "postgres" in db_type:
                            db_block = """DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'db',
        'USER': 'db',
        'PASSWORD': 'db',
        'HOST': 'db',
        'PORT': '5432',
    }
}"""
                        else:
                            db_block = """import pymysql
pymysql.install_as_MySQLdb()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'db',
        'USER': 'db',
        'PASSWORD': 'db',
        'HOST': 'db',
        'PORT': '3306',
    }
}"""
                        s_code = re.sub(r'DATABASES\s*=\s*\{.*?\n\}', db_block, s_code, flags=re.DOTALL)
                        with open(settings_py_path, "w") as sf:
                            sf.write(s_code)
                    except Exception as ex:
                        log(f"Nota en settings.py: {ex}")
                        
                set_st("Ejecutando migraciones de base de datos...")
                run_subproc(["ddev", "exec", "/var/www/html/.venv/bin/python manage.py migrate"], target_dir, dialog)
                
                if auto_install:
                    set_st("Creando superusuario administrador (admin / admin)...")
                    superuser_script = "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin')"
                    run_subproc(["ddev", "exec", f'/var/www/html/.venv/bin/python manage.py shell -c "{superuser_script}"'], target_dir, dialog)
                    log("\n👑 Superusuario creado: admin / admin (Panel en /admin)")
                    
                set_st("Configurando Nginx Reverse Proxy y daemon de fondo...")
                nginx_full_dir = os.path.join(target_dir, ".ddev", "nginx_full")
                os.makedirs(nginx_full_dir, exist_ok=True)
                with open(os.path.join(nginx_full_dir, "nginx-site.conf"), "w") as nf:
                    nf.write("""server {
    listen 80 default_server;
    listen 443 ssl default_server;

    root /var/www/html;

    ssl_certificate /etc/ssl/certs/master.crt;
    ssl_certificate_key /etc/ssl/certs/master.key;

    include /etc/nginx/monitoring.conf;

    error_log /dev/stdout info;
    access_log /var/log/nginx/access.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }

    include /etc/nginx/common.d/*.conf;
    include /mnt/ddev_config/nginx/*.conf;
}
""")
                with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                    df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: django
    command: "/var/www/html/.venv/bin/python manage.py runserver 0.0.0.0:8000"
    directory: /var/www/html
""")
                set_st("Reiniciando servidor DDEV para activar Django...")
                run_subproc(["ddev", "restart", "-y"], target_dir, dialog)
                log("\n🎉 Proyecto Django listo y corriendo!")

            elif fw_id == "flask":
                set_st("Configurando DDEV para Flask...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=generic",
                    "--docroot=.",
                    f"--database={db_type}",
                    "--webimage-extra-packages=python3-venv,python3-pip"
                ]
                run_subproc(cfg_cmd, target_dir, dialog)
                
                set_st("Iniciando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                set_st("Creando entorno virtual Python (.venv)...")
                run_subproc(["ddev", "exec", "python3 -m venv /var/www/html/.venv"], target_dir, dialog)
                
                set_st("Instalando Flask y conectores...")
                run_subproc(["ddev", "exec", "/var/www/html/.venv/bin/pip install flask pymysql psycopg2-binary cryptography python-dotenv"], target_dir, dialog)
                
                set_st("Creando aplicación inicial app.py...")
                app_py_path = os.path.join(target_dir, "app.py")
                flask_code = f"""from flask import Flask, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = \"\"\"<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{slug} - Flask en DDEV</title>
    <style>
        body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 500px; border: 1px solid rgba(255,255,255,0.1); }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        .badge {{ background: #0284c7; padding: 4px 12px; border-radius: 9999px; font-size: 0.85rem; font-weight: bold; display: inline-block; margin-top: 10px; }}
        p {{ color: #94a3b8; line-height: 1.5; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>¡Flask en DDEV Studio! 🚀</h1>
        <p>Tu aplicación <b>{slug}</b> con microframework Flask está corriendo exitosamente en Ubuntu MATE.</p>
        <span class="badge">Python 3 + Flask + DDEV</span>
    </div>
</body>
</html>\"\"\"

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
"""
                with open(app_py_path, "w") as f:
                    f.write(flask_code)

                set_st("Configurando Nginx Reverse Proxy y daemon de fondo...")
                nginx_full_dir = os.path.join(target_dir, ".ddev", "nginx_full")
                os.makedirs(nginx_full_dir, exist_ok=True)
                with open(os.path.join(nginx_full_dir, "nginx-site.conf"), "w") as nf:
                    nf.write("""server {
    listen 80 default_server;
    listen 443 ssl default_server;

    root /var/www/html;

    ssl_certificate /etc/ssl/certs/master.crt;
    ssl_certificate_key /etc/ssl/certs/master.key;

    include /etc/nginx/monitoring.conf;

    error_log /dev/stdout info;
    access_log /var/log/nginx/access.log;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }

    include /etc/nginx/common.d/*.conf;
    include /mnt/ddev_config/nginx/*.conf;
}
""")
                with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                    df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: flask
    command: "/var/www/html/.venv/bin/python app.py"
    directory: /var/www/html
""")
                set_st("Reiniciando servidor DDEV para activar Flask...")
                run_subproc(["ddev", "restart", "-y"], target_dir, dialog)
                log("\n🎉 Proyecto Flask listo y corriendo!")

            elif fw_id == "angular":
                set_st("Configurando DDEV para Angular...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=generic",
                    "--docroot=dist",
                    f"--nodejs-version={node_version}",
                    "--web-environment-add=NG_CLI_ANALYTICS=false"
                ]
                if db_type == "none":
                    cfg_cmd.append("--omit-containers=db")
                else:
                    cfg_cmd.append(f"--database={db_type}")
                run_subproc(cfg_cmd, target_dir, dialog)

                set_st("Iniciando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                set_st("Creando proyecto Angular con @angular/cli...")
                run_subproc(["ddev", "exec", "NG_CLI_ANALYTICS=false npx -y @angular/cli new app --directory=. --routing --style=css --skip-git --defaults"], target_dir, dialog)
                
                set_st("Configurando Nginx Reverse Proxy y Live Dev Server...")
                nginx_full_dir = os.path.join(target_dir, ".ddev", "nginx_full")
                os.makedirs(nginx_full_dir, exist_ok=True)
                with open(os.path.join(nginx_full_dir, "nginx-site.conf"), "w") as nf:
                    nf.write("""server {
    listen 80 default_server;
    listen 443 ssl default_server;

    root /var/www/html;

    ssl_certificate /etc/ssl/certs/master.crt;
    ssl_certificate_key /etc/ssl/certs/master.key;

    include /etc/nginx/monitoring.conf;

    error_log /dev/stdout info;
    access_log /var/log/nginx/access.log;

    location / {
        proxy_pass http://127.0.0.1:4200;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }

    include /etc/nginx/common.d/*.conf;
    include /mnt/ddev_config/nginx/*.conf;
}
""")
                with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                    df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: angular
    command: "npx ng serve --host 0.0.0.0 --port 4200 --allowed-hosts"
    directory: /var/www/html
""")
                set_st("Reiniciando DDEV para activar Angular Live Dev Server...")
                run_subproc(["ddev", "restart", "-y"], target_dir, dialog)
                log("\n🎉 Proyecto Angular listo y corriendo!")

            elif fw_id == "symfony":
                set_st("Configurando DDEV para Symfony...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=php",
                    "--docroot=public",
                    f"--php-version={php_version}",
                    f"--database={db_type}"
                ]
                run_subproc(cfg_cmd, target_dir, dialog)
                
                set_st("Levantando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                
                set_st("Descargando Symfony...")
                run_subproc(["ddev", "composer", "create-project", "symfony/skeleton", "."], target_dir, dialog)
                run_subproc(["ddev", "composer", "require", "webapp"], target_dir, dialog)
                log("\n🎉 Proyecto Symfony listo!")

            else:  # Generic PHP
                set_st("Configurando DDEV PHP...")
                cfg_cmd = [
                    "ddev", "config",
                    f"--project-name={slug}",
                    "--project-type=php",
                    "--docroot=.",
                    f"--php-version={php_version}",
                    f"--database={db_type}"
                ]
                run_subproc(cfg_cmd, target_dir, dialog)
                
                index_path = os.path.join(target_dir, "index.php")
                if not os.path.exists(index_path):
                    with open(index_path, "w") as f:
                        f.write(f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{slug} - DDEV Studio</title>
    <style>
        body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 500px; }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        .badge {{ background: #0284c7; padding: 4px 12px; border-radius: 9999px; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>¡Proyecto {slug} Activo! 🚀</h1>
        <p>Tu entorno DDEV está corriendo perfectamente en Ubuntu MATE.</p>
        <p><span class="badge">PHP <?php echo phpversion(); ?></span></p>
    </div>
</body>
</html>""")
                
                set_st("Levantando contenedores DDEV...")
                run_subproc(["ddev", "start", "-y"], target_dir, dialog)
                log("\n🎉 Proyecto PHP listo!")

            log("\n" + "="*50)
            log(f"URL: {primary_url}")
            log("¡Completado con éxito!")
            GLib.idle_add(dialog.finish, True, f"¡Proyecto '{slug}' creado con éxito!", primary_url, target_dir)
            if on_success_callback:
                GLib.idle_add(on_success_callback)
            
        except Exception as e:
            log(f"\n❌ ERROR: {str(e)}")
            GLib.idle_add(dialog.finish, False, f"Error en la creación: {str(e)}", "", target_dir)
            
    threading.Thread(target=run_creation, daemon=True).start()


def run_import_project(parent_window, target_dir, slug, p_type, docroot, php_ver, node_ver, db_type, is_multisite, do_composer, on_success_callback=None):
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
            if p_type == "django":
                os.makedirs(os.path.join(target_dir, ".ddev", "nginx_full"), exist_ok=True)
                with open(os.path.join(target_dir, ".ddev", "nginx_full", "nginx-site.conf"), "w") as nf:
                    nf.write("""location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
""")
                with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                    df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: django-server
    command: "/var/www/html/.venv/bin/python manage.py runserver 0.0.0.0:8000"
    directory: /var/www/html
""")
            elif p_type == "flask":
                os.makedirs(os.path.join(target_dir, ".ddev", "nginx_full"), exist_ok=True)
                with open(os.path.join(target_dir, ".ddev", "nginx_full", "nginx-site.conf"), "w") as nf:
                    nf.write("""location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
""")
                with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                    df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: flask-server
    command: "/var/www/html/.venv/bin/python app.py"
    directory: /var/www/html
""")
            elif p_type == "angular":
                os.makedirs(os.path.join(target_dir, ".ddev", "nginx_full"), exist_ok=True)
                with open(os.path.join(target_dir, ".ddev", "nginx_full", "nginx-site.conf"), "w") as nf:
                    nf.write("""location / {
    proxy_pass http://127.0.0.1:4200;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
""")
                with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                    df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: angular-dev-server
    command: "npx ng serve --host 0.0.0.0 --port 4200 --allowed-hosts"
    directory: /var/www/html
""")
            elif p_type == "nextjs":
                os.makedirs(os.path.join(target_dir, ".ddev", "nginx_full"), exist_ok=True)
                with open(os.path.join(target_dir, ".ddev", "nginx_full", "nginx-site.conf"), "w") as nf:
                    nf.write("""location / {
    proxy_pass http://127.0.0.1:3000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
""")
                with open(os.path.join(target_dir, ".ddev", "config.daemon.yaml"), "w") as df:
                    df.write("""#ddev-silent-no-warn
web_extra_daemons:
  - name: nextjs-dev-server
    command: "npm run dev"
    directory: /var/www/html
""")
            
            # 2. Dynamic sites.php if Drupal Multisite
            if is_multisite:
                set_st("Configurando enrutador dinámico Drupal Multisite...")
                sites_dir = os.path.join(target_dir, docroot, "sites") if docroot != "." else os.path.join(target_dir, "sites")
                os.makedirs(sites_dir, exist_ok=True)
                sites_php_file = os.path.join(sites_dir, "sites.php")
                if not os.path.exists(sites_php_file):
                    with open(sites_php_file, "w") as sf:
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
            log(f"\n❌ ERROR: {str(ex)}")
            GLib.idle_add(dialog.finish, False, f"Error importando proyecto: {str(ex)}", "", target_dir)
            
    threading.Thread(target=run_import, daemon=True).start()
