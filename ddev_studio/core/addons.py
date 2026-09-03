# -*- coding: utf-8 -*-
"""
Módulo core para la gestión del catálogo, inspección e instalación de Add-ons de DDEV.
"""

import json
import os
import re
import subprocess
from typing import List, Dict, Tuple, Optional


# Catálogo fallback integrado con los Add-ons oficiales y más populares de DDEV
FALLBACK_ADDONS = [
    {
        "title": "ddev/ddev-redis",
        "name": "ddev-redis",
        "user": "ddev",
        "description": "Servidor de caché y almacenamiento en memoria Redis para sesiones, colas y alto rendimiento.",
        "type": "official",
        "category": "db_cache",
        "github_url": "https://github.com/ddev/ddev-redis",
        "stars": 150,
        "tag_name": "v1.2.0"
    },
    {
        "title": "ddev/ddev-solr",
        "name": "ddev-solr",
        "user": "ddev",
        "description": "Motor de búsqueda empresarial Apache Solr preconfigurado para Drupal (Search API) y WordPress.",
        "type": "official",
        "category": "search",
        "github_url": "https://github.com/ddev/ddev-solr",
        "stars": 85,
        "tag_name": "v1.2.1"
    },
    {
        "title": "ddev/ddev-cron",
        "name": "ddev-cron",
        "user": "ddev",
        "description": "Ejecución desatendida y periódica de tareas cron en segundo plano dentro del contenedor web.",
        "type": "official",
        "category": "devops",
        "github_url": "https://github.com/ddev/ddev-cron",
        "stars": 90,
        "tag_name": "v1.2.1"
    },
    {
        "title": "ddev/ddev-browsersync",
        "name": "ddev-browsersync",
        "user": "ddev",
        "description": "Sincronización en vivo de archivos CSS, JavaScript y recarga automática del navegador (Live Reload).",
        "type": "official",
        "category": "frontend_dx",
        "github_url": "https://github.com/ddev/ddev-browsersync",
        "stars": 110,
        "tag_name": "v1.1.2"
    },
    {
        "title": "ddev/ddev-phpmyadmin",
        "name": "ddev-phpmyadmin",
        "user": "ddev",
        "description": "Interfaz web clásica y completa para la administración gráfica de MySQL y MariaDB.",
        "type": "official",
        "category": "db_cache",
        "github_url": "https://github.com/ddev/ddev-phpmyadmin",
        "stars": 95,
        "tag_name": "v1.1.0"
    },
    {
        "title": "ddev/ddev-adminer",
        "name": "ddev-adminer",
        "user": "ddev",
        "description": "Gestor ultra-ligero en un único archivo PHP para MySQL, MariaDB, PostgreSQL y SQLite.",
        "type": "official",
        "category": "db_cache",
        "github_url": "https://github.com/ddev/ddev-adminer",
        "stars": 70,
        "tag_name": "v1.0.8"
    },
    {
        "title": "ddev/ddev-elasticsearch",
        "name": "ddev-elasticsearch",
        "user": "ddev",
        "description": "Motor de búsqueda distribuido y analítica NoSQL Elasticsearch con soporte RESTful.",
        "type": "official",
        "category": "search",
        "github_url": "https://github.com/ddev/ddev-elasticsearch",
        "stars": 60,
        "tag_name": "v1.2.0"
    },
    {
        "title": "ddev/ddev-memcached",
        "name": "ddev-memcached",
        "user": "ddev",
        "description": "Sistema distribuido de almacenamiento en caché en memoria de objetos de alta velocidad.",
        "type": "official",
        "category": "db_cache",
        "github_url": "https://github.com/ddev/ddev-memcached",
        "stars": 45,
        "tag_name": "v1.1.1"
    },
    {
        "title": "ddev/ddev-mongo",
        "name": "ddev-mongo",
        "user": "ddev",
        "description": "Base de datos NoSQL líder orientada a documentos para aplicaciones Node.js, Python y PHP.",
        "type": "official",
        "category": "db_cache",
        "github_url": "https://github.com/ddev/ddev-mongo",
        "stars": 40,
        "tag_name": "v1.0.3"
    },
    {
        "title": "ddev/ddev-rabbitmq",
        "name": "ddev-rabbitmq",
        "user": "ddev",
        "description": "Broker de mensajería asíncrona AMQP y gestor de colas con panel web de administración.",
        "type": "official",
        "category": "devops",
        "github_url": "https://github.com/ddev/ddev-rabbitmq",
        "stars": 35,
        "tag_name": "v1.0.2"
    },
    {
        "title": "ddev/ddev-selenium-standalone-chrome",
        "name": "ddev-selenium-standalone-chrome",
        "user": "ddev",
        "description": "Contenedor Selenium WebDriver con navegador Chrome para pruebas automatizadas E2E y Behat/Nightwatch.",
        "type": "official",
        "category": "testing",
        "github_url": "https://github.com/ddev/ddev-selenium-standalone-chrome",
        "stars": 65,
        "tag_name": "v1.0.5"
    },
    {
        "title": "ddev/ddev-playwright",
        "name": "ddev-playwright",
        "user": "ddev",
        "description": "Servicio de automatización de pruebas y screenshots con Playwright para pruebas E2E modernas.",
        "type": "contrib",
        "category": "testing",
        "github_url": "https://github.com/xima-media/ddev-playwright",
        "stars": 15,
        "tag_name": "v3.1.0"
    }
]

ADDON_CATEGORIES = [
    {"id": "all", "label": "Todos", "icon": "emblem-package-symbolic"},
    {"id": "official", "label": "Oficiales (ddev/*)", "icon": "emblem-default-symbolic"},
    {"id": "db_cache", "label": "Bases de Datos & Caché", "icon": "drive-harddisk-symbolic"},
    {"id": "search", "label": "Búsqueda (Solr / Elastic)", "icon": "system-search-symbolic"},
    {"id": "frontend_dx", "label": "Frontend & DX", "icon": "applications-graphics-symbolic"},
    {"id": "devops", "label": "Colas & Tareas (Cron/Rabbit)", "icon": "system-run-symbolic"},
    {"id": "testing", "label": "Testing & QA (Selenium/Playwright)", "icon": "utilities-system-monitor-symbolic"},
    {"id": "contrib", "label": "Comunidad (Contrib)", "icon": "system-users-symbolic"},
    {"id": "installed", "label": "Instalados en este proyecto", "icon": "emblem-ok-symbolic"}
]

KNOWN_ADDON_DESCRIPTIONS = {
    "ddev-redis": "Servidor de caché en memoria Redis ultra-rápido. Acelera consultas de base de datos, sesiones y colas en Drupal, WordPress o Laravel.",
    "ddev-solr": "Motor de indexación y búsqueda avanzada a gran escala. Ideal para Search API en Drupal y catálogos grandes de contenido.",
    "ddev-drupal-solr": "Servidor Apache Solr con núcleos y esquemas XML preconfigurados específicamente para Drupal 8, 9, 10 y 11.",
    "ddev-cron": "Ejecutor de tareas programadas en segundo plano. Corre drush cron, artisan schedule:run o wp cron periódicamente de forma automática.",
    "ddev-browsersync": "Herramienta Live Reload que recarga el navegador web automáticamente al editar archivos CSS, JS o plantillas Twig/Blade.",
    "ddev-phpmyadmin": "Panel web gráfico clásico para explorar, ejecutar consultas SQL e importar/exportar bases de datos MySQL y MariaDB.",
    "ddev-adminer": "Gestor de base de datos ultraligero en una sola página PHP con mínimo consumo de memoria para MySQL, Postgres y SQLite.",
    "ddev-elasticsearch": "Motor distribuido de búsqueda full-text y analítica NoSQL para grandes volúmenes de datos con API REST.",
    "ddev-opensearch": "Búsqueda y analítica distribuida de código abierto de alto rendimiento, alternativa moderna y libre a Elasticsearch.",
    "ddev-memcached": "Sistema de caché en memoria de alto rendimiento para almacenamiento temporal de objetos y fragmentos HTML.",
    "ddev-mongo": "Base de datos NoSQL líder orientada a documentos JSON para aplicaciones modernas, microservicios y Node.js.",
    "ddev-rabbitmq": "Broker de colas y mensajería asíncrona AMQP con panel web de métricas para desacoplar tareas pesadas en segundo plano.",
    "ddev-selenium-standalone-chrome": "Contenedor Selenium con Chrome headless para ejecutar pruebas funcionales automatizadas E2E, Nightwatch y Behat.",
    "ddev-playwright": "Entorno automatizado para pruebas E2E modernas y captura de screenshots en navegadores Chromium, Firefox y WebKit.",
    "ddev-wkhtmltopdf": "Utilidad de renderizado para convertir páginas HTML y CSS en documentos PDF de alta fidelidad.",
    "ddev-varnish": "Acelerador HTTP y proxy inverso de caché web para simular arquitecturas de producción de altísimo tráfico.",
    "ddev-blackfire": "Herramienta de profiling continuo para diagnosticar cuellos de botella de rendimiento, CPU y consumo de memoria en PHP.",
    "ddev-keycloak": "Servidor de gestión de identidad y accesos (IAM) con Single Sign-On (SSO), OAuth 2.0 y OpenID Connect.",
    "ddev-drupal-contrib": "Entorno optimizado para desarrollo y generación de parches para módulos y temas comunitarios de Drupal.org.",
    "ddev-typesense": "Motor de búsqueda instantánea ultrarrápido, tolerante a fallos tipográficos y muy fácil de configurar.",
    "ddev-meilisearch": "Motor de búsqueda 'search-as-you-type' ultraligero con ranking por relevancia listo para frontends modernos.",
    "ddev-dynamodb": "Emulador local de base de datos NoSQL Amazon DynamoDB para pruebas locales sin conexión a AWS.",
    "ddev-vitest": "Runner de pruebas unitarias ultrarrápido integrado con Vite para proyectos React, Vue y TypeScript.",
    "ddev-tailwind": "Compilador y watcher en vivo de Tailwind CSS para maquetación ágil de estilos en el proyecto.",
    "ddev-mailpit": "Capturador web de emails transaccionales en desarrollo local con visor de mensajes HTML y API REST.",
    "ddev-mailhog": "Servidor simulador de SMTP y visor web de correos salientes en desarrollo.",
    "ddev-directus": "Backend instantáneo y CMS Headless que envuelve tu base de datos SQL con APIs REST y GraphQL.",
    "ddev-strapi": "CMS Headless de código abierto basado en Node.js y React para gestión de contenidos con API REST.",
    "ddev-nextcloud-fpm": "Servidor Nextcloud optimizado con PHP-FPM y Nginx para almacenamiento y sincronización de archivos en la nube.",
    "ddev-civicrm-cli-tools": "Herramientas de línea de comandos para automatización y mantenimiento de CiviCRM con DDEV.",
    "ddev-farmos": "Distribución especializada farmOS para gestión agrícola y ambiental basada en Drupal.",
    "ddev-shopware-cli": "Herramientas de CLI y compilación de extensiones para la plataforma de comercio electrónico Shopware.",
}


def get_addon_description(title: str, raw_desc: str) -> str:
    """
    Retorna una descripción clara, detallada y en español de lo que hace el add-on.
    """
    title_lower = title.lower().strip()
    repo_name = title_lower.split("/")[-1]
    
    if repo_name in KNOWN_ADDON_DESCRIPTIONS:
        return KNOWN_ADDON_DESCRIPTIONS[repo_name]
    if title_lower in KNOWN_ADDON_DESCRIPTIONS:
        return KNOWN_ADDON_DESCRIPTIONS[title_lower]
        
    for k, v in KNOWN_ADDON_DESCRIPTIONS.items():
        if k in title_lower or k in repo_name:
            return v
            
    if raw_desc and len(raw_desc.strip()) > 5:
        return raw_desc.strip()
        
    return f"Extensión y servicio complementario '{repo_name}' para potenciar tu entorno DDEV."



def classify_addon_category(title: str, description: str, addon_type: str) -> str:
    """
    Clasifica heurísticamente un add-on en una categoría lógica para la interfaz de usuario.
    """
    text = (title + " " + (description or "")).lower()
    
    if any(k in text for k in ["redis", "memcached", "mongo", "mysql", "mariadb", "postgres", "adminer", "phpmyadmin", "dynamodb", "database"]):
        return "db_cache"
    elif any(k in text for k in ["solr", "elastic", "opensearch", "meilisearch", "typesense", "search"]):
        return "search"
    elif any(k in text for k in ["browsersync", "vite", "webpack", "tailwind", "storybook", "front", "theme", "reload"]):
        return "frontend_dx"
    elif any(k in text for k in ["selenium", "playwright", "behat", "cypress", "test", "quality", "phpstan", "phpcs"]):
        return "testing"
    elif any(k in text for k in ["cron", "queue", "rabbitmq", "worker", "deploy", "ansible", "sync"]):
        return "devops"
    
    return "contrib" if addon_type == "contrib" else "official"


def fetch_available_addons(timeout: int = 15) -> List[Dict]:
    """
    Obtiene la lista completa de add-ons disponibles en DDEV ejecutando `ddev get --list -j`.
    Si el comando falla o no hay conexión, retorna el catálogo fallback integrado.
    """
    try:
        res = subprocess.run(
            ["ddev", "get", "--list", "-j"],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if res.returncode == 0 and res.stdout.strip():
            raw_data = json.loads(res.stdout.strip())
            items = raw_data.get("raw", [])
            if isinstance(items, list) and len(items) > 0:
                addons = []
                for it in items:
                    title = it.get("title") or f"{it.get('user', '')}/{it.get('repo', '')}".strip("/")
                    if not title:
                        continue
                    raw_desc = it.get("description", "") or ""
                    desc = get_addon_description(title, raw_desc)
                    atype = it.get("type", "contrib")
                    category = classify_addon_category(title, desc, atype)
                    
                    addons.append({
                        "title": title,
                        "name": it.get("repo", title.split("/")[-1]),
                        "user": it.get("user", title.split("/")[0] if "/" in title else ""),
                        "description": desc,
                        "raw_description": raw_desc,
                        "type": atype,
                        "category": category,
                        "github_url": it.get("github_url", f"https://github.com/{title}"),
                        "stars": it.get("stars", 0),
                        "tag_name": it.get("tag_name", "latest")
                    })
                # Ordenar: primero oficiales, luego por estrellas descendente
                addons.sort(key=lambda a: (0 if a["type"] == "official" else 1, -a["stars"]))
                return addons
    except Exception:
        pass

    return list(FALLBACK_ADDONS)


def get_installed_addons(approot: str) -> List[str]:
    """
    Detecta los add-ons instalados en el proyecto inspeccionando `.ddev/` y mediante `ddev get --installed -j`.
    Retorna una lista de identificadores o títulos de los add-ons instalados.
    """
    installed = set()
    if not approot or not os.path.exists(approot):
        return list(installed)

    # 1. Ejecutar ddev get --installed -j
    try:
        res = subprocess.run(
            ["ddev", "get", "--installed", "-j"],
            cwd=approot,
            capture_output=True,
            text=True,
            timeout=10
        )
        if res.returncode == 0 and res.stdout.strip():
            raw = json.loads(res.stdout.strip())
            items = raw.get("raw", [])
            if isinstance(items, list):
                for it in items:
                    t = it.get("title") or it.get("name") or ""
                    if t:
                        installed.add(t.lower())
                        installed.add(t.split("/")[-1].lower())
    except Exception:
        pass

    # 2. Heurística en el sistema de archivos: .ddev/
    ddev_dir = os.path.join(approot, ".ddev")
    if os.path.isdir(ddev_dir):
        # 2a. Inspeccionar carpeta .ddev/addon-metadata
        addon_meta_dir = os.path.join(ddev_dir, "addon-metadata")
        if os.path.isdir(addon_meta_dir):
            try:
                for entry in os.listdir(addon_meta_dir):
                    installed.add(entry.lower())
                    if not entry.startswith("ddev-"):
                        installed.add(f"ddev-{entry}".lower())
            except Exception:
                pass

        # 2b. Inspeccionar docker-compose.*.yaml
        try:
            for f in os.listdir(ddev_dir):
                if f.startswith("docker-compose.") and f.endswith((".yaml", ".yml")):
                    service_name = f.replace("docker-compose.", "").replace(".yaml", "").replace(".yml", "")
                    if service_name not in ["full", "stdservices"]:
                        installed.add(service_name.lower())
                        installed.add(f"ddev-{service_name}".lower())
                        installed.add(f"ddev/ddev-{service_name}".lower())
        except Exception:
            pass

    return list(installed)


def is_addon_installed(addon_title: str, installed_list: List[str]) -> bool:
    """
    Comprueba de forma flexible si un add-on dado está en la lista de add-ons instalados.
    """
    if not installed_list:
        return False
        
    t_lower = addon_title.lower()
    short_name = t_lower.split("/")[-1]
    name_without_prefix = short_name.replace("ddev-", "")
    
    for inst in installed_list:
        inst_clean = inst.lower().strip()
        if (inst_clean == t_lower or 
            inst_clean == short_name or 
            inst_clean == name_without_prefix or
            f"ddev/{inst_clean}" == t_lower or
            f"ddev-{inst_clean}" == short_name):
            return True
            
    return False


def build_install_addon_command(addon_title: str) -> List[str]:
    """
    Genera el comando seguro para instalar un add-on en DDEV.
    """
    return ["ddev", "get", addon_title]


def build_remove_addon_command(addon_title: str) -> List[str]:
    """
    Genera el comando seguro para desinstalar un add-on en DDEV.
    """
    return ["ddev", "get", "--remove", addon_title]
