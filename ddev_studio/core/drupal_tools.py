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
        f"core_version_requirement: ^9 || ^10 || ^11\n"
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
    base_theme: str = "olivero"
) -> list:
    """
    Crea la estructura estándar para un tema personalizado de Drupal 10/11.
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

    # 1. .info.yml
    info_path = os.path.join(thm_dir, f"{machine_name}.info.yml")
    info_content = (
        f"name: '{name}'\n"
        f"type: theme\n"
        f"description: 'Tema personalizado {name} basado en {base_theme}.'\n"
        f"package: 'Custom'\n"
        f"core_version_requirement: ^9 || ^10 || ^11\n"
        f"base theme: '{base_theme}'\n"
        f"libraries:\n"
        f"  - {machine_name}/global-styling\n\n"
        f"regions:\n"
        f"  header: 'Header'\n"
        f"  primary_menu: 'Primary menu'\n"
        f"  secondary_menu: 'Secondary menu'\n"
        f"  breadcrumb: 'Breadcrumb'\n"
        f"  highlighted: 'Highlighted'\n"
        f"  content: 'Content'\n"
        f"  sidebar_first: 'Sidebar first'\n"
        f"  sidebar_second: 'Sidebar second'\n"
        f"  footer: 'Footer'\n"
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
    lib_path = os.path.join(thm_dir, f"{machine_name}.libraries.yml")
    lib_content = (
        "global-styling:\n"
        "  version: 1.x\n"
        "  css:\n"
        "    theme:\n"
        "      css/style.css: {}\n"
        "  js:\n"
        "    js/script.js: {}\n"
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

