# -*- coding: utf-8 -*-
"""
Recetas de scaffolding para tecnologías basadas en PHP:
Drupal (11/10/9/8/7), WordPress, Laravel, Symfony y PHP Plano / HTML.
"""

import os
import re

from ddev_studio.recipes.base import BaseRecipe
from ddev_studio.recipes.context import RecipeContext


class DrupalRecipe(BaseRecipe):
    fw_id = "drupal"

    def execute(self, ctx: RecipeContext) -> None:
        d_ver = ctx.drupal_ver_info.get("id", "10")
        d_type = ctx.drupal_ver_info.get("type", "drupal10")
        d_docroot = ctx.drupal_ver_info.get("docroot", "web")

        self.configure_ddev(
            ctx,
            project_type=d_type,
            docroot=d_docroot,
            php_version=ctx.php_version,
            db_type=ctx.db_type
        )
        self.start_ddev(ctx)

        if d_ver in ["11", "10", "9"]:
            ctx.set_status(f"Descargando Drupal {d_ver} con Composer...")
            pkg = f"drupal/recommended-project:^{d_ver}"
            drush_pkg = "drush/drush:^11" if d_ver == "9" else "drush/drush"

            ctx.run_cmd(["ddev", "composer", "create-project", pkg, "."])
            ctx.set_status(f"Instalando Drush ({drush_pkg})...")
            ctx.run_cmd(["ddev", "composer", "require", drush_pkg])

            if ctx.auto_install:
                ctx.set_status("Instalando Drupal estándar con Drush...")
                inst_cmd = [
                    "ddev", "drush", "site:install", "standard",
                    "--account-name=admin",
                    "--account-pass=admin",
                    f"--site-name={ctx.slug.capitalize()}",
                    "-y"
                ]
                ctx.run_cmd(inst_cmd)
                ctx.log("\n🎉 Drupal instalado con éxito!")
                ctx.log("Credenciales: admin / admin")

        elif d_ver == "8":
            ctx.set_status("Descargando Drupal 8 con Composer...")
            ctx.run_cmd(["ddev", "composer", "create-project", "--no-install", "drupal/recommended-project:^8", "."])

            ctx.set_status("Configurando permisos de plugins en Composer (allow-plugins)...")
            ctx.run_cmd(["ddev", "composer", "config", "--no-plugins", "allow-plugins.composer/installers", "true"])
            ctx.run_cmd(["ddev", "composer", "config", "--no-plugins", "allow-plugins.drupal/core-composer-scaffold", "true"])
            ctx.run_cmd(["ddev", "composer", "config", "--no-plugins", "allow-plugins.drupal/core-project-message", "true"])
            ctx.run_cmd(["ddev", "composer", "config", "--no-plugins", "allow-plugins.dealerdirect/phpcodesniffer-composer-installer", "true"])

            ctx.set_status("Instalando dependencias de Drupal 8...")
            ctx.run_cmd(["ddev", "composer", "install"])

            ctx.set_status("Instalando Drush 10 para Drupal 8...")
            ctx.run_cmd(["ddev", "composer", "require", "drush/drush:^10"])

            if ctx.auto_install:
                ctx.set_status("Instalando Drupal 8 estándar con Drush...")
                inst_cmd = [
                    "ddev", "drush", "site:install", "standard",
                    "--account-name=admin",
                    "--account-pass=admin",
                    f"--site-name={ctx.slug.capitalize()}",
                    "-y"
                ]
                ctx.run_cmd(inst_cmd)
                ctx.log("\n🎉 Drupal 8 instalado!")
                ctx.log("Credenciales: admin / admin")

        elif d_ver == "7":
            ctx.set_status("Descargando Drupal 7 oficial desde drupal.org...")
            ctx.run_cmd(["ddev", "exec", "curl -fSL 'https://ftp.drupal.org/files/projects/drupal-7.101.tar.gz' -o /tmp/drupal7.tar.gz"])
            ctx.run_cmd(["ddev", "exec", "tar -xzf /tmp/drupal7.tar.gz --strip-components=1 -C /var/www/html"])
            ctx.run_cmd(["ddev", "exec", "rm -f /tmp/drupal7.tar.gz"])

            ctx.set_status("Instalando Drush 8 para Drupal 7...")
            ctx.run_cmd(["ddev", "composer", "require", "drush/drush:^8"])

            if ctx.auto_install:
                ctx.set_status("Instalando Drupal 7 estándar con Drush...")
                inst_cmd = [
                    "ddev", "drush", "site:install", "standard",
                    "--account-name=admin",
                    "--account-pass=admin",
                    f"--site-name={ctx.slug.capitalize()}",
                    "-y"
                ]
                ctx.run_cmd(inst_cmd)
                ctx.log("\n🎉 Drupal 7 instalado!")
                ctx.log("Credenciales: admin / admin")

        if ctx.is_multisite_enabled:
            self.setup_sites_php(ctx, d_docroot)


class WordPressRecipe(BaseRecipe):
    fw_id = "wordpress"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="wordpress",
            docroot=".",
            php_version=ctx.php_version,
            db_type=ctx.db_type
        )
        self.start_ddev(ctx)

        ctx.set_status("Descargando núcleo de WordPress...")
        ctx.run_cmd(["ddev", "wp", "core", "download"])

        if ctx.auto_install:
            ctx.set_status("Instalando base de datos y usuario admin...")
            install_cmd = [
                "ddev", "wp", "core", "install",
                f"--url=https://{ctx.slug}.ddev.site",
                f"--title={ctx.slug.capitalize()}",
                "--admin_user=admin",
                "--admin_password=admin",
                "--admin_email=admin@example.com",
                "--skip-email"
            ]
            ctx.run_cmd(install_cmd)
            ctx.log("\n🎉 WordPress instalado!")
            ctx.log("Credenciales: admin / admin")


class LaravelRecipe(BaseRecipe):
    fw_id = "laravel"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="laravel",
            docroot="public",
            php_version=ctx.php_version,
            db_type=ctx.db_type
        )
        self.start_ddev(ctx)

        ctx.set_status("Instalando Laravel con Composer...")
        ctx.run_cmd(["ddev", "composer", "create-project", "--prefer-dist", "laravel/laravel", "."])

        if ctx.db_type == "sqlite":
            ctx.set_status("Configurando conexión SQLite en .env...")
            env_file = os.path.join(ctx.target_dir, ".env")
            if os.path.exists(env_file):
                with open(env_file, "r", encoding="utf-8") as ef:
                    env_txt = ef.read()
                env_txt = re.sub(r'DB_CONNECTION=\w+', 'DB_CONNECTION=sqlite', env_txt)
                with open(env_file, "w", encoding="utf-8") as ef:
                    ef.write(env_txt)
            ctx.run_cmd(["ddev", "exec", "touch database/database.sqlite"])

        ctx.set_status("Ejecutando migraciones iniciales de base de datos...")
        ctx.run_cmd(["ddev", "exec", "php artisan migrate --force"])
        ctx.log("\n🎉 ¡Proyecto Laravel listo y conectado a la base de datos!")


class SymfonyRecipe(BaseRecipe):
    fw_id = "symfony"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="php",
            docroot="public",
            php_version=ctx.php_version,
            db_type=ctx.db_type
        )
        self.start_ddev(ctx)

        ctx.set_status("Descargando e instalando Symfony Skeleton...")
        ctx.run_cmd(["ddev", "composer", "create-project", "symfony/skeleton", "."])

        ctx.set_status("Instalando componentes web (webapp)...")
        ctx.run_cmd(["ddev", "composer", "require", "webapp", "-n"])

        ctx.set_status("Configurando conexión a base de datos DDEV...")
        env_local_file = os.path.join(ctx.target_dir, ".env.local")
        with open(env_local_file, "w", encoding="utf-8") as ef:
            ef.write('DATABASE_URL="mysql://db:db@db:3306/db?serverVersion=mariadb-10.11.8&charset=utf8mb4"\n')

        ctx.log("\n🎉 ¡Proyecto Symfony listo y conectado a la base de datos!")


class GenericPhpRecipe(BaseRecipe):
    fw_id = "php"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="php",
            docroot=".",
            php_version=ctx.php_version,
            db_type=ctx.db_type
        )

        index_path = os.path.join(ctx.target_dir, "index.php")
        if not os.path.exists(index_path):
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{ctx.slug} - DDEV Studio</title>
    <style>
        body {{ font-family: system-ui, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .card {{ background: #1e293b; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; max-width: 500px; }}
        h1 {{ color: #38bdf8; margin-top: 0; }}
        .badge {{ background: #0284c7; padding: 4px 12px; border-radius: 9999px; font-size: 0.85rem; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>¡Proyecto {ctx.slug} Activo! 🚀</h1>
        <p>Tu entorno DDEV está corriendo perfectamente</p>
        <p><span class="badge">PHP <?php echo phpversion(); ?></span></p>
    </div>
</body>
</html>""")

        self.start_ddev(ctx)
        ctx.log("\n🎉 Proyecto PHP listo!")
