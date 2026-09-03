# -*- coding: utf-8 -*-
"""
Recetas de scaffolding para tecnologías basadas en Python 3:
Django y Flask con entornos virtuales y reverse proxy Nginx en DDEV.
"""

import os
import re

from ddev_studio.recipes.base import BaseRecipe
from ddev_studio.recipes.context import RecipeContext


class DjangoRecipe(BaseRecipe):
    fw_id = "django"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="generic",
            docroot=".",
            db_type=ctx.db_type,
            extra_args=["--webimage-extra-packages=python3-venv,python3-pip"]
        )
        self.start_ddev(ctx)

        ctx.set_status("Creando entorno virtual Python (.venv)...")
        ctx.run_cmd(["ddev", "exec", "python3 -m venv /var/www/html/.venv"])

        ctx.set_status("Instalando Django y conectores de base de datos...")
        pip_pkgs = "django"
        if ctx.db_type != "sqlite":
            pip_pkgs += " PyMySQL cryptography psycopg2-binary"
        ctx.run_cmd(["ddev", "exec", f"/var/www/html/.venv/bin/pip install {pip_pkgs}"])

        ctx.set_status("Generando estructura inicial de Django...")
        ctx.run_cmd(["ddev", "exec", "/var/www/html/.venv/bin/django-admin startproject app ."])

        ctx.set_status("Configurando base de datos y ALLOWED_HOSTS...")
        settings_py_path = os.path.join(ctx.target_dir, "app", "settings.py")
        if os.path.exists(settings_py_path):
            try:
                with open(settings_py_path, "r", encoding="utf-8") as sf:
                    s_code = sf.read()
                s_code = s_code.replace("ALLOWED_HOSTS = []", "ALLOWED_HOSTS = ['*']")
                if ctx.db_type == "sqlite":
                    pass
                elif "postgres" in ctx.db_type:
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
                    s_code = re.sub(r'DATABASES\s*=\s*\{.*?\n\}', db_block, s_code, flags=re.DOTALL)
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
                with open(settings_py_path, "w", encoding="utf-8") as sf:
                    sf.write(s_code)
            except Exception as ex:
                ctx.log(f"Nota en settings.py: {ex}")

        ctx.set_status("Ejecutando migraciones de base de datos...")
        ctx.run_cmd(["ddev", "exec", "/var/www/html/.venv/bin/python manage.py migrate"])

        if ctx.auto_install:
            ctx.set_status("Creando superusuario administrador (admin / admin)...")
            superuser_script = (
                "from django.contrib.auth import get_user_model; "
                "User = get_user_model(); "
                "User.objects.filter(username='admin').exists() or "
                "User.objects.create_superuser('admin', 'admin@example.com', 'admin')"
            )
            ctx.run_cmd(["ddev", "exec", f'/var/www/html/.venv/bin/python manage.py shell -c "{superuser_script}"'])
            ctx.log("\n👑 Superusuario creado: admin / admin (Panel en /admin)")

        ctx.set_status("Configurando Nginx Reverse Proxy y daemon de fondo...")
        self.setup_nginx_proxy(ctx, port=8000)
        self.setup_daemon(ctx, name="django", command="/var/www/html/.venv/bin/python manage.py runserver 0.0.0.0:8000")

        self.restart_ddev(ctx, "Reiniciando servidor DDEV para activar Django...")
        ctx.log("\n🎉 Proyecto Django listo y corriendo!")


class FlaskRecipe(BaseRecipe):
    fw_id = "flask"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="generic",
            docroot=".",
            db_type=ctx.db_type,
            extra_args=["--webimage-extra-packages=python3-venv,python3-pip"]
        )
        self.start_ddev(ctx)

        ctx.set_status("Creando entorno virtual Python (.venv)...")
        ctx.run_cmd(["ddev", "exec", "python3 -m venv /var/www/html/.venv"])

        ctx.set_status("Instalando Flask y conectores...")
        ctx.run_cmd(["ddev", "exec", "/var/www/html/.venv/bin/pip install flask pymysql psycopg2-binary cryptography python-dotenv"])

        ctx.set_status("Creando aplicación inicial app.py...")
        app_py_path = os.path.join(ctx.target_dir, "app.py")
        flask_code = f"""from flask import Flask, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = \"\"\"<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ctx.slug} - Flask en DDEV</title>
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
        <p>Tu aplicación <b>{ctx.slug}</b> con microframework Flask está corriendo exitosamente.</p>
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
        with open(app_py_path, "w", encoding="utf-8") as f:
            f.write(flask_code)

        ctx.set_status("Configurando Nginx Reverse Proxy y daemon de fondo...")
        self.setup_nginx_proxy(ctx, port=5000)
        self.setup_daemon(ctx, name="flask", command="/var/www/html/.venv/bin/python app.py")

        self.restart_ddev(ctx, "Reiniciando servidor DDEV para activar Flask...")
        ctx.log("\n🎉 Proyecto Flask listo y corriendo!")
