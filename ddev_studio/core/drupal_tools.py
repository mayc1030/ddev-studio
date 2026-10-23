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
        "entity_usage": False,
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
        "entity_usage": [r"\bentity_usage\b", r"\bentity\s+usage\b"],
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


def build_starterkit_theme_command(
    machine_name: str,
    name: str = "",
    docroot: str = "web",
    subsite_url: str = ""
) -> list:
    """
    Construye el comando resiliente para generar un tema Starterkit en Drupal (Drupal 10, 11+).
    Detecta dinámicamente si se debe invocar vendor/bin/dr o core/scripts/drupal según la versión y estructura,
    y asegura la colocación en themes/custom y reconstrucción de caché con drush cr.
    """
    clean_docroot = (docroot or "web").strip().strip("/")
    safe_name = name.replace("'", "\\'") if name else machine_name
    uri_flag = f"--uri={subsite_url} " if subsite_url else ""
    script_sh = (
        f'if [ -f "vendor/bin/dr" ]; then '
        f'vendor/bin/dr generate-theme {machine_name} --name=\'{safe_name}\' --path=themes/custom; '
        f'elif [ -f "{clean_docroot}/core/scripts/drupal" ]; then '
        f'php {clean_docroot}/core/scripts/drupal generate-theme {machine_name} --name=\'{safe_name}\' --path=themes/custom; '
        f'elif [ -f "core/scripts/drupal" ]; then '
        f'php core/scripts/drupal generate-theme {machine_name} --name=\'{safe_name}\' --path=themes/custom; '
        f'else '
        f'echo "Error: el generador Starterkit requiere Drupal 10 o Drupal 11 (o 9.3+). Para Drupal 8 usa la opción \'Subtema Clásico\'." >&2; exit 1; '
        f'fi && drush {uri_flag}cr'
    )
    return ["ddev", "exec", "bash", "-c", script_sh]


DRUPAL_BASE_THEMES_PRESETS = {
    "olivero": {
        "label": "Olivero (Core - Drupal 10/11 Estándar)",
        "base_theme": "olivero",
        "composer_pkg": None,
        "is_core": True,
        "type": "frontend",
        "regions": {
            "header": "Header",
            "primary_menu": "Primary menu",
            "secondary_menu": "Secondary menu",
            "breadcrumb": "Breadcrumb",
            "highlighted": "Highlighted",
            "content": "Content",
            "sidebar": "Sidebar",
            "footer_top": "Footer Top",
            "footer_bottom": "Footer Bottom",
        },
    },
    "bootstrap5": {
        "label": "Bootstrap 5 (Limpio & Moderno - Contrib)",
        "base_theme": "bootstrap5",
        "composer_pkg": "drupal/bootstrap5",
        "is_core": False,
        "type": "frontend",
        "drush_gen_cmd": "bootstrap5:generate-subtheme",
        "regions": {
            "header": "Header",
            "nav_branding": "Navigation Branding",
            "nav_main": "Main Navigation",
            "breadcrumb": "Breadcrumb",
            "highlighted": "Highlighted",
            "content": "Content",
            "sidebar_first": "Sidebar First",
            "sidebar_second": "Sidebar Second",
            "footer": "Footer",
        },
    },
    "bootstrap_barrio": {
        "label": "Bootstrap Barrio (SASS & Avanzado - Contrib)",
        "base_theme": "bootstrap_barrio",
        "composer_pkg": "drupal/bootstrap_barrio",
        "is_core": False,
        "type": "frontend",
        "regions": {
            "top_header": "Top Header",
            "top_header_form": "Top Header Form",
            "header": "Header",
            "header_form": "Header Form",
            "primary_menu": "Primary menu",
            "secondary_menu": "Secondary menu",
            "page_top": "Page top",
            "page_bottom": "Page bottom",
            "highlighted": "Highlighted",
            "featured_top": "Featured top",
            "breadcrumb": "Breadcrumb",
            "content": "Content",
            "sidebar_first": "Sidebar first",
            "sidebar_second": "Sidebar second",
            "featured_bottom_first": "Featured bottom first",
            "featured_bottom_second": "Featured bottom second",
            "featured_bottom_third": "Featured bottom third",
            "footer_first": "Footer first",
            "footer_second": "Footer second",
            "footer_third": "Footer third",
            "footer_fourth": "Footer fourth",
            "footer_fifth": "Footer fifth",
        },
    },
    "radix": {
        "label": "Radix (Componentes SDC & Vite - Contrib)",
        "base_theme": "radix",
        "composer_pkg": "drupal/radix",
        "is_core": False,
        "type": "frontend",
        "drush_gen_cmd": "radix:create",
        "regions": {
            "navbar": "Navbar",
            "header": "Header",
            "breadcrumb": "Breadcrumb",
            "highlighted": "Highlighted",
            "content": "Content",
            "sidebar": "Sidebar",
            "footer": "Footer",
        },
    },
    "gin": {
        "label": "Gin Admin (Tema de Administración Moderno)",
        "base_theme": "gin",
        "composer_pkg": "drupal/gin",
        "is_core": False,
        "type": "admin",
        "regions": {
            "header": "Header",
            "pre_content": "Pre-content",
            "breadcrumb": "Breadcrumb",
            "highlighted": "Highlighted",
            "help": "Help",
            "content": "Content",
            "page_top": "Page top",
            "page_bottom": "Page bottom",
            "sidebar": "Sidebar",
        },
    },
    "claro": {
        "label": "Claro (Core - Administración Drupal 9/10/11)",
        "base_theme": "claro",
        "composer_pkg": None,
        "is_core": True,
        "type": "admin",
        "regions": {
            "header": "Header",
            "pre_content": "Pre-content",
            "breadcrumb": "Breadcrumb",
            "highlighted": "Highlighted",
            "help": "Help",
            "content": "Content",
            "page_top": "Page top",
            "page_bottom": "Page bottom",
            "sidebar": "Sidebar",
        },
    },
    "bartik": {
        "label": "Bartik (Core Legacy - Drupal 7 / 8)",
        "base_theme": "bartik",
        "composer_pkg": None,
        "is_core": True,
        "type": "frontend_legacy",
        "regions": {
            "header": "Header",
            "primary_menu": "Primary menu",
            "secondary_menu": "Secondary menu",
            "breadcrumb": "Breadcrumb",
            "highlighted": "Highlighted",
            "content": "Content",
            "sidebar_first": "Sidebar first",
            "sidebar_second": "Sidebar second",
            "footer": "Footer",
        },
    },
    "classy": {
        "label": "Classy (Core Legacy - Drupal 8 / 9)",
        "base_theme": "classy",
        "composer_pkg": None,
        "is_core": True,
        "type": "frontend_legacy",
        "regions": {
            "header": "Header",
            "primary_menu": "Primary menu",
            "secondary_menu": "Secondary menu",
            "breadcrumb": "Breadcrumb",
            "highlighted": "Highlighted",
            "content": "Content",
            "sidebar_first": "Sidebar first",
            "sidebar_second": "Sidebar second",
            "footer": "Footer",
        },
    },
    "custom": {
        "label": "Personalizado (Ingresar nombre manualmente...)",
        "base_theme": "",
        "composer_pkg": None,
        "is_core": False,
        "type": "custom",
        "regions": None,
    }
}


def is_theme_installed(approot: str, docroot: str = "web", theme_name: str = "") -> bool:
    """
    Comprueba si un tema base está instalado o presente en el proyecto Drupal,
    revisando en core/themes, themes/contrib, themes/custom o en composer.json.
    """
    if not approot or not theme_name:
        return False
    clean_docroot = (docroot or "web").strip().strip("/")

    # 1. Verificar directorios físicos
    check_dirs = [
        os.path.join(approot, clean_docroot, "core", "themes", theme_name),
        os.path.join(approot, clean_docroot, "themes", "contrib", theme_name),
        os.path.join(approot, clean_docroot, "themes", "custom", theme_name),
        os.path.join(approot, clean_docroot, "themes", theme_name),
        os.path.join(approot, "themes", "contrib", theme_name),
        os.path.join(approot, "themes", theme_name),
        os.path.join(approot, "core", "themes", theme_name),
    ]
    for d in check_dirs:
        if os.path.isdir(d):
            return True

    # 2. Verificar en composer.json si existe la dependencia
    composer_json = os.path.join(approot, "composer.json")
    if os.path.isfile(composer_json):
        try:
            with open(composer_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            reqs = data.get("require", {})
            dev_reqs = data.get("require-dev", {})
            pkg_target = f"drupal/{theme_name.replace('_', '-')}"
            pkg_target_under = f"drupal/{theme_name}"
            for r in (reqs, dev_reqs):
                if pkg_target in r or pkg_target_under in r or f"drupal/{theme_name}" in r:
                    return True
        except Exception:
            pass

    return False


def build_subtheme_command(
    machine_name: str,
    base_theme: str = "olivero",
    composer_pkg: str = None,
    install_base: bool = False,
    enable_theme: bool = True,
    set_as_default: bool = True,
    is_admin_theme: bool = False,
    subsite_url: str = ""
) -> list:
    """
    Construye la secuencia de comandos DDEV para requerir el paquete del tema base vía Composer
    (si es contrib y se solicita), habilitar el tema base, habilitar el nuevo subtema,
    establecerlo opcionalmente como predeterminado y reconstruir la caché de Drupal.
    """
    uri_flag = f"--uri={subsite_url} " if subsite_url else ""
    steps = []

    if install_base and composer_pkg:
        steps.append(f"composer require '{composer_pkg}'")
        if base_theme:
            steps.append(f"drush {uri_flag}theme:enable {base_theme} -y")

    if enable_theme and machine_name:
        steps.append(f"drush {uri_flag}theme:enable {machine_name} -y")
        if set_as_default:
            config_key = "admin" if is_admin_theme else "default"
            steps.append(f"drush {uri_flag}config-set system.theme {config_key} {machine_name} -y")

    steps.append(f"drush {uri_flag}cr")

    script_sh = " && ".join(steps)
    return ["ddev", "exec", "bash", "-c", script_sh]


def scaffold_custom_module(
    approot: str,
    docroot: str,
    machine_name: str,
    name: str,
    description: str = "",
    package: str = "Custom",
    has_install: bool = False,
    has_permissions: bool = False
) -> list:
    """
    Crea la estructura de archivos estándar para un módulo personalizado de Drupal 10/11.
    Retorna la lista de rutas relativas de los archivos creados.
    """
    created_files = []
    if not approot or not machine_name:
        return created_files

    docroot = docroot or "web"
    mod_dir = os.path.join(approot, docroot, "modules", "custom", machine_name)
    os.makedirs(mod_dir, exist_ok=True)

    name = name or machine_name
    description = description or f"Módulo personalizado {name}."
    package = package or "Custom"

    # 1. .info.yml
    info_path = os.path.join(mod_dir, f"{machine_name}.info.yml")
    info_content = (
        f"name: '{name}'\n"
        f"type: module\n"
        f"description: '{description}'\n"
        f"package: '{package}'\n"
        f"core_version_requirement: ^8 || ^9 || ^10 || ^11\n"
    )
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(info_content)
    created_files.append(os.path.relpath(info_path, approot))

    # 2. .module
    mod_path = os.path.join(mod_dir, f"{machine_name}.module")
    mod_content = (
        "<?php\n\n"
        "/**\n"
        f" * @file\n"
        f" * Primary module hooks for {name} module.\n"
        " */\n\n"
        "use Drupal\\Core\\Routing\\RouteMatchInterface;\n\n"
        "/**\n"
        " * Implements hook_help().\n"
        " */\n"
        f"function {machine_name}_help($route_name, RouteMatchInterface $route_match) {{\n"
        "  switch ($route_name) {\n"
        f"    case 'help.page.{machine_name}':\n"
        f"      return '<p>' . t('{description}') . '</p>';\n"
        "  }\n"
        "}\n"
    )
    with open(mod_path, "w", encoding="utf-8") as f:
        f.write(mod_content)
    created_files.append(os.path.relpath(mod_path, approot))

    # 3. .install (opcional)
    if has_install:
        inst_path = os.path.join(mod_dir, f"{machine_name}.install")
        inst_content = (
            "<?php\n\n"
            "/**\n"
            " * @file\n"
            f" * Install, update and uninstall functions for the {name} module.\n"
            " */\n\n"
            "/**\n"
            " * Implements hook_install().\n"
            " */\n"
            f"function {machine_name}_install() {{\n"
            f"  \\Drupal::messenger()->addStatus(t('Module {name} has been installed.'));\n"
            "}\n\n"
            "/**\n"
            " * Implements hook_uninstall().\n"
            " */\n"
            f"function {machine_name}_uninstall() {{\n"
            f"  \\Drupal::messenger()->addStatus(t('Module {name} has been uninstalled.'));\n"
            "}\n"
        )
        with open(inst_path, "w", encoding="utf-8") as f:
            f.write(inst_content)
        created_files.append(os.path.relpath(inst_path, approot))

    # 4. .permissions.yml (opcional)
    if has_permissions:
        perm_path = os.path.join(mod_dir, f"{machine_name}.permissions.yml")
        perm_content = (
            f"administer {machine_name}:\n"
            f"  title: 'Administer {name}'\n"
            f"  description: 'Perform administration tasks for {name} module.'\n"
            f"  restrict access: true\n"
        )
        with open(perm_path, "w", encoding="utf-8") as f:
            f.write(perm_content)
        created_files.append(os.path.relpath(perm_path, approot))

    return created_files


def scaffold_custom_theme(
    approot: str,
    docroot: str,
    machine_name: str,
    name: str,
    base_theme: str = "olivero",
    regions: dict = None
) -> list:
    """
    Crea la estructura estándar para un tema/subtema personalizado de Drupal (Drupal 8, 9, 10, 11).
    Soporta presets específicos (Bootstrap 5, Barrio, Radix, Olivero, Gin, Claro, Bartik).
    Retorna la lista de rutas relativas de los archivos creados.
    """
    created_files = []
    if not approot or not machine_name:
        return created_files

    docroot = docroot or "web"
    thm_dir = os.path.join(approot, docroot, "themes", "custom", machine_name)
    os.makedirs(thm_dir, exist_ok=True)
    os.makedirs(os.path.join(thm_dir, "css"), exist_ok=True)
    os.makedirs(os.path.join(thm_dir, "js"), exist_ok=True)

    name = name or machine_name
    base_theme = base_theme or "olivero"

    # Resolver regiones según preset si no fueron provistas
    if regions is None:
        preset_info = DRUPAL_BASE_THEMES_PRESETS.get(base_theme)
        if preset_info and preset_info.get("regions"):
            regions = preset_info["regions"]
        else:
            regions = {
                "header": "Header",
                "primary_menu": "Primary menu",
                "secondary_menu": "Secondary menu",
                "breadcrumb": "Breadcrumb",
                "highlighted": "Highlighted",
                "content": "Content",
                "sidebar_first": "Sidebar first",
                "sidebar_second": "Sidebar second",
                "footer": "Footer",
            }

    regions_yaml = "regions:\n"
    for r_key, r_label in regions.items():
        regions_yaml += f"  {r_key}: '{r_label}'\n"

    # 1. .info.yml
    info_path = os.path.join(thm_dir, f"{machine_name}.info.yml")
    info_content = (
        f"name: '{name}'\n"
        f"type: theme\n"
        f"description: 'Tema personalizado {name} basado en {base_theme}.'\n"
        f"package: 'Custom'\n"
        f"core_version_requirement: ^8 || ^9 || ^10 || ^11\n"
        f"base theme: '{base_theme}'\n"
        f"libraries:\n"
        f"  - {machine_name}/global-styling\n\n"
        f"{regions_yaml}"
    )
    with open(info_path, "w", encoding="utf-8") as f:
        f.write(info_content)
    created_files.append(os.path.relpath(info_path, approot))

    # 2. .theme
    thm_path = os.path.join(thm_dir, f"{machine_name}.theme")
    thm_content = (
        "<?php\n\n"
        "/**\n"
        f" * @file\n"
        f" * Functions to support theming in the {name} theme.\n"
        " */\n"
    )
    with open(thm_path, "w", encoding="utf-8") as f:
        f.write(thm_content)
    created_files.append(os.path.relpath(thm_path, approot))

    # 3. .libraries.yml
    base_dep = ""
    if base_theme in ("bootstrap5", "bootstrap_barrio", "gin", "radix"):
        base_dep = f"  dependencies:\n    - {base_theme}/global-styling\n"

    lib_path = os.path.join(thm_dir, f"{machine_name}.libraries.yml")
    lib_content = (
        "global-styling:\n"
        "  version: 1.x\n"
        "  css:\n"
        "    theme:\n"
        "      css/style.css: {}\n"
        "  js:\n"
        "    js/script.js: {}\n"
        f"{base_dep}"
    )
    with open(lib_path, "w", encoding="utf-8") as f:
        f.write(lib_content)
    created_files.append(os.path.relpath(lib_path, approot))

    # 4. css/style.css
    css_path = os.path.join(thm_dir, "css", "style.css")
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(f"/* Estilos para el tema {name} */\n")
    created_files.append(os.path.relpath(css_path, approot))

    # 5. js/script.js
    js_path = os.path.join(thm_dir, "js", "script.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(f"// Scripts para el tema {name}\n")
    created_files.append(os.path.relpath(js_path, approot))

    return created_files


def scaffold_custom_component(
    approot: str,
    docroot: str,
    target_mod: str,
    cmp_type: str,
    cmp_name: str
) -> list:
    """
    Genera un componente Drupal (controller, form, service) dentro de un módulo personalizado.
    Retorna la lista de rutas relativas de los archivos creados o actualizados.
    """
    created_files = []
    if not approot or not target_mod or not cmp_name:
        return created_files

    docroot = docroot or "web"
    mod_dir = os.path.join(approot, docroot, "modules", "custom", target_mod)
    if not os.path.exists(mod_dir):
        alt_candidates = [
            os.path.join(approot, docroot, "modules", target_mod),
            os.path.join(approot, "modules", "custom", target_mod),
            os.path.join(approot, "modules", target_mod),
        ]
        for alt in alt_candidates:
            if os.path.exists(alt):
                mod_dir = alt
                break

    class_name = re.sub(r'[^a-zA-Z0-9_]', '', cmp_name)
    if not class_name:
        class_name = "CustomComponent"
    class_name = class_name[0].upper() + class_name[1:]

    slug = re.sub(r'[^a-z0-9_]', '_', cmp_name.lower()).strip('_')

    if cmp_type == "controller":
        src_dir = os.path.join(mod_dir, "src", "Controller")
        os.makedirs(src_dir, exist_ok=True)
        file_path = os.path.join(src_dir, f"{class_name}.php")
        content = (
            "<?php\n\n"
            f"namespace Drupal\\{target_mod}\\Controller;\n\n"
            "use Drupal\\Core\\Controller\\ControllerBase;\n\n"
            "/**\n"
            f" * Returns responses for {target_mod} routes.\n"
            " */\n"
            f"class {class_name} extends ControllerBase {{\n\n"
            "  /**\n"
            "   * Builds the response.\n"
            "   */\n"
            "  public function build(): array {\n"
            "    return [\n"
            f"      '#markup' => $this->t('Hello from {class_name}!'),\n"
            "    ];\n"
            "  }\n\n"
            "}\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        created_files.append(os.path.relpath(file_path, approot))

        routing_path = os.path.join(mod_dir, f"{target_mod}.routing.yml")
        routing_entry = (
            f"\n{target_mod}.{slug}:\n"
            f"  path: '/{target_mod}/{slug}'\n"
            f"  defaults:\n"
            f"    _controller: '\\Drupal\\{target_mod}\\Controller\\{class_name}::build'\n"
            f"    _title: '{class_name}'\n"
            f"  requirements:\n"
            f"    _permission: 'access content'\n"
        )
        with open(routing_path, "a" if os.path.exists(routing_path) else "w", encoding="utf-8") as f:
            f.write(routing_entry)
        created_files.append(os.path.relpath(routing_path, approot))

    elif cmp_type == "form":
        src_dir = os.path.join(mod_dir, "src", "Form")
        os.makedirs(src_dir, exist_ok=True)
        file_path = os.path.join(src_dir, f"{class_name}.php")
        content = (
            "<?php\n\n"
            f"namespace Drupal\\{target_mod}\\Form;\n\n"
            "use Drupal\\Core\\Form\\FormBase;\n"
            "use Drupal\\Core\\Form\\FormStateInterface;\n\n"
            "/**\n"
            f" * Provides a {target_mod} form.\n"
            " */\n"
            f"class {class_name} extends FormBase {{\n\n"
            "  /**\n"
            "   * {@inheritdoc}\n"
            "   */\n"
            "  public function getFormId(): string {\n"
            f"    return '{target_mod}_{slug}';\n"
            "  }\n\n"
            "  /**\n"
            "   * {@inheritdoc}\n"
            "   */\n"
            "  public function buildForm(array $form, FormStateInterface $form_state): array {\n"
            "    $form['message'] = [\n"
            "      '#type' => 'textarea',\n"
            "      '#title' => $this->t('Message'),\n"
            "      '#required' => TRUE,\n"
            "    ];\n\n"
            "    $form['actions'] = [\n"
            "      '#type' => 'actions',\n"
            "      'submit' => [\n"
            "        '#type' => 'submit',\n"
            "        '#value' => $this->t('Send'),\n"
            "      ],\n"
            "    ];\n\n"
            "    return $form;\n"
            "  }\n\n"
            "  /**\n"
            "   * {@inheritdoc}\n"
            "   */\n"
            "  public function submitForm(array &$form, FormStateInterface $form_state): void {\n"
            "    $this->messenger()->addStatus($this->t('The form has been submitted.'));\n"
            "  }\n\n"
            "}\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        created_files.append(os.path.relpath(file_path, approot))

        routing_path = os.path.join(mod_dir, f"{target_mod}.routing.yml")
        routing_entry = (
            f"\n{target_mod}.{slug}:\n"
            f"  path: '/{target_mod}/{slug}'\n"
            f"  defaults:\n"
            f"    _form: '\\Drupal\\{target_mod}\\Form\\{class_name}'\n"
            f"    _title: '{class_name}'\n"
            f"  requirements:\n"
            f"    _permission: 'access content'\n"
        )
        with open(routing_path, "a" if os.path.exists(routing_path) else "w", encoding="utf-8") as f:
            f.write(routing_entry)
        created_files.append(os.path.relpath(routing_path, approot))

    elif cmp_type == "service":
        src_dir = os.path.join(mod_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        file_path = os.path.join(src_dir, f"{class_name}.php")
        content = (
            "<?php\n\n"
            f"namespace Drupal\\{target_mod};\n\n"
            "/**\n"
            f" * Service {class_name}.\n"
            " */\n"
            f"class {class_name} {{\n\n"
            "  /**\n"
            "   * Construct.\n"
            "   */\n"
            "  public function __construct() {\n"
            "  }\n\n"
            "  /**\n"
            "   * Example method.\n"
            "   */\n"
            "  public function execute(): string {\n"
            f"    return 'Execution from {class_name}';\n"
            "  }\n\n"
            "}\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        created_files.append(os.path.relpath(file_path, approot))

        services_path = os.path.join(mod_dir, f"{target_mod}.services.yml")
        services_entry = (
            f"\nservices:\n"
            f"  {target_mod}.{slug}:\n"
            f"    class: Drupal\\{target_mod}\\{class_name}\n"
        )
        if not os.path.exists(services_path):
            with open(services_path, "w", encoding="utf-8") as f:
                f.write(services_entry.lstrip())
        else:
            with open(services_path, "a", encoding="utf-8") as f:
                f.write(f"  {target_mod}.{slug}:\n    class: Drupal\\{target_mod}\\{class_name}\n")
        created_files.append(os.path.relpath(services_path, approot))

    return created_files


def scaffold_rest_resource(
    approot: str,
    docroot: str,
    target_mod: str,
    plugin_id: str,
    label: str,
    canonical_url: str
) -> list:
    """
    Genera un plugin RestResource dentro de un módulo personalizado.
    Retorna la lista de rutas relativas de los archivos creados.
    """
    created_files = []
    if not approot or not target_mod or not plugin_id:
        return created_files

    docroot = docroot or "web"
    mod_dir = os.path.join(approot, docroot, "modules", "custom", target_mod)
    if not os.path.exists(mod_dir):
        alt_candidates = [
            os.path.join(approot, docroot, "modules", target_mod),
            os.path.join(approot, "modules", "custom", target_mod),
            os.path.join(approot, "modules", target_mod),
        ]
        for alt in alt_candidates:
            if os.path.exists(alt):
                mod_dir = alt
                break

    clean_id = re.sub(r'[^a-zA-Z0-9_]', '_', plugin_id.lower()).strip('_')
    class_name = "".join(part.capitalize() for part in clean_id.split("_")) + "Resource"
    canonical_url = canonical_url or f"/api/v1/{clean_id}"
    if not canonical_url.startswith("/"):
        canonical_url = "/" + canonical_url
    label = label or plugin_id

    src_dir = os.path.join(mod_dir, "src", "Plugin", "rest", "resource")
    os.makedirs(src_dir, exist_ok=True)

    file_path = os.path.join(src_dir, f"{class_name}.php")
    content = (
        "<?php\n\n"
        f"namespace Drupal\\{target_mod}\\Plugin\\rest\\resource;\n\n"
        "use Drupal\\rest\\Plugin\\ResourceBase;\n"
        "use Drupal\\rest\\ResourceResponse;\n"
        "use Symfony\\Component\\HttpFoundation\\Request;\n\n"
        "/**\n"
        f" * Represents {label} as a resource.\n"
        " *\n"
        " * @RestResource(\n"
        f" *   id = \"{clean_id}\",\n"
        f" *   label = @Translation(\"{label}\"),\n"
        " *   uri_paths = {\n"
        f" *     \"canonical\" = \"{canonical_url}\"\n"
        " *   }\n"
        " * )\n"
        " */\n"
        f"class {class_name} extends ResourceBase {{\n\n"
        "  /**\n"
        "   * Responds to GET requests.\n"
        "   */\n"
        "  public function get(): ResourceResponse {\n"
        "    $data = [\n"
        "      'status' => 'success',\n"
        f"      'message' => 'Hello from {clean_id} REST resource!',\n"
        "      'timestamp' => time(),\n"
        "    ];\n"
        "    return new ResourceResponse($data, 200);\n"
        "  }\n\n"
        "}\n"
    )
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    created_files.append(os.path.relpath(file_path, approot))
    return created_files


def get_drupal_uninstall_anchor(module_machine_name: str) -> str:
    """
    Retorna el ancla HTML de Drupal para el módulo en /admin/modules/uninstall.
    En Drupal, los guiones bajos se convierten en guiones medios (ej. 'simple_oauth' -> 'edit-uninstall-simple-oauth').
    """
    clean_name = module_machine_name.strip().replace('_', '-')
    return f"edit-uninstall-{clean_name}"


def get_drupal_uninstall_url(base_url: str, module_machine_name: str = "") -> str:
    """
    Construye la URL directa a la página de desinstalación de Drupal (/admin/modules/uninstall),
    opcionalmente posicionando en el módulo específico con su ancla.
    """
    base = base_url.rstrip("/") if base_url else ""
    if module_machine_name:
        anchor = get_drupal_uninstall_anchor(module_machine_name)
        return f"{base}/admin/modules/uninstall#{anchor}"
    return f"{base}/admin/modules/uninstall"


# =========================================================================
# REGISTRO CANÓNICO DE BUNDLES Y MÓDULOS ESENCIALES (DRUPAL 10 / 11)
# =========================================================================

DRUPAL_ESSENTIAL_BUNDLES = {
    "seo": {
        "id": "seo",
        "title": "🔍 Suite SEO & Posicionamiento en Buscadores",
        "desc": "Metatag (OpenGraph + Twitter Cards), Pathauto (URLs limpias), Token, Simple XML Sitemap y Redirects automáticos.",
        "btn_install_label": "📦 Instalar Suite SEO Completa",
        "success_msg": "¡Suite SEO completa instalada y configurada!",
        "cmd_template": (
            "composer require drupal/metatag drupal/pathauto drupal/token drupal/simple_sitemap drupal/redirect --no-interaction && "
            "drush {uri_flag}pm:enable metatag metatag_open_graph metatag_twitter_cards pathauto token simple_sitemap redirect -y && "
            "drush {uri_flag}cr"
        ),
        "extra_actions": [
            ("⚙️ Metatags", "/admin/config/search/metatag"),
            ("🔗 Patrones Pathauto", "/admin/config/search/path/patterns"),
            ("🗺️ Sitemap (/sitemap.xml)", "/sitemap.xml"),
        ],
        "modules": [
            {
                "machine_name": "token",
                "label": "Token",
                "composer_pkg": "drupal/token",
                "enable_modules": ["token"],
                "desc": "Tokens y reemplazo dinámico de patrones en URLs y metadatos.",
            },
            {
                "machine_name": "pathauto",
                "label": "Pathauto",
                "composer_pkg": "drupal/pathauto",
                "composer_deps": ["drupal/token"],
                "enable_modules": ["token", "pathauto"],
                "desc": "Generación automática y limpia de alias de URL amigables.",
            },
            {
                "machine_name": "metatag",
                "label": "Metatag",
                "composer_pkg": "drupal/metatag",
                "composer_deps": ["drupal/token"],
                "enable_modules": ["token", "metatag", "metatag_open_graph", "metatag_twitter_cards"],
                "desc": "Metaetiquetas estructuradas, OpenGraph y Twitter Cards para redes sociales.",
            },
            {
                "machine_name": "simple_sitemap",
                "label": "Simple Sitemap",
                "composer_pkg": "drupal/simple_sitemap",
                "enable_modules": ["simple_sitemap"],
                "desc": "Generador de mapas de sitio XML para indexación en Google.",
            },
            {
                "machine_name": "redirect",
                "label": "Redirect",
                "composer_pkg": "drupal/redirect",
                "enable_modules": ["redirect"],
                "desc": "Redirecciones 301 automáticas al modificar slugs o alias.",
            },
        ],
    },
    "paragraphs": {
        "id": "paragraphs",
        "title": "🧩 Arquitectura Modular & Paragraphs Suite",
        "desc": "Paragraphs, Paragraphs Library, Entity Usage, Field Group e Inline Entity Form para modelado de páginas por componentes reutilizables y serialización en APIs.",
        "btn_install_label": "📦 Instalar Paragraphs & Componentes",
        "success_msg": "¡Suite de Paragraphs y Componentes instalada!",
        "cmd_template": (
            "composer require drupal/paragraphs drupal/entity_reference_revisions drupal/field_group drupal/inline_entity_form drupal/entity_usage --no-interaction && "
            "drush {uri_flag}pm:enable paragraphs entity_usage paragraphs_library entity_reference_revisions field_group inline_entity_form -y && "
            "drush {uri_flag}cr"
        ),
        "extra_actions": [
            ("🧩 Paragraph Types", "/admin/structure/paragraphs_type"),
            ("📚 Paragraphs Library", "/admin/content/paragraphs-library"),
            ("📊 Entity Usage", "/admin/config/entity-usage"),
        ],
        "modules": [
            {
                "machine_name": "paragraphs",
                "label": "Paragraphs",
                "composer_pkg": "drupal/paragraphs",
                "composer_deps": ["drupal/entity_reference_revisions"],
                "enable_modules": ["entity_reference_revisions", "paragraphs"],
                "desc": "Modelado de páginas mediante componentes dinámicos modulares.",
            },
            {
                "machine_name": "paragraphs_library",
                "label": "Paragraphs Library",
                "composer_pkg": "drupal/paragraphs",
                "composer_deps": ["drupal/entity_reference_revisions"],
                "enable_modules": ["entity_reference_revisions", "paragraphs", "paragraphs_library"],
                "desc": "Biblioteca centralizada de párrafos globales reusables.",
            },
            {
                "machine_name": "field_group",
                "label": "Field Group",
                "composer_pkg": "drupal/field_group",
                "enable_modules": ["field_group"],
                "desc": "Agrupación visual de campos en pestañas, acordeones y fieldsets.",
            },
            {
                "machine_name": "entity_usage",
                "label": "Entity Usage",
                "composer_pkg": "drupal/entity_usage",
                "enable_modules": ["entity_usage"],
                "desc": "Rastreo de relaciones y uso de imágenes y entidades referenciadas.",
            },
            {
                "machine_name": "inline_entity_form",
                "label": "Inline Entity Form",
                "composer_pkg": "drupal/inline_entity_form",
                "enable_modules": ["inline_entity_form"],
                "desc": "Inserción y edición embebida de entidades en formularios de edición.",
            },
        ],
    },
    "admin_media": {
        "id": "admin_media",
        "title": "⚡ Administración Avanzada & Gestión de Medios (DX / UX)",
        "desc": "Admin Toolbar (Tools + Search multinivel), Focal Point (recortes inteligentes de imágenes) y soporte nativo para logotipos SVG.",
        "btn_install_label": "📦 Instalar Admin Toolbar & Medios",
        "success_msg": "¡Admin Toolbar, Focal Point y SVG Image instalados!",
        "cmd_template": (
            "composer require drupal/admin_toolbar drupal/focal_point drupal/crop drupal/svg_image --no-interaction && "
            "drush {uri_flag}pm:enable admin_toolbar admin_toolbar_tools admin_toolbar_search focal_point crop svg_image -y && "
            "drush {uri_flag}cr"
        ),
        "extra_actions": [
            ("⚙️ Admin Toolbar", "/admin/config/user-interface/admin-toolbar"),
            ("🎯 Focal Point", "/admin/config/media/crop-widget"),
        ],
        "modules": [
            {
                "machine_name": "admin_toolbar",
                "label": "Admin Toolbar",
                "composer_pkg": "drupal/admin_toolbar",
                "enable_modules": ["admin_toolbar", "admin_toolbar_tools", "admin_toolbar_search"],
                "desc": "Barra de navegación multinivel con búsqueda rápida de rutas.",
            },
            {
                "machine_name": "focal_point",
                "label": "Focal Point",
                "composer_pkg": "drupal/focal_point",
                "composer_deps": ["drupal/crop"],
                "enable_modules": ["crop", "focal_point"],
                "desc": "Recorte inteligente de imágenes basado en punto de interés focal.",
            },
            {
                "machine_name": "crop",
                "label": "Crop API",
                "composer_pkg": "drupal/crop",
                "enable_modules": ["crop"],
                "desc": "API base para gestión y almacenamiento de recortes de medios.",
            },
            {
                "machine_name": "svg_image",
                "label": "SVG Image",
                "composer_pkg": "drupal/svg_image",
                "enable_modules": ["svg_image"],
                "desc": "Soporte nativo para gráficos vectoriales SVG en campos de imagen.",
            },
        ],
    },
    "api_headless": {
        "id": "api_headless",
        "title": "🌐 Suite de APIs REST, JSON:API & Headless (Decoupled)",
        "desc": "JSON:API (Core), JSON:API Extras (personalización de esquemas), Simple OAuth (tokens JWT para React/Vue/Next.js), REST Core y GraphQL.",
        "btn_install_label": "📦 Instalar Suite de APIs & OAuth",
        "success_msg": "¡Suite de APIs REST, JSON:API Extras y Simple OAuth instalados!",
        "cmd_template": (
            "composer require drupal/jsonapi_extras drupal/simple_oauth --no-interaction && "
            "drush {uri_flag}pm:enable jsonapi jsonapi_extras simple_oauth -y && "
            "drush {uri_flag}cr"
        ),
        "extra_actions": [
            ("🌐 Probar /jsonapi", "/jsonapi"),
            ("⚙️ JSON:API Extras", "/admin/config/services/jsonapi"),
            ("🗝️ Generar Claves RSA", "rsa_keys"),
        ],
        "modules": [
            {
                "machine_name": "jsonapi",
                "label": "JSON:API",
                "composer_pkg": None,  # Módulo nativo del Core de Drupal
                "enable_modules": ["jsonapi"],
                "desc": "Especificación JSON:API nativa del núcleo sin dependencias externas.",
            },
            {
                "machine_name": "jsonapi_extras",
                "label": "JSON:API Extras",
                "composer_pkg": "drupal/jsonapi_extras",
                "enable_modules": ["jsonapi", "jsonapi_extras"],
                "desc": "Configuración de recursos, alias y anulación de campos en endpoints.",
            },
            {
                "machine_name": "simple_oauth",
                "label": "Simple OAuth",
                "composer_pkg": "drupal/simple_oauth",
                "enable_modules": ["simple_oauth"],
                "desc": "Servidor OAuth 2.0 con tokens Bearer JWT para frontend desacoplado.",
            },
        ],
    },
    "devel_stage": {
        "id": "devel_stage",
        "title": "🐞 Depuración, Consola PHP & Rendimiento Local (DDEV)",
        "desc": "Devel + Kint, Consola PHP interactiva (/devel/php) y Stage File Proxy (descarga de imágenes bajo demanda desde producción).",
        "btn_install_label": "📦 Instalar Devel + Stage File Proxy",
        "success_msg": "¡Devel, Kint y Stage File Proxy instalados con éxito!",
        "cmd_template": (
            "composer require --dev drupal/devel drupal/devel_php kint-php/kint drupal/stage_file_proxy --no-interaction && "
            "drush {uri_flag}pm:enable devel devel_php stage_file_proxy -y && "
            "drush {uri_flag}cr"
        ),
        "extra_actions": [
            ("⚡ Abrir Consola PHP (/devel/php)", "/devel/php"),
            ("🖼️ Stage File Proxy", "/admin/config/development/stage_file_proxy"),
        ],
        "modules": [
            {
                "machine_name": "devel",
                "label": "Devel",
                "composer_pkg": "drupal/devel",
                "composer_deps": ["kint-php/kint"],
                "is_dev": True,
                "enable_modules": ["devel"],
                "desc": "Herramientas de inspección, depuración y perfilado de rendimiento.",
            },
            {
                "machine_name": "devel_php",
                "label": "Devel PHP",
                "composer_pkg": "drupal/devel_php",
                "is_dev": True,
                "enable_modules": ["devel_php"],
                "desc": "Consola interactiva para ejecutar código PHP directamente en el navegador.",
            },
            {
                "machine_name": "stage_file_proxy",
                "label": "Stage File Proxy",
                "composer_pkg": "drupal/stage_file_proxy",
                "is_dev": True,
                "enable_modules": ["stage_file_proxy"],
                "desc": "Descarga de medios e imágenes bajo demanda desde un entorno remoto.",
            },
        ],
    },
}


def build_module_install_command(module_info: dict, uri: str = "") -> list:
    """
    Construye la lista de argumentos para ejecutar la instalación de un único módulo
    en Drupal mediante Composer (si aplica) y Drush (pm:enable y cr).
    Soporta subsitios Drupal mediante el parámetro uri.
    """
    uri_flag = f"--uri={uri} " if uri else ""
    composer_pkg = module_info.get("composer_pkg")
    deps = module_info.get("composer_deps", [])
    
    pkgs = []
    if composer_pkg:
        pkgs.append(composer_pkg)
    for d in deps:
        if d not in pkgs:
            pkgs.append(d)
            
    enable_modules = module_info.get("enable_modules") or [module_info.get("machine_name", "")]
    enable_str = " ".join(enable_modules)
    
    parts = []
    if pkgs:
        dev_flag = "--dev " if module_info.get("is_dev", False) else ""
        pkgs_str = " ".join(pkgs)
        parts.append(f"composer require {dev_flag}{pkgs_str} --no-interaction")
        
    parts.append(f"drush {uri_flag}pm:enable {enable_str} -y")
    parts.append(f"drush {uri_flag}cr")
    
    cmd_str = " && ".join(parts)
    return ["ddev", "exec", "bash", "-c", cmd_str]


def build_bundle_install_command(bundle_info: dict, uri: str = "") -> list:
    """
    Construye la lista de argumentos para ejecutar la instalación completa de un
    paquete/suite de Drupal mediante Composer y Drush.
    """
    uri_flag = f"--uri={uri} " if uri else ""
    raw_template = bundle_info.get("cmd_template")
    if raw_template:
        cmd_str = raw_template.format(uri_flag=uri_flag)
        return ["ddev", "exec", "bash", "-c", cmd_str]
        
    pkgs_prod = []
    pkgs_dev = []
    modules_to_enable = []
    
    for mod in bundle_info.get("modules", []):
        pkg = mod.get("composer_pkg")
        deps = mod.get("composer_deps", [])
        is_dev = mod.get("is_dev", False)
        target_list = pkgs_dev if is_dev else pkgs_prod
        
        if pkg and pkg not in target_list:
            target_list.append(pkg)
        for d in deps:
            if d not in target_list:
                target_list.append(d)
                
        for m in (mod.get("enable_modules") or [mod.get("machine_name", "")]):
            if m and m not in modules_to_enable:
                modules_to_enable.append(m)
                
    parts = []
    if pkgs_prod:
        parts.append(f"composer require {' '.join(pkgs_prod)} --no-interaction")
    if pkgs_dev:
        parts.append(f"composer require --dev {' '.join(pkgs_dev)} --no-interaction")
    if modules_to_enable:
        parts.append(f"drush {uri_flag}pm:enable {' '.join(modules_to_enable)} -y")
    parts.append(f"drush {uri_flag}cr")
    
    return ["ddev", "exec", "bash", "-c", " && ".join(parts)]


def build_module_uninstall_command(module_info: dict, uri: str = "") -> list:
    """
    Construye la lista de argumentos para desinstalar un módulo en Drupal
    mediante Drush (pm:uninstall) y reconstruir la caché (cr).
    Soporta subsitios Drupal mediante el parámetro uri.
    """
    machine_name = module_info.get("machine_name", "")
    modules_to_uninstall = module_info.get("enable_modules") or ([machine_name] if machine_name else [])
    modules_to_uninstall = [m for m in modules_to_uninstall if m]
    if not modules_to_uninstall:
        return []

    uri_flag = f"--uri={uri} " if uri else ""
    # Desinstalar en orden inverso si hay submódulos (ej. dependiente antes del padre)
    uninst_str = " ".join(reversed(modules_to_uninstall))

    parts = [
        f"drush {uri_flag}pm:uninstall {uninst_str} -y",
        f"drush {uri_flag}cr",
    ]
    return ["ddev", "exec", "bash", "-c", " && ".join(parts)]


