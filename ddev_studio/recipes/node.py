# -*- coding: utf-8 -*-
"""
Recetas de scaffolding para tecnologías basadas en Node.js y Frontend moderno:
Next.js (React App Router), React (Vite), Vue 3 (Vite) y Angular.
"""

import os

from ddev_studio.recipes.base import BaseRecipe
from ddev_studio.recipes.context import RecipeContext


class NextjsRecipe(BaseRecipe):
    fw_id = "nextjs"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="generic",
            docroot=".",
            node_version=ctx.node_version,
            db_type=ctx.db_type
        )
        self.start_ddev(ctx)

        ctx.set_status("Creando aplicación Next.js con App Router y Tailwind CSS...")
        ctx.run_cmd([
            "ddev", "npx", "--yes", "create-next-app@latest", "tmp-next",
            "--typescript",
            "--tailwind",
            "--eslint",
            "--app",
            "--src-dir",
            '--import-alias=@/*',
            "--use-npm"
        ])

        ctx.set_status("Organizando estructura del proyecto...")
        ctx.run_cmd(["ddev", "exec", "sh -c 'cp -a tmp-next/. . && rm -rf tmp-next'"])
        ctx.run_cmd(["ddev", "exec", "sed -i 's/\"dev\": \"next dev\"/\"dev\": \"next dev -H 0.0.0.0 -p 3000\"/g' package.json"])

        ctx.set_status("Configurando Nginx Reverse Proxy y daemon en segundo plano...")
        self.setup_nginx_proxy(ctx, port=3000)
        self.setup_daemon(ctx, name="nextjs-dev-server", command="npm run dev")

        self.restart_ddev(ctx, "Reiniciando DDEV para activar el servidor Next.js...")
        ctx.log("\n🎉 ¡Proyecto Next.js creado y ejecutándose en segundo plano!")


class ReactRecipe(BaseRecipe):
    fw_id = "react"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="generic",
            docroot=".",
            node_version=ctx.node_version,
            db_type=ctx.db_type
        )
        self.start_ddev(ctx)

        ctx.set_status("Creando plantilla React con Vite...")
        ctx.run_cmd(["ddev", "npx", "--yes", "create-vite@latest", "tmp-vite", "--template", "react-ts"])

        ctx.set_status("Organizando estructura del proyecto...")
        ctx.run_cmd(["ddev", "exec", "sh -c 'cp -a tmp-vite/. . && rm -rf tmp-vite'"])
        ctx.run_cmd(["ddev", "exec", "sed -i 's/\"dev\": \"vite\"/\"dev\": \"vite --host 0.0.0.0 --port 5173\"/g' package.json"])

        ctx.set_status("Configurando Vite para DDEV (allowedHosts y HMR)...")
        react_vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    hmr: {
      clientPort: 443,
    },
  },
})
"""
        vite_cfg_ts = os.path.join(ctx.target_dir, "vite.config.ts")
        with open(vite_cfg_ts, "w", encoding="utf-8") as f:
            f.write(react_vite_config)

        ctx.set_status("Instalando dependencias npm...")
        ctx.run_cmd(["ddev", "npm", "install"])

        ctx.set_status("Configurando Nginx Reverse Proxy y Live Dev Server...")
        self.setup_nginx_proxy(ctx, port=5173)
        self.setup_daemon(ctx, name="react-dev-server", command="npm run dev")

        self.restart_ddev(ctx, "Reiniciando DDEV para activar React Live Dev Server...")
        ctx.log("\n🎉 Proyecto React listo con Live Fast Refresh en segundo plano!")


class VueRecipe(BaseRecipe):
    fw_id = "vue"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="generic",
            docroot=".",
            node_version=ctx.node_version,
            db_type=ctx.db_type
        )
        self.start_ddev(ctx)

        ctx.set_status("Creando plantilla Vue 3 con Vite...")
        ctx.run_cmd(["ddev", "npx", "--yes", "create-vite@latest", "tmp-vite", "--template", "vue-ts"])

        ctx.set_status("Organizando estructura del proyecto...")
        ctx.run_cmd(["ddev", "exec", "sh -c 'cp -a tmp-vite/. . && rm -rf tmp-vite'"])
        ctx.run_cmd(["ddev", "exec", "sed -i 's/\"dev\": \"vite\"/\"dev\": \"vite --host 0.0.0.0 --port 5173\"/g' package.json"])

        ctx.set_status("Configurando Vite para DDEV (allowedHosts y HMR)...")
        vue_vite_config = """import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    allowedHosts: true,
    hmr: {
      clientPort: 443,
    },
  },
})
"""
        vite_cfg_ts = os.path.join(ctx.target_dir, "vite.config.ts")
        with open(vite_cfg_ts, "w", encoding="utf-8") as f:
            f.write(vue_vite_config)

        ctx.set_status("Instalando dependencias npm...")
        ctx.run_cmd(["ddev", "npm", "install"])

        ctx.set_status("Configurando Nginx Reverse Proxy y Live Dev Server...")
        self.setup_nginx_proxy(ctx, port=5173)
        self.setup_daemon(ctx, name="vue-dev-server", command="npm run dev")

        self.restart_ddev(ctx, "Reiniciando DDEV para activar Vue 3 Live Dev Server...")
        ctx.log("\n🎉 Proyecto Vue 3 listo con Live Fast Refresh en segundo plano!")


class AngularRecipe(BaseRecipe):
    fw_id = "angular"

    def execute(self, ctx: RecipeContext) -> None:
        self.configure_ddev(
            ctx,
            project_type="generic",
            docroot=".",
            node_version=ctx.node_version,
            db_type=ctx.db_type,
            extra_args=["--web-environment-add=NG_CLI_ANALYTICS=false"]
        )
        self.start_ddev(ctx)

        ctx.set_status("Creando proyecto Angular con @angular/cli...")
        ctx.run_cmd(["ddev", "exec", "NG_CLI_ANALYTICS=false npx -y @angular/cli new tmp-ng --routing --style=css --skip-git --defaults"])
        ctx.run_cmd(["ddev", "exec", "sh -c 'cp -a tmp-ng/. . && rm -rf tmp-ng'"])

        ctx.set_status("Configurando Nginx Reverse Proxy y Live Dev Server...")
        self.setup_nginx_proxy(ctx, port=4200)
        self.setup_daemon(ctx, name="angular", command="npx ng serve --host 0.0.0.0 --port 4200 --allowed-hosts")

        self.restart_ddev(ctx, "Reiniciando DDEV para activar Angular Live Dev Server...")
        ctx.log("\n🎉 Proyecto Angular listo y corriendo!")
