# -*- coding: utf-8 -*-
"""
Registro y fábrica centralizada de recetas (Strategy Pattern) para DDEV Studio.
"""

from typing import Dict

from ddev_studio.recipes.base import BaseRecipe
from ddev_studio.recipes.php import (
    DrupalRecipe,
    WordPressRecipe,
    LaravelRecipe,
    SymfonyRecipe,
    GenericPhpRecipe,
)
from ddev_studio.recipes.node import (
    NextjsRecipe,
    ReactRecipe,
    VueRecipe,
    AngularRecipe,
)
from ddev_studio.recipes.python import (
    DjangoRecipe,
    FlaskRecipe,
)

_RECIPES: Dict[str, BaseRecipe] = {
    "drupal": DrupalRecipe(),
    "wordpress": WordPressRecipe(),
    "laravel": LaravelRecipe(),
    "symfony": SymfonyRecipe(),
    "php": GenericPhpRecipe(),
    "html": GenericPhpRecipe(),
    "nextjs": NextjsRecipe(),
    "react": ReactRecipe(),
    "vue": VueRecipe(),
    "angular": AngularRecipe(),
    "django": DjangoRecipe(),
    "flask": FlaskRecipe(),
}


def get_recipe(fw_id: str) -> BaseRecipe:
    """
    Retorna la estrategia de aprovisionamiento asociada al identificador del framework.
    Si no existe una receta específica, retorna GenericPhpRecipe como fallback seguro.
    """
    return _RECIPES.get(fw_id, _RECIPES["php"])


def register_recipe(fw_id: str, recipe: BaseRecipe) -> None:
    """Permite registrar nuevas recetas de forma dinámica en tiempo de ejecución."""
    _RECIPES[fw_id] = recipe


def list_recipes() -> Dict[str, BaseRecipe]:
    """Retorna un diccionario de solo lectura con todas las recetas registradas."""
    return dict(_RECIPES)
