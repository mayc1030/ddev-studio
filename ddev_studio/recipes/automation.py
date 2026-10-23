# -*- coding: utf-8 -*-
"""
Recetas de scaffolding para herramientas de Automatización y Agentes de IA:
n8n (Workflow Automation) y OpenClaw (Autonomous AI Agent Gateway).
"""

import os

from ddev_studio.recipes.base import BaseRecipe
from ddev_studio.recipes.context import RecipeContext


class N8nRecipe(BaseRecipe):
    """
    Estrategia de aprovisionamiento para n8n Workflow Automation.
    Configura DDEV con Node.js 22, proxy reverso hacia el puerto 5678,
    variables de entorno para webhooks/HTTPS y daemon de ejecución en segundo plano.
    """
    fw_id = "n8n"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="generic",
            docroot=".",
            node_version="24",
            db_type="none",
            extra_args=[
                f"--web-environment-add=N8N_PORT=5678,N8N_EDITOR_BASE_URL=https://{ctx.slug}.ddev.site/,WEBHOOK_URL=https://{ctx.slug}.ddev.site/,N8N_PROTOCOL=https",
                "--webimage-extra-packages=python3-setuptools,build-essential"
            ]
        )
        self.start_ddev(ctx)

        ctx.set_status("Inicializando espacio de trabajo para n8n...")
        ctx.run_cmd(["ddev", "exec", "npm", "init", "-y"])

        ctx.set_status("Instalando plataforma n8n (compilando módulos nativos C++)...")
        ctx.run_cmd(["ddev", "exec", "npm", "install", "n8n@latest", "--save"])

        ctx.set_status("Configurando Nginx Reverse Proxy y daemon en segundo plano...")
        self.setup_nginx_proxy(ctx, port=5678)
        self.setup_daemon(ctx, name="n8n-server", command="bash -lc 'npx n8n start'")

        self.restart_ddev(ctx, "Reiniciando DDEV para activar el servidor n8n...")
        ctx.log(f"\n🎉 ¡n8n instalado y listo en https://{ctx.slug}.ddev.site!")


class OpenClawRecipe(BaseRecipe):
    """
    Estrategia de aprovisionamiento para OpenClaw AI Agent Gateway.
    Configura DDEV con Node.js 22, proxy reverso hacia el puerto 18789,
    soporte de estado persistente, conexión directa a Ollama y daemon de servicio.
    """
    fw_id = "openclaw"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="generic",
            docroot=".",
            node_version="22",
            db_type="none",
            extra_args=[
                "--web-environment-add=OPENCLAW_GATEWAY_PORT=18789,OPENCLAW_STATE_DIR=/var/www/html/.openclaw,OLLAMA_BASE_URL=http://host.docker.internal:11434",
                "--webimage-extra-packages=python3-setuptools,build-essential"
            ]
        )
        self.start_ddev(ctx)

        ctx.set_status("Inicializando entorno de agente para OpenClaw...")
        ctx.run_cmd(["ddev", "exec", "npm", "init", "-y"])

        ctx.set_status("Instalando framework OpenClaw...")
        ctx.run_cmd(["ddev", "exec", "npm", "install", "openclaw@latest", "--save"])

        ctx.set_status("Configurando Nginx Reverse Proxy y daemon en segundo plano...")
        self.setup_nginx_proxy(ctx, port=18789)
        self.setup_daemon(ctx, name="openclaw-gateway", command="bash -lc 'npx openclaw gateway --port 18789'")

        self.restart_ddev(ctx, "Reiniciando DDEV para activar el gateway de OpenClaw...")
        ctx.log(f"\n🎉 ¡OpenClaw instalado y listo en https://{ctx.slug}.ddev.site!")
