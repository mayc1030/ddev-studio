# -*- coding: utf-8 -*-
"""
Clase base y utilidades compartidas para las recetas de scaffolding DDEV.
"""

from abc import ABC, abstractmethod
import os
from typing import List, Optional

from ddev_studio.recipes.context import RecipeContext

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

NGINX_FULL_PROXY_TEMPLATE = '''#ddev-silent-no-warn
server {{
    listen 80 default_server;
    listen 443 ssl default_server;

    root /var/www/html;

    ssl_certificate /etc/ssl/certs/master.crt;
    ssl_certificate_key /etc/ssl/certs/master.key;

    include /etc/nginx/monitoring.conf;

    error_log /dev/stdout info;
    access_log /var/log/nginx/access.log;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }}

    include /etc/nginx/common.d/*.conf;
    include /mnt/ddev_config/nginx/*.conf;
}}
'''


class BaseRecipe(ABC):
    """
    Clase abstracta base para la estrategia de aprovisionamiento de un framework.
    """
    fw_id: str = "generic"

    @abstractmethod
    def execute(self, ctx: RecipeContext) -> None:
        """Ejecuta el aprovisionamiento específico del framework."""
        pass

    def configure_ddev(
        self,
        ctx: RecipeContext,
        project_type: str,
        docroot: str = ".",
        php_version: Optional[str] = None,
        node_version: Optional[str] = None,
        db_type: Optional[str] = None,
        extra_args: Optional[List[str]] = None
    ) -> None:
        """Configura el entorno DDEV mediante `ddev config`."""
        ctx.set_status(f"Configurando DDEV para {ctx.fw.get('name', project_type)}...")
        cfg_cmd = [
            "ddev", "config",
            f"--project-name={ctx.slug}",
            f"--project-type={project_type}",
            f"--docroot={docroot}",
        ]
        if php_version:
            cfg_cmd.append(f"--php-version={php_version}")
        if node_version:
            cfg_cmd.append(f"--nodejs-version={node_version}")

        effective_db = db_type if db_type is not None else ctx.db_type
        if effective_db in ["none", "sqlite"]:
            cfg_cmd.append("--omit-containers=db")
        elif effective_db:
            cfg_cmd.append(f"--database={effective_db}")

        if extra_args:
            cfg_cmd.extend(extra_args)

        ctx.run_cmd(cfg_cmd)

    def start_ddev(self, ctx: RecipeContext) -> None:
        """Inicia los contenedores DDEV."""
        ctx.set_status("Levantando contenedores DDEV...")
        ctx.run_cmd(["ddev", "start", "-y"])

    def restart_ddev(self, ctx: RecipeContext, status_msg: str = "Reiniciando DDEV...") -> None:
        """Reinicia los contenedores DDEV para aplicar configuraciones o daemons."""
        ctx.set_status(status_msg)
        ctx.run_cmd(["ddev", "restart", "-y"])

    def setup_nginx_proxy(self, ctx: RecipeContext, port: int) -> None:
        """Crea el archivo de configuración reverse proxy de Nginx para exponer servidores Node/Python."""
        nginx_full_dir = os.path.join(ctx.target_dir, ".ddev", "nginx_full")
        os.makedirs(nginx_full_dir, exist_ok=True)
        conf_path = os.path.join(nginx_full_dir, "nginx-site.conf")
        with open(conf_path, "w", encoding="utf-8") as nf:
            nf.write(NGINX_FULL_PROXY_TEMPLATE.format(port=port))

    def setup_daemon(self, ctx: RecipeContext, name: str, command: str, directory: str = "/var/www/html") -> None:
        """Configura un servicio en segundo plano persistente en `.ddev/config.daemon.yaml`."""
        daemon_path = os.path.join(ctx.target_dir, ".ddev", "config.daemon.yaml")
        with open(daemon_path, "w", encoding="utf-8") as df:
            df.write(f"""#ddev-silent-no-warn
web_extra_daemons:
  - name: {name}
    command: "{command}"
    directory: {directory}
""")

    def setup_sites_php(self, ctx: RecipeContext, docroot: str) -> None:
        """Configura el archivo sites.php para Drupal multisite con mapeo dinámico."""
        ctx.set_status("Configurando enrutador multisite dinámico sites.php...")
        sites_dir = os.path.join(ctx.target_dir, docroot, "sites") if docroot != "." else os.path.join(ctx.target_dir, "sites")
        os.makedirs(sites_dir, exist_ok=True)
        sites_php_file = os.path.join(sites_dir, "sites.php")
        with open(sites_php_file, "w", encoding="utf-8") as sf:
            sf.write(SITES_PHP_TEMPLATE)
        ctx.log("✓ Arquitectura Multisite habilitada en sites/sites.php con mapeo dinámico.")
