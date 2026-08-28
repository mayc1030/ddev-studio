# -*- coding: utf-8 -*-
"""
Diálogo de gestión de add-ons oficiales y contenedores secundarios de bases de datos
(CloudBeaver/DBeaver, phpMyAdmin, Adminer).
"""

import json
import os
import shutil
import subprocess
import threading
import webbrowser
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from ddev_studio.ui.dialogs.progress import ProgressDialog

CLOUDBEAVER_COMPOSE_TEMPLATE = """#ddev-generated
services:
  cloudbeaver:
    container_name: ddev-${DDEV_SITENAME}-cloudbeaver
    image: dbeaver/cloudbeaver:latest
    restart: "no"
    labels:
      com.ddev.site-name: ${DDEV_SITENAME}
      com.ddev.approot: ${DDEV_APPROOT}
    environment:
      - VIRTUAL_HOST=${DDEV_HOSTNAME}
      - HTTP_EXPOSE=8978:8978
      - HTTPS_EXPOSE=8979:8978
      - CB_SERVER_NAME=DDEV Studio (${DDEV_SITENAME})
      - CB_SERVER_URL=https://${DDEV_HOSTNAME}:8979
      - CB_ADMIN_NAME=ddev
      - CB_ADMIN_PASSWORD=ddev
      - CLOUDBEAVER_APP_ANONYMOUS_ACCESS_ENABLED=true
      - CLOUDBEAVER_APP_GRANT_CONNECTIONS_ACCESS_TO_ANONYMOUS_TEAM=true
      - CLOUDBEAVER_APP_SUPPORTS_CUSTOM_CONNECTIONS=true
    volumes:
      - "./cloudbeaver/workspace:/opt/cloudbeaver/workspace"
"""


class DBContainersDialog(Gtk.Dialog):
    def __init__(self, parent_view, approot, proj_name, primary_url):
        super().__init__(title="Gestores de Base de Datos en Docker", transient_for=parent_view.main_app, modal=True)
        self.set_default_size(600, 520)
        self.approot = approot
        self.proj_name = proj_name
        self.primary_url = primary_url
        self.parent_view = parent_view
        
        box = self.get_content_area()
        box.set_spacing(12)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        
        lbl_title = Gtk.Label()
        lbl_title.set_markup("<big><b>Gestores de Base de Datos en Contenedor (Docker)</b></big>")
        lbl_title.set_halign(Gtk.Align.START)
        box.pack_start(lbl_title, False, False, 0)
        
        lbl_desc = Gtk.Label()
        lbl_desc.set_markup(f"<small><span color='#94a3b8'>Ejecuta herramientas visuales de base de datos directamente dentro del entorno Docker de <b>{proj_name}</b>.\\nNo consumen RAM cuando el proyecto está apagado y no requieren instalar software en tu equipo.</span></small>")
        lbl_desc.set_halign(Gtk.Align.START)
        lbl_desc.set_line_wrap(True)
        box.pack_start(lbl_desc, False, False, 0)
        
        ddev_dir = os.path.join(approot, ".ddev")
        
        # 1. DBeaver in Docker (CloudBeaver)
        has_dbeaver = os.path.exists(os.path.join(ddev_dir, "docker-compose.cloudbeaver.yaml"))
        dbeaver_url = f"{primary_url}:8979"
        
        card_dbeaver = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_dbeaver.get_style_context().add_class("option-highlight-box" if has_dbeaver else "project-card")
        
        row_db1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_db1.pack_start(Gtk.Image.new_from_icon_name("drive-harddisk-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_db1_title = Gtk.Label(use_markup=True)
        lbl_db1_title.set_markup("<b>🐬 DBeaver en Docker (CloudBeaver)</b>")
        row_db1.pack_start(lbl_db1_title, False, False, 0)
        
        lbl_db1_st = Gtk.Label(label="HABILITADO" if has_dbeaver else "NO HABILITADO")
        lbl_db1_st.get_style_context().add_class("badge")
        lbl_db1_st.get_style_context().add_class("badge-running" if has_dbeaver else "badge-stopped")
        row_db1.pack_start(lbl_db1_st, False, False, 0)
        card_dbeaver.pack_start(row_db1, False, False, 0)
        
        lbl_db1_desc = Gtk.Label()
        lbl_db1_desc.set_markup("<small>La versión oficial de DBeaver Community en Docker. Editor SQL avanzado, diagramas ER y soporte multi-motor.</small>")
        lbl_db1_desc.set_line_wrap(True)
        lbl_db1_desc.set_halign(Gtk.Align.START)
        card_dbeaver.pack_start(lbl_db1_desc, False, False, 0)
        
        db_actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        if has_dbeaver:
            btn_open_db = Gtk.Button()
            b_op = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_op.pack_start(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_op.pack_start(Gtk.Label(label="Abrir DBeaver en Navegador (:8979)"), False, False, 0)
            btn_open_db.add(b_op)
            btn_open_db.get_style_context().add_class("btn-primary")
            btn_open_db.connect("clicked", lambda b, u=dbeaver_url: webbrowser.open(u))
            db_actions_row.pack_start(btn_open_db, False, False, 0)
            
            btn_rem_db = Gtk.Button(label="Deshabilitar DBeaver")
            btn_rem_db.connect("clicked", lambda b: self.toggle_dbeaver(False))
            db_actions_row.pack_start(btn_rem_db, False, False, 0)
        else:
            btn_act_db = Gtk.Button()
            b_ac = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_ac.pack_start(Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_ac.pack_start(Gtk.Label(label="Habilitar DBeaver en Docker (1 Clic)"), False, False, 0)
            btn_act_db.add(b_ac)
            btn_act_db.get_style_context().add_class("btn-primary")
            btn_act_db.connect("clicked", lambda b: self.toggle_dbeaver(True))
            db_actions_row.pack_start(btn_act_db, False, False, 0)
            
        card_dbeaver.pack_start(db_actions_row, False, False, 0)
        box.pack_start(card_dbeaver, False, False, 0)
        
        # 2. phpMyAdmin in DDEV
        has_pma = os.path.exists(os.path.join(ddev_dir, "docker-compose.phpmyadmin.yaml"))
        pma_url = f"{primary_url}:8037"
        
        card_pma = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_pma.get_style_context().add_class("option-highlight-box" if has_pma else "project-card")
        
        row_pma1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_pma1.pack_start(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_pma_title = Gtk.Label(use_markup=True)
        lbl_pma_title.set_markup("<b>🌐 phpMyAdmin</b>")
        row_pma1.pack_start(lbl_pma_title, False, False, 0)
        
        lbl_pma_st = Gtk.Label(label="HABILITADO" if has_pma else "NO HABILITADO")
        lbl_pma_st.get_style_context().add_class("badge")
        lbl_pma_st.get_style_context().add_class("badge-running" if has_pma else "badge-stopped")
        row_pma1.pack_start(lbl_pma_st, False, False, 0)
        card_pma.pack_start(row_pma1, False, False, 0)
        
        lbl_pma_desc = Gtk.Label()
        lbl_pma_desc.set_markup("<small>El gestor clásico de base de datos para MariaDB y MySQL. Interfaz intuitiva y completa.</small>")
        lbl_pma_desc.set_line_wrap(True)
        lbl_pma_desc.set_halign(Gtk.Align.START)
        card_pma.pack_start(lbl_pma_desc, False, False, 0)
        
        pma_actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        if has_pma:
            btn_open_pma = Gtk.Button()
            b_op_p = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_op_p.pack_start(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_op_p.pack_start(Gtk.Label(label="Abrir phpMyAdmin en Navegador (:8037)"), False, False, 0)
            btn_open_pma.add(b_op_p)
            btn_open_pma.get_style_context().add_class("btn-primary")
            btn_open_pma.connect("clicked", lambda b, u=pma_url: webbrowser.open(u))
            pma_actions_row.pack_start(btn_open_pma, False, False, 0)
            
            btn_rem_pma = Gtk.Button(label="Deshabilitar phpMyAdmin")
            btn_rem_pma.connect("clicked", lambda b: self.toggle_addon("phpmyadmin", False))
            pma_actions_row.pack_start(btn_rem_pma, False, False, 0)
        else:
            btn_act_pma = Gtk.Button()
            b_ac_p = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_ac_p.pack_start(Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_ac_p.pack_start(Gtk.Label(label="Habilitar phpMyAdmin en Docker (1 Clic)"), False, False, 0)
            btn_act_pma.add(b_ac_p)
            btn_act_pma.get_style_context().add_class("btn-primary")
            btn_act_pma.connect("clicked", lambda b: self.toggle_addon("phpmyadmin", True))
            pma_actions_row.pack_start(btn_act_pma, False, False, 0)
            
        card_pma.pack_start(pma_actions_row, False, False, 0)
        box.pack_start(card_pma, False, False, 0)
        
        # 3. Adminer in DDEV (Port 9101 HTTPS / 9100 HTTP)
        has_adm = os.path.exists(os.path.join(ddev_dir, "docker-compose.adminer.yaml"))
        adm_url = f"{primary_url}:9101"
        
        card_adm = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        card_adm.get_style_context().add_class("option-highlight-box" if has_adm else "project-card")
        
        row_adm1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row_adm1.pack_start(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.MENU), False, False, 0)
        lbl_adm_title = Gtk.Label(use_markup=True)
        lbl_adm_title.set_markup("<b>⚡ Adminer (Ultra Rápido &amp; Ligero)</b>")
        row_adm1.pack_start(lbl_adm_title, False, False, 0)
        
        lbl_adm_st = Gtk.Label(label="HABILITADO" if has_adm else "NO HABILITADO")
        lbl_adm_st.get_style_context().add_class("badge")
        lbl_adm_st.get_style_context().add_class("badge-running" if has_adm else "badge-stopped")
        row_adm1.pack_start(lbl_adm_st, False, False, 0)
        card_adm.pack_start(row_adm1, False, False, 0)
        
        lbl_adm_desc = Gtk.Label()
        lbl_adm_desc.set_markup("<small>Gestor de alto rendimiento y consumo casi nulo (&lt; 5 MB RAM). Compatible con MariaDB, MySQL y PostgreSQL.</small>")
        lbl_adm_desc.set_line_wrap(True)
        lbl_adm_desc.set_halign(Gtk.Align.START)
        card_adm.pack_start(lbl_adm_desc, False, False, 0)
        
        adm_actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        if has_adm:
            btn_open_adm = Gtk.Button()
            b_op_a = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_op_a.pack_start(Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_op_a.pack_start(Gtk.Label(label="Abrir Adminer en Navegador (:9101)"), False, False, 0)
            btn_open_adm.add(b_op_a)
            btn_open_adm.get_style_context().add_class("btn-primary")
            btn_open_adm.connect("clicked", lambda b, u=adm_url: webbrowser.open(u))
            adm_actions_row.pack_start(btn_open_adm, False, False, 0)
            
            btn_rem_adm = Gtk.Button(label="Deshabilitar Adminer")
            btn_rem_adm.connect("clicked", lambda b: self.toggle_addon("adminer", False))
            adm_actions_row.pack_start(btn_rem_adm, False, False, 0)
        else:
            btn_act_adm = Gtk.Button()
            b_ac_a = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            b_ac_a.pack_start(Gtk.Image.new_from_icon_name("system-software-install-symbolic", Gtk.IconSize.MENU), False, False, 0)
            b_ac_a.pack_start(Gtk.Label(label="Habilitar Adminer en Docker (1 Clic)"), False, False, 0)
            btn_act_adm.add(b_ac_a)
            btn_act_adm.get_style_context().add_class("btn-primary")
            btn_act_adm.connect("clicked", lambda b: self.toggle_addon("adminer", True))
            adm_actions_row.pack_start(btn_act_adm, False, False, 0)
            
        card_adm.pack_start(adm_actions_row, False, False, 0)
        box.pack_start(card_adm, False, False, 0)
        
        # Close button
        btn_close = Gtk.Button(label="Cerrar")
        btn_close.connect("clicked", lambda b: self.destroy())
        self.add_action_widget(btn_close, Gtk.ResponseType.CLOSE)
        
        self.show_all()

    def toggle_dbeaver(self, enable):
        self.destroy()
        cb_compose_file = os.path.join(self.approot, ".ddev", "docker-compose.cloudbeaver.yaml")
        cb_base_dir = os.path.join(self.approot, ".ddev", "cloudbeaver")
        dbeaver_dir = os.path.join(cb_base_dir, "workspace", "GlobalConfiguration", ".dbeaver")
        dialog = ProgressDialog(self.parent_view.main_app, title=f"DBeaver en Docker: {self.proj_name}")
        dialog.set_status("Configurando contenedor DBeaver (CloudBeaver)...")
        
        def task():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t)
                if enable:
                    log("🐬 Preparando configuración de DBeaver (CloudBeaver)...\n")
                    ddev_dir = os.path.join(self.approot, ".ddev")
                    subprocess.run(["docker", "run", "--rm", "-v", f"{ddev_dir}:/ddev", "alpine", "rm", "-rf", "/ddev/cloudbeaver"], check=False)
                    
                    os.makedirs(dbeaver_dir, mode=0o777, exist_ok=True)
                    os.chmod(cb_base_dir, 0o777)
                    os.chmod(os.path.join(cb_base_dir, "workspace"), 0o777)
                    os.chmod(os.path.join(cb_base_dir, "workspace", "GlobalConfiguration"), 0o777)
                    os.chmod(dbeaver_dir, 0o777)
                    
                    db_type = self.parent_view.raw_data.get("database_type", "mariadb")
                    is_pg = ("postgres" in db_type.lower())
                    
                    init_sources = {
                        "folders": {},
                        "connections": {
                            "ddev-database": {
                                "provider": "postgresql" if is_pg else "mysql",
                                "driver": "postgres-jdbc" if is_pg else "mariaDB",
                                "name": f"DDEV Database ({self.proj_name})",
                                "save-password": True,
                                "read-only": False,
                                "configuration": {
                                    "host": "db",
                                    "port": "5432" if is_pg else "3306",
                                    "database": "db",
                                    "url": "jdbc:postgresql://db:5432/db" if is_pg else "jdbc:mariadb://db:3306/db",
                                    "user": "db",
                                    "password": "db",
                                    "type": "dev",
                                    "auth-model": "native",
                                    "auth-properties": {
                                        "user": "db",
                                        "password": "db"
                                    },
                                    "handlers": {}
                                }
                            }
                        }
                    }
                    ds_path = os.path.join(dbeaver_dir, "data-sources.json")
                    with open(ds_path, "w", encoding="utf-8") as f:
                        json.dump(init_sources, f, indent=2)
                    os.chmod(ds_path, 0o666)
                    log("✓ Conexión a la base de datos pre-configurada (db:db@db).\n")
                    
                    with open(cb_compose_file, "w", encoding="utf-8") as f:
                        f.write(CLOUDBEAVER_COMPOSE_TEMPLATE)
                    log("✓ Archivo .ddev/docker-compose.cloudbeaver.yaml creado.\n")
                else:
                    log("🗑️ Eliminando configuración de DBeaver...\n")
                    if os.path.exists(cb_compose_file):
                        os.remove(cb_compose_file)
                    ddev_dir = os.path.join(self.approot, ".ddev")
                    subprocess.run(["docker", "run", "--rm", "-v", f"{ddev_dir}:/ddev", "alpine", "rm", "-rf", "/ddev/cloudbeaver"], check=False)
                    log("✓ Contenedor y workspace de DBeaver eliminados.\n")
                
                log("\n🔄 Reiniciando proyecto DDEV para aplicar cambios de contenedor...\n")
                p2 = subprocess.Popen(["ddev", "restart", "-y"], cwd=self.approot, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in iter(p2.stdout.readline, ''):
                    log(line)
                p2.stdout.close()
                p2.wait()
                
                db_url = f"{self.primary_url}:8979" if enable else ""
                GLib.idle_add(dialog.finish, True, f"DBeaver en Docker {'habilitado' if enable else 'deshabilitado'}", db_url, self.approot)
                GLib.idle_add(self.parent_view.refresh_details)
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error: {ex}", "", self.approot)
                
        threading.Thread(target=task, daemon=True).start()

    def toggle_addon(self, addon_id, enable):
        self.destroy()
        dialog = ProgressDialog(self.parent_view.main_app, title=f"{addon_id}: {self.proj_name}")
        dialog.set_status(f"{'Habilitando' if enable else 'Deshabilitando'} {addon_id}...")
        
        def task():
            try:
                def log(t):
                    GLib.idle_add(dialog.append_log, t)
                
                if enable:
                    log(f"📦 Instalando complemento oficial 'ddev get ddev/ddev-{addon_id}'...\n")
                    p = subprocess.Popen(["ddev", "get", f"ddev/ddev-{addon_id}"], cwd=self.approot, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in iter(p.stdout.readline, ''):
                        log(line)
                    p.stdout.close()
                    p.wait()
                else:
                    log(f"🗑️ Desinstalando complemento oficial {addon_id}...\n")
                    p = subprocess.Popen(["ddev", "add-on", "remove", addon_id], cwd=self.approot, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                    for line in iter(p.stdout.readline, ''):
                        log(line)
                    p.stdout.close()
                    p.wait()
                    
                    for f_name in [f"docker-compose.{addon_id}.yaml", f"docker-compose.{addon_id}_norouter.yaml"]:
                        f_path = os.path.join(self.approot, ".ddev", f_name)
                        if os.path.exists(f_path):
                            os.remove(f_path)
                    meta_dir = os.path.join(self.approot, ".ddev", "addon-metadata", addon_id)
                    if os.path.exists(meta_dir):
                        shutil.rmtree(meta_dir, ignore_errors=True)
                    log(f"✓ Archivos y metadatos de {addon_id} eliminados por completo.\n")
                
                log(f"\n🔄 Reiniciando proyecto DDEV...\n")
                p2 = subprocess.Popen(["ddev", "restart", "-y"], cwd=self.approot, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for line in iter(p2.stdout.readline, ''):
                    log(line)
                p2.stdout.close()
                p2.wait()
                
                target_url = f"{self.primary_url}:8037" if addon_id == "phpmyadmin" else f"{self.primary_url}:9101"
                GLib.idle_add(dialog.finish, True, f"{addon_id} {'habilitado con éxito' if enable else 'desinstalado con éxito'}", target_url if enable else "", self.approot)
                GLib.idle_add(self.parent_view.refresh_details)
            except Exception as ex:
                GLib.idle_add(dialog.finish, False, f"Error: {ex}", "", self.approot)
                
        threading.Thread(target=task, daemon=True).start()
