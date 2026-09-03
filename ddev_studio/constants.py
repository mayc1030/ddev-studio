# -*- coding: utf-8 -*-
"""
Constantes, configuraciones y estilos CSS globales para DDEV Studio.
"""

import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(PACKAGE_DIR)

# Resolución dinámica de la carpeta de iconos
ICONS_DIR = os.path.join(APP_DIR, "icons")
if not os.path.exists(ICONS_DIR):
    installed_icons = os.path.expanduser("~/.local/share/ddev-manager/icons")
    if os.path.exists(installed_icons):
        ICONS_DIR = installed_icons
    else:
        ICONS_DIR = os.path.join(PACKAGE_DIR, "icons")

DEFAULT_SITES_DIR = os.path.expanduser("~/sites")

CUSTOM_CSS = b"""
.header-title {
    font-size: 16px;
    font-weight: bold;
}
.header-subtitle {
    font-size: 11px;
    opacity: 0.8;
}
.framework-card {
    border-radius: 12px;
    border: 2px solid rgba(128, 128, 128, 0.25);
    background: alpha(@theme_base_color, 0.6);
    padding: 14px;
    transition: all 200ms ease-in-out;
}
.framework-card:hover {
    border-color: @theme_selected_bg_color;
    background: alpha(@theme_selected_bg_color, 0.1);
}
.framework-card.selected {
    border-color: @theme_selected_bg_color;
    background: alpha(@theme_selected_bg_color, 0.18);
}
.segmented-btn {
    border-radius: 8px;
    padding: 6px 16px;
    font-weight: bold;
}
.segmented-btn:checked {
    background-color: #0284c7;
    color: white;
}
.segmented-mode-container {
    background: alpha(@theme_base_color, 0.6);
    border: 1px solid rgba(128, 128, 128, 0.25);
    border-radius: 12px;
    padding: 4px;
}
.segmented-mode-btn {
    border-radius: 8px;
    padding: 8px 22px;
    font-weight: 600;
    font-size: 13px;
    background: transparent;
    border: 1px solid transparent;
    color: @theme_text_color;
}
.segmented-mode-btn:checked {
    background-color: #0284c7;
    color: white;
    box-shadow: 0 2px 6px rgba(2, 132, 199, 0.35);
}
.segmented-mode-btn:hover:not(:checked) {
    background-color: alpha(@theme_selected_bg_color, 0.18);
}

.badge {
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: bold;
}
.badge-running {
    background-color: #10b981;
    color: white;
}
.badge-stopped {
    background-color: #6b7280;
    color: white;
}
.badge-paused {
    background-color: #f59e0b;
    color: white;
}
.badge-danger {
    background-color: #ef4444;
    color: white;
}
.badge-tech {
    background-color: alpha(@theme_selected_bg_color, 0.25);
    color: @theme_text_color;
}
.badge-multisite {
    background-color: #8b5cf6;
    color: white;
    font-weight: bold;
}
.badge-single-site {
    background-color: #0284c7;
    color: white;
    font-weight: 500;
}
.option-highlight-box {
    border-radius: 10px;
    border: 1px solid alpha(@theme_selected_bg_color, 0.4);
    background: alpha(@theme_selected_bg_color, 0.08);
    padding: 12px 16px;
}
.combo-filter {
    border-radius: 8px;
    font-weight: 500;
    font-size: 13px;
    padding: 2px 6px;
}
.btn-primary {
    background-color: #0284c7;
    color: white;
    font-weight: bold;
    border-radius: 8px;
    padding: 8px 18px;
}
.btn-primary:hover {
    background-color: #0369a1;
}
.console-view {
    font-family: 'Monospace', monospace;
    font-size: 11px;
    background-color: #1e1e1e;
    color: #e0e0e0;
    border-radius: 8px;
}
.project-card {
    border-radius: 10px;
    border: 1px solid rgba(128, 128, 128, 0.2);
    padding: 12px;
    margin-bottom: 8px;
    background: alpha(@theme_base_color, 0.4);
}
.project-card:hover {
    border-color: rgba(128, 128, 128, 0.4);
    background: alpha(@theme_base_color, 0.8);
}
.btn-drupal {
    background-color: alpha(#0678be, 0.15);
    color: @theme_text_color;
    border: 1px solid alpha(#0678be, 0.4);
    border-radius: 6px;
    padding: 3px 8px;
    font-weight: 500;
}
.btn-drupal:hover {
    background-color: alpha(#0678be, 0.3);
    border-color: #0678be;
}
.btn-quick {
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: bold;
}
.btn-quick-cache {
    background-color: alpha(#10b981, 0.15);
    color: @theme_text_color;
    border: 1px solid alpha(#10b981, 0.4);
}
.btn-quick-cache:hover {
    background-color: alpha(#10b981, 0.3);
    border-color: #10b981;
}
.btn-quick-login {
    background-color: alpha(#f59e0b, 0.15);
    color: @theme_text_color;
    border: 1px solid alpha(#f59e0b, 0.4);
}
.btn-quick-login:hover {
    background-color: alpha(#f59e0b, 0.3);
    border-color: #f59e0b;
}
.loader-card {
    border-radius: 14px;
    border: 1px solid rgba(56, 189, 248, 0.35);
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
    padding: 28px 24px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
}
.big-spinner {
    min-width: 48px;
    min-height: 48px;
}
.loader-spinner {
    min-width: 32px;
    min-height: 32px;
}
.loader-pbar progress {
    background-color: #0284c7;
    border-radius: 4px;
}
.loader-pbar trough {
    background-color: rgba(255, 255, 255, 0.08);
    border-radius: 4px;
    min-height: 4px;
}

.nav-bar-box {
    padding: 4px 2px;
    margin-bottom: 2px;
}
.btn-back {
    border-radius: 8px;
    font-weight: 600;
    padding: 6px 14px;
    background-color: alpha(@theme_selected_bg_color, 0.15);
}
.btn-back:hover {
    background-color: alpha(@theme_selected_bg_color, 0.3);
}
"""

FRAMEWORKS = [
    {
        "id": "drupal",
        "name": "Drupal",
        "category": "CMS Empresarial",
        "desc": "CMS potente y modular con Drush. Soporta versiones 11, 10, 9, 8 y 7.",
        "icon": "drupal.svg",
        "php": "8.3",
        "docroot": "web",
        "db": "mariadb:10.11",
    },
    {
        "id": "wordpress",
        "name": "WordPress",
        "category": "CMS",
        "desc": "El CMS más popular del mundo. Con WP-CLI y base de datos lista.",
        "icon": "wordpress.svg",
        "php": "8.2",
        "docroot": ".",
        "db": "mariadb:10.11",
    },
    {
        "id": "laravel",
        "name": "Laravel",
        "category": "PHP Framework",
        "desc": "Framework PHP elegante con Artisan, migraciones y docroot public.",
        "icon": "laravel.svg",
        "php": "8.3",
        "docroot": "public",
        "db": "mysql:8.0",
    },
    {
        "id": "django",
        "name": "Django",
        "category": "Python Framework",
        "desc": "Framework web de alto nivel en Python con ORM, admin y base de datos.",
        "icon": "django.svg",
        "php": "8.3",
        "docroot": ".",
        "db": "postgres:16",
    },
    {
        "id": "flask",
        "name": "Flask",
        "category": "Python Microframework",
        "desc": "Microframework ligero y flexible en Python para APIs y aplicaciones web.",
        "icon": "flask.svg",
        "php": "8.3",
        "docroot": ".",
        "db": "mariadb:10.11",
    },
    {
        "id": "angular",
        "name": "Angular",
        "category": "Frontend SPA",
        "desc": "Plataforma y framework TypeScript de Google para aplicaciones web escalables.",
        "icon": "angular.svg",
        "php": "8.3",
        "nodejs": "22",
        "docroot": ".",
        "db": "none",
    },
    {
        "id": "nextjs",
        "name": "Next.js (React)",
        "category": "React Full-Stack / SSR",
        "desc": "Meta-framework full-stack para React con App Router, TypeScript, Tailwind CSS y SSR/SSG.",
        "icon": "nextjs.svg",
        "php": "8.3",
        "nodejs": "22",
        "docroot": ".",
        "db": "none",
    },
    {
        "id": "react",
        "name": "React (Vite)",
        "category": "Frontend SPA",
        "desc": "Desarrollo rápido con Vite + React (TypeScript/JavaScript).",
        "icon": "react.svg",
        "php": "8.3",
        "nodejs": "22",
        "docroot": ".",
        "db": "none",
    },
    {
        "id": "vue",
        "name": "Vue 3 (Vite)",
        "category": "Frontend SPA",
        "desc": "Vite + Vue 3 con Fast Refresh y Node.js integrado.",
        "icon": "vue.svg",
        "php": "8.3",
        "nodejs": "22",
        "docroot": ".",
        "db": "none",
    },
    {
        "id": "php",
        "name": "PHP Plano / HTML",
        "category": "Básico",
        "desc": "Entorno limpio para scripts PHP o páginas web simples.",
        "icon": "php.svg",
        "php": "8.3",
        "docroot": ".",
        "db": "mariadb:10.11",
    },
    {
        "id": "symfony",
        "name": "Symfony",
        "category": "PHP Framework",
        "desc": "Framework robusto para aplicaciones PHP de alto rendimiento.",
        "icon": "symfony.svg",
        "php": "8.3",
        "docroot": "public",
        "db": "mariadb:10.11",
    }
]

DRUPAL_VERSIONS = [
    {"id": "11", "label": "Drupal 11 (Última versión recomendada - PHP 8.3/8.4)", "php": "8.3", "docroot": "web", "type": "drupal11"},
    {"id": "10", "label": "Drupal 10 (LTS Estable - PHP 8.3/8.2)", "php": "8.3", "docroot": "web", "type": "drupal10"},
    {"id": "9", "label": "Drupal 9 (PHP 8.1)", "php": "8.1", "docroot": "web", "type": "drupal9"},
    {"id": "8", "label": "Drupal 8 (PHP 7.4)", "php": "7.4", "docroot": "web", "type": "drupal8"},
    {"id": "7", "label": "Drupal 7 (Legacy - PHP 7.4)", "php": "7.4", "docroot": ".", "type": "drupal7"},
]

TECH_CATEGORIES = [
    {
        "id": "all",
        "name": "Todos",
        "icon": "ddev.svg",
        "match_keys": []
    },
    {
        "id": "drupal",
        "name": "Drupal",
        "icon": "drupal.svg",
        "match_keys": ["drupal", "drupal7", "drupal8", "drupal9", "drupal10", "drupal11"]
    },
    {
        "id": "wordpress",
        "name": "WordPress",
        "icon": "wordpress.svg",
        "match_keys": ["wordpress", "wp"]
    },
    {
        "id": "laravel",
        "name": "Laravel",
        "icon": "laravel.svg",
        "match_keys": ["laravel"]
    },
    {
        "id": "symfony",
        "name": "Symfony",
        "icon": "symfony.svg",
        "match_keys": ["symfony"]
    },
    {
        "id": "nextjs",
        "name": "Next.js",
        "icon": "nextjs.svg",
        "match_keys": ["next", "nextjs"]
    },
    {
        "id": "react",
        "name": "React",
        "icon": "react.svg",
        "match_keys": ["react", "react-ts"]
    },
    {
        "id": "vue",
        "name": "Vue",
        "icon": "vue.svg",
        "match_keys": ["vue", "vue-ts", "vue3"]
    },
    {
        "id": "angular",
        "name": "Angular",
        "icon": "angular.svg",
        "match_keys": ["angular"]
    },
    {
        "id": "django",
        "name": "Django",
        "icon": "django.svg",
        "match_keys": ["django"]
    },
    {
        "id": "flask",
        "name": "Flask",
        "icon": "flask.svg",
        "match_keys": ["flask"]
    },
    {
        "id": "php",
        "name": "PHP",
        "icon": "php.svg",
        "match_keys": ["php"]
    },
    {
        "id": "python",
        "name": "Python",
        "icon": "python.svg",
        "match_keys": ["python"]
    },
    {
        "id": "html",
        "name": "HTML",
        "icon": "php.svg",
        "match_keys": ["html", "static"]
    }
]
