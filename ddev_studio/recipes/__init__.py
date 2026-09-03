"""
Módulo de recetas de scaffolding, importación e infraestructura para DDEV Studio.
"""

from ddev_studio.recipes.base import BaseRecipe, SITES_PHP_TEMPLATE, NGINX_FULL_PROXY_TEMPLATE
from ddev_studio.recipes.context import RecipeContext
from ddev_studio.recipes.registry import get_recipe, register_recipe, list_recipes
from ddev_studio.recipes.runner import run_create_project, run_import_project

__all__ = [
    "BaseRecipe",
    "RecipeContext",
    "get_recipe",
    "register_recipe",
    "list_recipes",
    "run_create_project",
    "run_import_project",
    "SITES_PHP_TEMPLATE",
    "NGINX_FULL_PROXY_TEMPLATE",
]
