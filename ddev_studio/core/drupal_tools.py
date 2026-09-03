# -*- coding: utf-8 -*-
"""
Utilidades y helpers de bajo nivel para Drupal: Drush code generation,
escaneo de módulos/temas custom y suite de APIs (JSON:API, REST, Simple OAuth).
"""

import json
import os
import re
import subprocess


def sanitize_machine_name(raw_name: str) -> str:
    """
    Sanitiza un string para convertirlo en un machine name válido para Drupal
    (solo letras minúsculas, números y guiones bajos).
    """
    if not raw_name:
        return ""
    slug = str(raw_name).strip().lower()
    slug = slug.replace("-", "_").replace(" ", "_")
    slug = re.sub(r'[^a-z0-9_]', '_', slug)
    slug = re.sub(r'_+', '_', slug)
    return slug.strip('_')


def scan_custom_modules(approot: str, docroot: str = "web") -> list:
    """
    Escanea los directorios de módulos personalizados en el proyecto y retorna
    una lista de nombres de módulos encontrados.
    """
    modules = []
    if not approot or not os.path.exists(approot):
        return modules

    candidates = [
        os.path.join(approot, docroot or "web", "modules", "custom"),
        os.path.join(approot, docroot or "web", "modules"),
        os.path.join(approot, "modules", "custom"),
        os.path.join(approot, "modules"),
        os.path.join(approot, "sites", "all", "modules", "custom"),
        os.path.join(approot, "sites", "all", "modules"),
    ]

    seen = set()
    for base_dir in candidates:
        if os.path.isdir(base_dir):
            try:
                for entry in sorted(os.listdir(base_dir)):
                    entry_path = os.path.join(base_dir, entry)
                    if os.path.isdir(entry_path) and not entry.startswith((".", "contrib", "devel")):
                        # Verificar si contiene un archivo .info.yml o .info
                        has_info = any(f.endswith((".info.yml", ".info")) for f in os.listdir(entry_path))
                        if (has_info or entry not in seen) and entry not in ["custom", "contrib"]:
                            seen.add(entry)
                            modules.append({
                                "name": entry,
                                "path": entry_path,
                                "rel_path": os.path.relpath(entry_path, approot)
                            })
            except Exception:
                pass

    return modules


def scan_custom_themes(approot: str, docroot: str = "web") -> list:
    """
    Escanea los directorios de temas personalizados en el proyecto y retorna
    una lista de temas encontrados.
    """
    themes = []
    if not approot or not os.path.exists(approot):
        return themes

    candidates = [
        os.path.join(approot, docroot or "web", "themes", "custom"),
        os.path.join(approot, docroot or "web", "themes"),
        os.path.join(approot, "themes", "custom"),
        os.path.join(approot, "themes"),
        os.path.join(approot, "sites", "all", "themes", "custom"),
        os.path.join(approot, "sites", "all", "themes"),
    ]

    seen = set()
    for base_dir in candidates:
        if os.path.isdir(base_dir):
            try:
                for entry in sorted(os.listdir(base_dir)):
                    entry_path = os.path.join(base_dir, entry)
                    if os.path.isdir(entry_path) and not entry.startswith((".", "contrib", "engines")):
                        has_info = any(f.endswith((".info.yml", ".info")) for f in os.listdir(entry_path))
                        if (has_info or entry not in seen) and entry not in ["custom", "contrib"]:
                            seen.add(entry)
                            themes.append({
                                "name": entry,
                                "path": entry_path,
                                "rel_path": os.path.relpath(entry_path, approot)
                            })
            except Exception:
                pass

    return themes


def parse_pm_list_output(raw_output: str) -> dict:
    """
    Parsea la salida JSON o textual de `drush pm:list` y retorna un diccionario
    con el estado (True/False) de módulos clave de API y desarrollo.
    """
    status_map = {
        # SEO Suite
        "metatag": False,
        "pathauto": False,
        "token": False,
        "simple_sitemap": False,
        "redirect": False,
        # Architecture & Paragraphs
        "paragraphs": False,
        "paragraphs_library": False,
        "field_group": False,
        "inline_entity_form": False,
        # Admin & Media
        "admin_toolbar": False,
        "admin_toolbar_tools": False,
        "admin_toolbar_search": False,
        "focal_point": False,
        "crop": False,
        "svg_image": False,
        # APIs & Headless
        "jsonapi": False,
        "jsonapi_extras": False,
        "rest": False,
        "restui": False,
        "simple_oauth": False,
        "graphql": False,
        "basic_auth": False,
        "serialization": False,
        # Dev & Local
        "devel": False,
        "devel_php": False,
        "devel_kint_pages": False,
        "stage_file_proxy": False,
    }

    if not raw_output or not raw_output.strip():
        return status_map

    # Intento 1: Parsear como JSON
    try:
        data = json.loads(raw_output)
        if isinstance(data, dict):
            for k, info in data.items():
                k_clean = k.lower().replace("-", "_")
                if k_clean in status_map:
                    if isinstance(info, dict):
                        st = str(info.get("status", "")).lower()
                        status_map[k_clean] = (st in ["enabled", "enabled\n", "1", "true"])
                    elif isinstance(info, str):
                        status_map[k_clean] = (info.lower() in ["enabled", "1", "true"])
            return status_map
    except Exception:
        pass

    # Intento 2: Parsear líneas de texto estándar de Drush pm:list
    alias_patterns = {
        # SEO
        "metatag": [r"\bmetatag\b"],
        "pathauto": [r"\bpathauto\b"],
        "token": [r"\btoken\b"],
        "simple_sitemap": [r"\bsimple_sitemap\b", r"\bsimple\s+sitemap\b", r"\bsimple-sitemap\b"],
        "redirect": [r"\bredirect\b"],
        # Paragraphs & Architecture
        "paragraphs": [r"\bparagraphs\b"],
        "paragraphs_library": [r"\bparagraphs_library\b", r"\bparagraphs\s+library\b"],
        "field_group": [r"\bfield_group\b", r"\bfield\s+group\b"],
        "inline_entity_form": [r"\binline_entity_form\b", r"\binline\s+entity\s+form\b"],
        # Admin & Media
        "admin_toolbar": [r"\badmin_toolbar\b", r"\badmin\s+toolbar\b"],
        "admin_toolbar_tools": [r"\badmin_toolbar_tools\b"],
        "admin_toolbar_search": [r"\badmin_toolbar_search\b"],
        "focal_point": [r"\bfocal_point\b", r"\bfocal\s+point\b"],
        "crop": [r"\bcrop\b"],
        "svg_image": [r"\bsvg_image\b", r"\bsvg\s+image\b"],
        # APIs
        "jsonapi": [r"\bjsonapi\b", r"\bjson:api\b"],
        "jsonapi_extras": [r"\bjsonapi_extras\b", r"\bjsonapi\s+extras\b"],
        "rest": [r"\brest\b"],
        "restui": [r"\brestui\b", r"\brest_ui\b"],
        "serialization": [r"\bserialization\b"],
        "simple_oauth": [r"\bsimple_oauth\b", r"\bsimple\s+oauth\b", r"\bsimple-oauth\b"],
        "graphql": [r"\bgraphql\b"],
        "basic_auth": [r"\bbasic_auth\b", r"\bbasic\s+auth\b"],
        # Dev & Local
        "devel": [r"\bdevel\b"],
        "devel_php": [r"\bdevel_php\b", r"\bdevel\s+php\b", r"\bdevel-php\b"],
        "devel_kint_pages": [r"\bdevel_kint_pages\b", r"\bkint\b"],
        "stage_file_proxy": [r"\bstage_file_proxy\b", r"\bstage\s+file\s+proxy\b"],
    }

    for line in raw_output.splitlines():
        line_lower = line.lower()
        is_enabled = any(k in line_lower for k in ["enabled", "habilitado", "active"])
        if is_enabled:
            for mod_key, patterns in alias_patterns.items():
                for pat in patterns:
                    if re.search(pat, line_lower):
                        status_map[mod_key] = True
                        break

    return status_map


def check_drupal_api_status(approot: str, uri: str = "") -> dict:
    """
    Ejecuta `ddev drush pm:list --status=enabled --format=json` en el proyecto
    (o para un subsitio si se especifica uri) para obtener el estado actual de las extensiones API.
    """
    if not approot or not os.path.exists(approot):
        return parse_pm_list_output("")

    cmd = ["ddev", "drush"]
    if uri:
        cmd.append(f"--uri={uri}")
    cmd.extend(["pm:list", "--status=enabled", "--format=json"])

    try:
        res = subprocess.run(
            cmd,
            cwd=approot,
            capture_output=True,
            text=True,
            timeout=10
        )
        if res.returncode == 0 and res.stdout:
            return parse_pm_list_output(res.stdout)
    except Exception:
        pass

    return parse_pm_list_output("")


def build_drush_generate_command(generator_id: str, answers: dict = None) -> list:
    """
    Construye la lista de argumentos para ejecutar `ddev drush generate <generator_id>`
    con respuestas JSON opcionales para modo no interactivo.
    """
    cmd = ["ddev", "drush", "generate", generator_id]
    if answers:
        answers_json = json.dumps(answers)
        cmd.append(f"--answers={answers_json}")
    return cmd
